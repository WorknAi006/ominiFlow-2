"""
Web Chat channel: channel configuration, the public widget endpoints
(tenant/channel resolved only from the public key), identity-based contact
resolution, outbound delivery through WebChatProvider, and automation.
"""
import uuid

from app.models import (
    Contact,
    ContactIdentity,
    Conversation,
    Message,
    MessageDirection,
)
from tests.inbox_fixtures import InboxTestCase


class WebChatTestCase(InboxTestCase):

    def headers(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def create_web_chat_channel(self, tenant=None, actor=None, name="Site Chat"):
        headers = self.headers(actor, tenant)
        created = self.client.post(
            "/api/v1/channels", headers=headers,
            json={"channel_type": "web_chat", "name": name},
        )
        assert created.status_code == 201, created.text
        channel_id = created.json()["id"]
        connected = self.client.post(
            f"/api/v1/channels/{channel_id}/web-chat/connect", headers=headers,
        )
        assert connected.status_code == 200, connected.text
        body = connected.json()
        return channel_id, body["external_account_id"]

    def inbound(self, public_key, visitor_id, text, client_message_id=None):
        payload = {"visitor_id": visitor_id, "text": text}
        if client_message_id:
            payload["client_message_id"] = client_message_id
        return self.client.post(f"/api/v1/web-chat/{public_key}/messages", json=payload)


class ChannelConfigTests(WebChatTestCase):

    # Test 1
    def test_create_and_connect_channel(self):
        channel_id, public_key = self.create_web_chat_channel()
        self.assertTrue(public_key.startswith("wc_"))
        detail = self.client.get(f"/api/v1/channels/{channel_id}", headers=self.headers()).json()
        self.assertEqual(detail["channel_type"], "web_chat")
        self.assertEqual(detail["status"], "connected")
        self.assertEqual(detail["external_account_id"], public_key)
        self.assertFalse(detail["has_credentials"])

    # Test 2
    def test_public_key_resolves_correct_tenant_channel(self):
        _, public_key = self.create_web_chat_channel()
        response = self.inbound(public_key, "visitor-1", "Hi there")
        self.assertEqual(response.status_code, 201, response.text)
        self.db.expire_all()
        message = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).one()
        self.assertEqual(message.text, "Hi there")
        self.assertEqual(message.direction, MessageDirection.INBOUND)

    # Test 3
    def test_invalid_public_key_rejected(self):
        self.assertEqual(self.inbound("wc_does_not_exist", "v", "hi").status_code, 404)
        self.assertEqual(
            self.client.get("/api/v1/web-chat/wc_does_not_exist/config").status_code, 404,
        )


class VisitorIdentityTests(WebChatTestCase):

    # Tests 4 and 8
    def test_visitor_creates_identity_and_message(self):
        _, public_key = self.create_web_chat_channel()
        self.inbound(public_key, "visitor-abc", "Hello")
        self.db.expire_all()
        identity = self.db.query(ContactIdentity).filter_by(
            tenant_id=self.tenant_a.id, channel_type="web_chat", external_id="visitor-abc",
        ).one()
        contact = self.db.get(Contact, identity.contact_id)
        self.assertIsNone(contact.normalized_phone_number)  # no phone required
        self.assertEqual(self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 1)

    # Tests 5 and 6
    def test_same_visitor_reuses_contact_and_conversation(self):
        _, public_key = self.create_web_chat_channel()
        self.inbound(public_key, "visitor-xyz", "First")
        self.inbound(public_key, "visitor-xyz", "Second")
        self.db.expire_all()
        self.assertEqual(
            self.db.query(ContactIdentity).filter_by(
                tenant_id=self.tenant_a.id, channel_type="web_chat", external_id="visitor-xyz",
            ).count(), 1,
        )
        self.assertEqual(self.db.query(Contact).filter_by(tenant_id=self.tenant_a.id).count(), 1)
        self.assertEqual(self.db.query(Conversation).filter_by(tenant_id=self.tenant_a.id).count(), 1)
        self.assertEqual(self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 2)

    def test_duplicate_client_message_id_is_idempotent(self):
        _, public_key = self.create_web_chat_channel()
        self.inbound(public_key, "visitor-dup", "Only once", client_message_id="c1")
        self.inbound(public_key, "visitor-dup", "Only once", client_message_id="c1")
        self.db.expire_all()
        self.assertEqual(self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 1)

    # Test 7
    def test_tenant_isolation(self):
        _, key_a = self.create_web_chat_channel(tenant=self.tenant_a, actor=self.owner)
        _, key_b = self.create_web_chat_channel(tenant=self.tenant_b, actor=self.owner_b, name="B Chat")
        self.inbound(key_a, "same-visitor", "to A")
        self.inbound(key_b, "same-visitor", "to B")
        self.db.expire_all()
        a_contacts = self.db.query(Contact).filter_by(tenant_id=self.tenant_a.id).all()
        b_contacts = self.db.query(Contact).filter_by(tenant_id=self.tenant_b.id).all()
        self.assertEqual(len(a_contacts), 1)
        self.assertEqual(len(b_contacts), 1)
        self.assertNotEqual(a_contacts[0].id, b_contacts[0].id)


class OutboundTests(WebChatTestCase):

    def _conversation_for(self, visitor_id):
        self.db.expire_all()
        identity = self.db.query(ContactIdentity).filter_by(
            tenant_id=self.tenant_a.id, channel_type="web_chat", external_id=visitor_id,
        ).one()
        return self.db.query(Conversation).filter_by(
            tenant_id=self.tenant_a.id, contact_id=identity.contact_id,
        ).one()

    # Tests 9 and 10
    def test_agent_reply_uses_web_chat_provider_not_whatsapp(self):
        _, public_key = self.create_web_chat_channel()
        self.inbound(public_key, "visitor-reply", "I need help")
        conversation = self._conversation_for("visitor-reply")

        headers = self.headers(self.agent)
        headers["Idempotency-Key"] = str(uuid.uuid4())
        response = self.client.post(
            f"/api/v1/conversations/{conversation.id}/messages",
            headers=headers, json={"type": "text", "text": "Happy to help!"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["status"], "sent")
        self.assertTrue(body["external_message_id"].startswith("wc_out_"))
        # The WhatsApp fake transport was never called.
        self.assertEqual(self.send_api.requests, [])

        # The visitor can poll the reply back.
        poll = self.client.get(
            f"/api/v1/web-chat/{public_key}/messages", params={"visitor_id": "visitor-reply"},
        )
        self.assertEqual(poll.status_code, 200)
        texts = [(m["direction"], m["text"]) for m in poll.json()["messages"]]
        self.assertIn(("visitor", "I need help"), texts)
        self.assertIn(("agent", "Happy to help!"), texts)


# NOTE: The old flow-graph automation auto-reply test was removed when the
# node/edge automation engine was replaced. Inbound keyword → flow triggering
# (which covers Web Chat through the same channel-neutral boundary) is tested
# in tests/test_keywords.py.
