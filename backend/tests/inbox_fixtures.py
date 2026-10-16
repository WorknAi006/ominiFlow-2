"""
Shared fixtures for Unified Inbox tests: two tenants, connected WhatsApp
channels with encrypted tokens, helpers for events/contacts/conversations,
and a fake Meta "send message" endpoint (httpx.MockTransport).
"""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet

from app.core.config import settings
from app.integrations.meta.graph_client import appsecret_proof, build_graph_client
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Contact,
    Conversation,
    ConversationStatus,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    WhatsAppEvent,
)
from app.services.credential_service import get_credential_service
from tests.base import DatabaseTestCase

APP_ID = "555666777888"
APP_SECRET = f"inbox-app-secret-{uuid.uuid4().hex}"
TOKEN_A = f"EAAG-inbox-a-{uuid.uuid4().hex}"
TOKEN_B = f"EAAG-inbox-b-{uuid.uuid4().hex}"

PHONE_ID_A, WABA_A = "610000000000001", "620000000000001"
PHONE_ID_B, WABA_B = "610000000000002", "620000000000002"

CUSTOMER = "15550102000"
CUSTOMER_E164 = "+15550102000"

BASE_TIME = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)


class FakeSendApi:
    """Simulates POST /{phone_number_id}/messages."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.fail_with: tuple[int, str, int] | None = None
        self.network_down = False
        self.counter = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.network_down:
            raise httpx.ConnectError("connection refused", request=request)

        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if request.url.params.get("appsecret_proof") != appsecret_proof(APP_SECRET, token):
            return httpx.Response(400, json={"error": {"message": "Invalid appsecret_proof", "code": 100}})

        if self.fail_with:
            status_code, message, code = self.fail_with
            return httpx.Response(
                status_code,
                json={"error": {"message": message.replace("{token}", token), "code": code}},
            )

        # Media upload (multipart) returns a media id, not a message id.
        if request.url.path.rstrip("/").endswith("/media"):
            self.counter += 1
            return httpx.Response(200, json={"id": f"media.OUT{self.counter}-{uuid.uuid4().hex[:8]}"})

        self.counter += 1
        return httpx.Response(200, json={
            "messaging_product": "whatsapp",
            "contacts": [{"input": "x", "wa_id": "x"}],
            "messages": [{"id": f"wamid.OUT{self.counter}-{uuid.uuid4().hex[:8]}"}],
        })


class InboxTestCase(DatabaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._saved = {
            name: getattr(settings, name)
            for name in ("meta_app_id", "meta_app_secret", "channel_credential_keys")
        }
        settings.meta_app_id = APP_ID
        settings.meta_app_secret = APP_SECRET
        settings.channel_credential_keys = Fernet.generate_key().decode()
        cls.provider = get_provider(ChannelType.WHATSAPP)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.provider.client_factory = build_graph_client
        for name, value in cls._saved.items():
            setattr(settings, name, value)

    def setUp(self) -> None:
        super().setUp()
        self.send_api = FakeSendApi()
        transport = httpx.MockTransport(self.send_api.handler)
        self.provider.client_factory = lambda: build_graph_client(transport=transport)

    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant_a = cls.make_tenant("Tenant A")
        cls.owner = cls.make_member(cls.tenant_a, "OWNER")
        cls.admin = cls.make_member(cls.tenant_a, "ADMIN")
        cls.manager = cls.make_member(cls.tenant_a, "MANAGER")
        cls.agent = cls.make_member(cls.tenant_a, "AGENT")
        cls.viewer = cls.make_member(cls.tenant_a, "VIEWER")
        cls.developer = cls.make_member(cls.tenant_a, "DEVELOPER")

        cls.tenant_b = cls.make_tenant("Tenant B")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

        cls.wa_a = cls.make_channel(cls.tenant_a, "WA A", PHONE_ID_A, WABA_A, TOKEN_A)
        cls.wa_b = cls.make_channel(cls.tenant_b, "WA B", PHONE_ID_B, WABA_B, TOKEN_B)
        cls.ig_a = cls.make_channel(
            cls.tenant_a, "IG A", "ig-1", None, TOKEN_A, channel_type=ChannelType.INSTAGRAM,
        )

    # ---------- builders ----------

    @classmethod
    def make_channel(cls, tenant, name, phone_id, waba_id, token, channel_type=ChannelType.WHATSAPP):
        channel = ChannelConnection(
            tenant_id=tenant.id,
            channel_type=channel_type,
            name=name,
            status=ChannelStatus.CONNECTED,
            external_account_id=phone_id,
            external_business_id=waba_id,
            access_token_encrypted=get_credential_service().encrypt(token),
        )
        cls.db.add(channel)
        cls.db.flush()
        return channel

    @classmethod
    def make_contact(cls, tenant, phone=None, **fields):
        contact = Contact(
            tenant_id=tenant.id,
            phone_number=phone,
            normalized_phone_number=f"+{phone.lstrip('+')}" if phone else None,
            external_identifier=phone.lstrip("+") if phone else None,
            is_blocked=False,
            **fields,
        )
        cls.db.add(contact)
        cls.db.flush()
        return contact

    @classmethod
    def make_conversation(cls, tenant, contact, channel, status=ConversationStatus.OPEN, **fields):
        conversation = Conversation(
            tenant_id=tenant.id,
            contact_id=contact.id,
            channel_connection_id=channel.id,
            channel_type=channel.channel_type,
            status=status,
            unread_count=fields.pop("unread_count", 0),
            **fields,
        )
        cls.db.add(conversation)
        cls.db.flush()
        return conversation

    @classmethod
    def make_message(cls, conversation, text="Hi", direction=MessageDirection.INBOUND,
                     status=None, external_id=None, created_at=None):
        message = Message(
            tenant_id=conversation.tenant_id,
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
            channel_connection_id=conversation.channel_connection_id,
            direction=direction,
            message_type=MessageType.TEXT,
            text=text,
            external_message_id=external_id,
            status=status or (
                MessageStatus.RECEIVED if direction == MessageDirection.INBOUND else MessageStatus.SENT
            ),
        )
        if created_at is not None:
            message.created_at = created_at
        cls.db.add(message)
        cls.db.flush()
        return message

    def make_event(self, channel, event_type, payload, *, wa_message_id=None,
                   wa_id=None, occurred_at=None, dedupe_key=None, tenant=None):
        event = WhatsAppEvent(
            tenant_id=tenant.id if tenant is not None else channel.tenant_id,
            channel_id=channel.id,
            event_type=event_type,
            dedupe_key=dedupe_key or f"{event_type}:{uuid.uuid4().hex}",
            wa_message_id=wa_message_id,
            wa_id=wa_id,
            occurred_at=occurred_at or BASE_TIME,
            payload=payload,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def message_event(self, channel, message, contact_name="Jane Customer", **kwargs):
        payload = {
            "message": message,
            "contact": {"wa_id": message.get("from"), "profile": {"name": contact_name}},
            "metadata": {"phone_number_id": channel.external_account_id},
        }
        return self.make_event(
            channel, "message", payload,
            wa_message_id=message.get("id"), wa_id=message.get("from"), **kwargs,
        )

    def status_event(self, channel, external_id, state, errors=None, occurred_at=None):
        status = {"id": external_id, "status": state, "recipient_id": CUSTOMER}
        if errors is not None:
            status["errors"] = errors
        return self.make_event(
            channel, "status", {"status": status, "metadata": {}},
            wa_message_id=external_id, wa_id=CUSTOMER,
            occurred_at=occurred_at or BASE_TIME + timedelta(minutes=5),
        )

    @staticmethod
    def text_message(message_id=None, body="Hello there", sender=CUSTOMER, **extra):
        return {
            "from": sender,
            "id": message_id or f"wamid.IN{uuid.uuid4().hex}",
            "timestamp": str(int(BASE_TIME.timestamp())),
            "type": "text",
            "text": {"body": body},
            **extra,
        }

    def reload(self, model, obj_id):
        self.db.expire_all()
        return self.db.get(model, obj_id)
