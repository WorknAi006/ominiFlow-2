"""
Facebook Messenger channel: provider, connect flow, tenant isolation,
webhook security + normalization, inbound pipeline (identity/contact/
conversation/message/dedup), outbound send, automation, realtime, and the
Unified Inbox. Uses a fake Meta Graph transport (httpx.MockTransport); no
live Meta calls and no real credentials.
"""
import hashlib
import hmac
import json
import uuid

import httpx
from cryptography.fernet import Fernet

from app.core.config import settings
from app.integrations.meta.graph_client import appsecret_proof, build_graph_client
from app.integrations.registry import get_provider
from app.integrations.facebook.provider import FacebookProvider, REQUIRED_SCOPES
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Contact,
    ContactIdentity,
    Conversation,
    ConversationStatus,
    Message,
    MessageDirection,
)
from app.models.automation import AutomationExecution
from app.services.automation_execution_service import process_execution
from app.services.credential_service import get_credential_service
from app.services.realtime_service import inbox_channel
from tests.base import DatabaseTestCase

APP_ID = "555666777888"
APP_SECRET = f"fb-app-secret-{uuid.uuid4().hex}"
VERIFY_TOKEN = f"fb-verify-{uuid.uuid4().hex}"

PAGE_A = "310000000000001"
PAGE_B = "310000000000002"
TOKEN_A = f"EAAG-fb-a-{uuid.uuid4().hex}"
TOKEN_B = f"EAAG-fb-b-{uuid.uuid4().hex}"

PSID_1 = "psid-1111111111"
PSID_2 = "psid-2222222222"


def _err(status_code: int, message: str, code: int) -> httpx.Response:
    return httpx.Response(status_code, json={"error": {"message": message, "code": code}})


class FakeFacebook:
    """Simulates the Meta Graph endpoints the Facebook provider calls."""

    def __init__(self) -> None:
        self.valid_tokens: set[str] = set()
        self.token_scopes: dict[str, list[str]] = {}
        self.subscribed: set[str] = set()
        self.sent: list[dict] = []
        self.requests: list[httpx.Request] = []
        self.send_error: tuple[int, str, int] | None = None
        self.network_down = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.network_down:
            raise httpx.ConnectError("connection refused", request=request)
        if request.url.host != "graph.facebook.com":
            return httpx.Response(200, content=b"stolen")

        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        _, _, path = request.url.path.lstrip("/").partition("/")
        parts = path.split("/")

        # App-token call; carries input_token, no appsecret_proof.
        if path == "debug_token":
            input_token = request.url.params.get("input_token")
            data = {
                "is_valid": input_token in self.valid_tokens,
                "app_id": APP_ID,
                "scopes": self.token_scopes.get(input_token, list(REQUIRED_SCOPES)),
                "expires_at": 0,
            }
            return httpx.Response(200, json={"data": data})

        if request.url.params.get("appsecret_proof") != appsecret_proof(APP_SECRET, token):
            return _err(400, "Invalid appsecret_proof", 100)
        if token not in self.valid_tokens:
            return _err(401, f"Error validating access token {token}", 190)

        if path == "me/messages" and request.method == "POST":
            if self.send_error:
                s, m, c = self.send_error
                return _err(s, m.replace("{token}", token), c)
            body = json.loads(request.content)
            self.sent.append(body)
            return httpx.Response(200, json={
                "recipient_id": body["recipient"]["id"],
                "message_id": f"m_{uuid.uuid4().hex}",
            })

        if len(parts) == 2 and parts[1] == "subscribed_apps":
            page_id = parts[0]
            if request.method == "POST":
                if request.url.params.get("subscribed_fields") != "messages":
                    return _err(400, "Missing subscribed_fields", 100)
                self.subscribed.add(page_id)
                return httpx.Response(200, json={"success": True})
            if request.method == "DELETE":
                self.subscribed.discard(page_id)
                return httpx.Response(200, json={"success": True})
            data = (
                [{"id": APP_ID, "subscribed_fields": [{"name": "messages"}]}]
                if page_id in self.subscribed else []
            )
            return httpx.Response(200, json={"data": data})

        if len(parts) == 1:
            page_id = parts[0]
            return httpx.Response(200, json={"id": page_id, "name": f"Page {page_id}"})

        return _err(404, "Unknown path", 100)


class FacebookTestCase(DatabaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._saved = {
            name: getattr(settings, name)
            for name in (
                "meta_app_id", "meta_app_secret", "channel_credential_keys",
                "facebook_webhook_verify_token",
            )
        }
        settings.meta_app_id = APP_ID
        settings.meta_app_secret = APP_SECRET
        settings.channel_credential_keys = Fernet.generate_key().decode()
        settings.facebook_webhook_verify_token = VERIFY_TOKEN
        cls.provider = get_provider(ChannelType.FACEBOOK)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.provider.client_factory = build_graph_client
        for name, value in cls._saved.items():
            setattr(settings, name, value)

    def setUp(self) -> None:
        super().setUp()
        self.fake = FakeFacebook()
        self.fake.valid_tokens.update({TOKEN_A, TOKEN_B})
        self.fake.subscribed.update({PAGE_A, PAGE_B})
        transport = httpx.MockTransport(self.fake.handler)
        self.provider.client_factory = lambda: build_graph_client(transport=transport)
        self.realtime.published.clear()

    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant_a = cls.make_tenant("OnlineGo")
        cls.owner = cls.make_member(cls.tenant_a, "OWNER")
        cls.agent = cls.make_member(cls.tenant_a, "AGENT")
        cls.viewer = cls.make_member(cls.tenant_a, "VIEWER")

        cls.tenant_b = cls.make_tenant("AI Tourism")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

        cls.fb_a = cls.make_fb_channel(cls.tenant_a, "OnlineGo Facebook", PAGE_A, TOKEN_A)
        cls.fb_b = cls.make_fb_channel(cls.tenant_b, "AI Tourism Facebook", PAGE_B, TOKEN_B)

    # ---------- builders ----------

    @classmethod
    def make_fb_channel(cls, tenant, name, page_id, token):
        channel = ChannelConnection(
            tenant_id=tenant.id,
            channel_type=ChannelType.FACEBOOK,
            name=name,
            status=ChannelStatus.CONNECTED,
            external_account_id=page_id,
            external_business_id=None,
            access_token_encrypted=get_credential_service().encrypt(token),
        )
        cls.db.add(channel)
        cls.db.flush()
        return channel

    def seed_contact(self, tenant, channel, psid, name="Visitor"):
        contact = Contact(tenant_id=tenant.id, display_name=name, is_blocked=False)
        self.db.add(contact)
        self.db.flush()
        self.db.add(ContactIdentity(
            tenant_id=tenant.id, contact_id=contact.id,
            channel_type=ChannelType.FACEBOOK.value, external_id=psid,
        ))
        conversation = Conversation(
            tenant_id=tenant.id, contact_id=contact.id,
            channel_connection_id=channel.id, status=ConversationStatus.OPEN,
        )
        self.db.add(conversation)
        self.db.flush()
        self.db.commit()
        return contact, conversation

    # ---------- webhook helpers ----------

    @staticmethod
    def payload(page_id, psid, text, mid=None, extra_message=None):
        message = {"mid": mid or f"m_{uuid.uuid4().hex}"}
        if text is not None:
            message["text"] = text
        if extra_message:
            message.update(extra_message)
        return {
            "object": "page",
            "entry": [{
                "id": page_id,
                "time": 1_700_000_000_000,
                "messaging": [{
                    "sender": {"id": psid},
                    "recipient": {"id": page_id},
                    "timestamp": 1_700_000_000_000,
                    "message": message,
                }],
            }],
        }

    def sign(self, raw: bytes) -> dict[str, str]:
        digest = hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        return {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}

    def post_webhook(self, payload, *, sign=True):
        raw = json.dumps(payload).encode()
        headers = self.sign(raw) if sign else {"Content-Type": "application/json"}
        return self.client.post("/api/v1/webhooks/facebook", content=raw, headers=headers)

    def auth_h(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def send_reply(self, conversation_id, text, actor=None, tenant=None):
        return self.client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={**self.auth_h(actor, tenant), "Idempotency-Key": str(uuid.uuid4())},
            json={"type": "text", "text": text},
        )

    # ========== provider ==========

    def test_01_provider_registration_and_construction(self):
        self.assertIsInstance(self.provider, FacebookProvider)
        self.assertEqual(self.provider.channel_type, ChannelType.FACEBOOK)
        self.assertTrue(self.provider.requires_credentials)
        self.assertTrue(self.provider.is_configured())

    # ========== connect / credentials / validation / isolation ==========

    def test_02_connect_configuration_and_credential_encryption(self):
        page_c, token_c = "310000000000009", f"EAAG-fb-c-{uuid.uuid4().hex}"
        self.fake.valid_tokens.add(token_c)
        created = self.client.post(
            "/api/v1/channels", headers=self.auth_h(),
            json={"channel_type": "facebook", "name": "New Page"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        channel_id = created.json()["id"]

        resp = self.client.post(
            f"/api/v1/channels/{channel_id}/facebook/connect",
            headers=self.auth_h(),
            json={"page_id": page_c, "access_token": token_c},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["status"], "connected")
        self.assertEqual(body["external_account_id"], page_c)
        self.assertTrue(body["has_credentials"])
        self.assertNotIn(token_c, resp.text)
        self.assertIn(page_c, self.fake.subscribed)

        channel = self.db.get(ChannelConnection, uuid.UUID(channel_id))
        self.db.refresh(channel)
        self.assertNotIn(token_c, channel.access_token_encrypted or "")
        self.assertEqual(
            get_credential_service().decrypt(channel.access_token_encrypted), token_c,
        )

    def test_03_connect_rejects_token_missing_scopes(self):
        page_c, token_c = "310000000000010", f"EAAG-fb-d-{uuid.uuid4().hex}"
        self.fake.valid_tokens.add(token_c)
        self.fake.token_scopes[token_c] = ["public_profile"]
        created = self.client.post(
            "/api/v1/channels", headers=self.auth_h(),
            json={"channel_type": "facebook", "name": "Bad Scopes"},
        )
        channel_id = created.json()["id"]
        resp = self.client.post(
            f"/api/v1/channels/{channel_id}/facebook/connect",
            headers=self.auth_h(), json={"page_id": page_c, "access_token": token_c},
        )
        self.assertEqual(resp.status_code, 400, resp.text)
        channel = self.db.get(ChannelConnection, uuid.UUID(channel_id))
        self.db.refresh(channel)
        self.assertEqual(channel.status, ChannelStatus.ERROR)

    def test_04_connection_validation_healthy(self):
        resp = self.client.post(
            f"/api/v1/channels/{self.fb_a.id}/facebook/test", headers=self.auth_h(),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body["healthy"])
        self.assertTrue(body["webhook_subscribed"])
        self.assertEqual(body["page_name"], f"Page {PAGE_A}")

    def test_05_tenant_isolation_of_connection(self):
        # A cannot test/connect B's channel; it simply does not resolve.
        self.assertEqual(
            self.client.post(
                f"/api/v1/channels/{self.fb_b.id}/facebook/test", headers=self.auth_h(),
            ).status_code, 404,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/channels/{self.fb_b.id}/facebook/connect", headers=self.auth_h(),
                json={"page_id": PAGE_B, "access_token": TOKEN_B},
            ).status_code, 404,
        )
        # Reusing a Page already connected elsewhere is refused (409), without
        # revealing the other tenant.
        created = self.client.post(
            "/api/v1/channels", headers=self.auth_h(),
            json={"channel_type": "facebook", "name": "Hijack attempt"},
        )
        resp = self.client.post(
            f"/api/v1/channels/{created.json()['id']}/facebook/connect",
            headers=self.auth_h(), json={"page_id": PAGE_B, "access_token": TOKEN_A},
        )
        self.assertEqual(resp.status_code, 409, resp.text)

    def test_06_connect_requires_channel_permission(self):
        created = self.client.post(
            "/api/v1/channels", headers=self.auth_h(),
            json={"channel_type": "facebook", "name": "RBAC"},
        )
        channel_id = created.json()["id"]
        self.assertEqual(
            self.client.post(
                f"/api/v1/channels/{channel_id}/facebook/connect",
                headers=self.auth_h(self.viewer),
                json={"page_id": "310000000000011", "access_token": TOKEN_A},
            ).status_code, 403,
        )

    # ========== webhook security ==========

    def test_07_webhook_verification_handshake(self):
        ok = self.client.get(
            "/api/v1/webhooks/facebook",
            params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "abc123"},
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.text, "abc123")

        bad = self.client.get(
            "/api/v1/webhooks/facebook",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "abc123"},
        )
        self.assertEqual(bad.status_code, 403)

    def test_08_webhook_signature_required(self):
        payload = self.payload(PAGE_A, PSID_1, "hello")
        unsigned = self.post_webhook(payload, sign=False)
        self.assertEqual(unsigned.status_code, 403)
        raw = json.dumps(payload).encode()
        tampered = self.client.post(
            "/api/v1/webhooks/facebook", content=raw,
            headers={"X-Hub-Signature-256": "sha256=deadbeef", "Content-Type": "application/json"},
        )
        self.assertEqual(tampered.status_code, 403)
        self.assertEqual(self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 0)

    # ========== inbound pipeline ==========

    def test_09_inbound_creates_identity_contact_conversation_message(self):
        resp = self.post_webhook(self.payload(PAGE_A, PSID_1, "I need pricing"))
        self.assertEqual(resp.status_code, 200, resp.text)

        identity = self.db.query(ContactIdentity).filter_by(
            tenant_id=self.tenant_a.id, channel_type="facebook", external_id=PSID_1,
        ).one()
        contact = self.db.get(Contact, identity.contact_id)
        self.assertEqual(contact.tenant_id, self.tenant_a.id)
        self.assertIsNone(contact.normalized_phone_number)  # PSID is not a phone

        conversation = self.db.query(Conversation).filter_by(
            tenant_id=self.tenant_a.id, contact_id=contact.id,
            channel_connection_id=self.fb_a.id,
        ).one()
        message = self.db.query(Message).filter_by(
            tenant_id=self.tenant_a.id, conversation_id=conversation.id,
        ).one()
        self.assertEqual(message.direction, MessageDirection.INBOUND)
        self.assertEqual(message.text, "I need pricing")
        self.assertEqual(message.sender_identifier, PSID_1)

    def test_10_existing_contact_is_reused(self):
        self.post_webhook(self.payload(PAGE_A, PSID_1, "first"))
        self.post_webhook(self.payload(PAGE_A, PSID_1, "second"))
        contacts = self.db.query(Contact).join(
            ContactIdentity, ContactIdentity.contact_id == Contact.id,
        ).filter(
            ContactIdentity.tenant_id == self.tenant_a.id,
            ContactIdentity.external_id == PSID_1,
        ).all()
        self.assertEqual(len(contacts), 1)
        self.assertEqual(
            self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 2,
        )

    def test_11_same_psid_isolated_across_tenants(self):
        self.post_webhook(self.payload(PAGE_A, PSID_1, "for OnlineGo"))
        self.post_webhook(self.payload(PAGE_B, PSID_1, "for AI Tourism"))
        a = self.db.query(ContactIdentity).filter_by(
            tenant_id=self.tenant_a.id, external_id=PSID_1,
        ).one()
        b = self.db.query(ContactIdentity).filter_by(
            tenant_id=self.tenant_b.id, external_id=PSID_1,
        ).one()
        self.assertNotEqual(a.contact_id, b.contact_id)

    def test_12_duplicate_webhook_is_idempotent(self):
        payload = self.payload(PAGE_A, PSID_1, "only once", mid="m_fixed_123")
        self.assertEqual(self.post_webhook(payload).status_code, 200)
        self.assertEqual(self.post_webhook(payload).status_code, 200)
        self.assertEqual(
            self.db.query(Message).filter_by(
                tenant_id=self.tenant_a.id, external_message_id="m_fixed_123",
            ).count(), 1,
        )

    def test_13_unroutable_and_non_message_events_are_dropped(self):
        # Unknown page -> dropped, still 200.
        self.assertEqual(self.post_webhook(self.payload("999999999999999", PSID_1, "x")).status_code, 200)
        # Delivery receipt (no message object) -> no row.
        receipt = {
            "object": "page",
            "entry": [{"id": PAGE_A, "messaging": [{"sender": {"id": PSID_1}, "recipient": {"id": PAGE_A}, "delivery": {"mids": ["m_x"]}}]}],
        }
        self.assertEqual(self.post_webhook(receipt).status_code, 200)
        # Echo -> ignored.
        echo = self.payload(PAGE_A, PSID_1, "echo", extra_message={"is_echo": True})
        self.assertEqual(self.post_webhook(echo).status_code, 200)
        self.assertEqual(self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 0)

    def test_14_non_text_message_stored_as_unknown(self):
        payload = self.payload(PAGE_A, PSID_1, None, extra_message={
            "attachments": [{"type": "image", "payload": {"url": "https://x"}}],
        })
        self.assertEqual(self.post_webhook(payload).status_code, 200)
        message = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).one()
        self.assertEqual(message.message_type, "unknown")
        self.assertIsNone(message.text)

    # ========== outbound ==========

    def test_15_outbound_send_text_resolves_psid_recipient(self):
        contact, conversation = self.seed_contact(self.tenant_a, self.fb_a, PSID_2)
        resp = self.send_reply(conversation.id, "Hello from OnlineGo")
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertEqual(resp.json()["status"], "sent")
        self.assertEqual(len(self.fake.sent), 1)
        body = self.fake.sent[0]
        self.assertEqual(body["recipient"]["id"], PSID_2)   # PSID, not a phone
        self.assertEqual(body["message"]["text"], "Hello from OnlineGo")
        self.assertEqual(body["messaging_type"], "RESPONSE")

    def test_16_outbound_cross_tenant_send_denied(self):
        _, conversation_b = self.seed_contact(self.tenant_b, self.fb_b, PSID_2)
        resp = self.send_reply(conversation_b.id, "A sending into B")  # actor = tenant A
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.fake.sent, [])

    # ========== automation ==========

    def _build_active_automation(self):
        created = self.client.post(
            "/api/v1/automations", headers=self.auth_h(), json={"name": "FB pricing"},
        )
        automation_id = created.json()["id"]
        trigger = self.client.get(
            f"/api/v1/automations/{automation_id}", headers=self.auth_h(),
        ).json()["nodes"][0]
        condition_id, action_id = str(uuid.uuid4()), str(uuid.uuid4())
        body = {
            "nodes": [
                {"id": trigger["id"], "node_type": "trigger_message", "name": "Inbound FB", "config": {"channel_connection_id": str(self.fb_a.id)}, "sort_order": 0},
                {"id": condition_id, "node_type": "message_contains", "name": "pricing", "config": {"value": "price", "case_sensitive": False}, "sort_order": 1},
                {"id": action_id, "node_type": "send_text", "name": "Reply", "config": {"text": "Thanks for asking about pricing."}, "sort_order": 2},
            ],
            "edges": [
                {"source_node_id": trigger["id"], "target_node_id": condition_id},
                {"source_node_id": condition_id, "target_node_id": action_id, "branch": "true"},
            ],
        }
        self.assertEqual(
            self.client.put(f"/api/v1/automations/{automation_id}/flow", headers=self.auth_h(), json=body).status_code, 200,
        )
        self.assertEqual(
            self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.auth_h(), json={}).status_code, 200,
        )
        return automation_id

    def test_17_automation_send_text_through_facebook_provider(self):
        automation_id = self._build_active_automation()
        self.assertEqual(self.post_webhook(self.payload(PAGE_A, PSID_1, "what is the price?")).status_code, 200)

        execution = self.db.query(AutomationExecution).filter_by(
            tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id),
        ).one()
        self.assertEqual(execution.status, "queued")
        self.assertTrue(process_execution(self.db, execution.id))
        self.db.refresh(execution)
        self.assertEqual(execution.status, "completed")
        # The automation reply went out through the Facebook Send API to the PSID.
        self.assertEqual(len(self.fake.sent), 1)
        self.assertEqual(self.fake.sent[0]["recipient"]["id"], PSID_1)

    # ========== realtime ==========

    def test_18_inbound_publishes_realtime_event_to_tenant(self):
        self.assertEqual(self.post_webhook(self.payload(PAGE_A, PSID_1, "ping")).status_code, 200)
        channels = [ch for ch, _ in self.realtime.published]
        self.assertIn(inbox_channel(self.tenant_a.id), channels)
        self.assertNotIn(inbox_channel(self.tenant_b.id), channels)
        events = [json.loads(p) for ch, p in self.realtime.published if ch == inbox_channel(self.tenant_a.id)]
        self.assertTrue(any(e.get("event") == "message.created" for e in events))

    # ========== unified inbox ==========

    def test_19_facebook_conversation_in_unified_inbox(self):
        self.post_webhook(self.payload(PAGE_A, PSID_1, "inbox please"))
        listing = self.client.get(
            f"/api/v1/conversations?channel_id={self.fb_a.id}", headers=self.auth_h(),
        )
        self.assertEqual(listing.status_code, 200, listing.text)
        items = listing.json()["items"]
        self.assertEqual(len(items), 1)
        conversation_id = items[0]["id"]
        messages = self.client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers=self.auth_h(),
        )
        self.assertEqual(messages.status_code, 200)
        texts = [m["text"] for m in messages.json()["items"]]
        self.assertIn("inbox please", texts)

    def test_20_cross_tenant_inbox_access_denied(self):
        self.post_webhook(self.payload(PAGE_B, PSID_1, "B only"))
        conversation_b = self.db.query(Conversation).filter_by(tenant_id=self.tenant_b.id).one()
        message_b = self.db.query(Message).filter_by(tenant_id=self.tenant_b.id).one()
        # Tenant A cannot see B's conversation or message.
        self.assertEqual(
            self.client.get(f"/api/v1/conversations/{conversation_b.id}", headers=self.auth_h()).status_code, 404,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/conversations/{conversation_b.id}/messages", headers=self.auth_h()).status_code, 404,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/messages/{message_b.id}", headers=self.auth_h()).status_code, 404,
        )
        self.assertNotIn(
            str(conversation_b.id),
            [c["id"] for c in self.client.get("/api/v1/conversations", headers=self.auth_h()).json()["items"]],
        )

    # ========== regression ==========

    def test_21_other_providers_still_registered(self):
        from app.integrations.whatsapp.provider import WhatsAppProvider
        from app.integrations.web_chat.provider import WebChatProvider
        self.assertIsInstance(get_provider(ChannelType.WHATSAPP), WhatsAppProvider)
        self.assertIsInstance(get_provider(ChannelType.WEB_CHAT), WebChatProvider)
