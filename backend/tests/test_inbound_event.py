"""
The channel-neutral inbound event boundary: the WhatsApp provider's
normalizer produces a NormalizedInboundEvent, and inbound_event_service
turns it into Contact -> Conversation -> Message using ContactIdentity,
with no WhatsApp-specific parsing in the common path.
"""
from datetime import timedelta

from app.integrations.base import NormalizedInboundEvent
from app.integrations.registry import get_provider
from app.models import (
    ChannelType,
    Contact,
    ContactIdentity,
    Conversation,
    Message,
    MessageType,
)
from app.services import inbound_event_service
from tests.inbox_fixtures import (
    BASE_TIME,
    CUSTOMER,
    CUSTOMER_E164,
    TOKEN_A,
    WABA_A,
    InboxTestCase,
)


def raw_text(message_id="wamid.N1", sender=CUSTOMER, body="Hello there", name="Jane Customer"):
    return {
        "payload": {
            "message": {"id": message_id, "from": sender, "type": "text", "text": {"body": body}},
            "contact": {"wa_id": sender, "profile": {"name": name}},
        },
        "external_message_id": message_id,
        "external_sender_id": sender,
        "external_event_id": f"message:{message_id}",
        "occurred_at": BASE_TIME,
    }


def raw_image(message_id="wamid.IMG", sender=CUSTOMER, media_id="media-123"):
    return {
        "payload": {
            "message": {
                "id": message_id, "from": sender, "type": "image",
                "image": {"id": media_id, "mime_type": "image/jpeg", "caption": "look"},
            },
            "contact": {"wa_id": sender, "profile": {"name": "Jane"}},
        },
        "external_message_id": message_id,
        "external_sender_id": sender,
        "external_event_id": f"message:{message_id}",
        "occurred_at": BASE_TIME,
    }


class NormalizerTests(InboxTestCase):

    @property
    def provider(self):  # the registry's shared WhatsApp provider
        return get_provider(ChannelType.WHATSAPP)

    # Test 1: webhook payload -> normalized inbound event
    def test_normalizes_whatsapp_text(self):
        event = self.provider.normalize_inbound_message(self.wa_a, raw_text())
        self.assertIsInstance(event, NormalizedInboundEvent)
        self.assertEqual(event.channel_type, "whatsapp")
        self.assertEqual(event.tenant_id, self.tenant_a.id)
        self.assertEqual(event.channel_connection_id, self.wa_a.id)
        self.assertEqual(event.external_message_id, "wamid.N1")
        self.assertEqual(event.external_sender_id, CUSTOMER)
        self.assertEqual(event.phone_hint, CUSTOMER)
        self.assertEqual(event.message_type, MessageType.TEXT)
        self.assertEqual(event.text, "Hello there")
        self.assertEqual(event.sender_display_name, "Jane Customer")

    def test_normalizes_whatsapp_image_media(self):
        event = self.provider.normalize_inbound_message(self.wa_a, raw_image())
        self.assertEqual(event.message_type, MessageType.IMAGE)
        self.assertEqual(event.media_metadata.get("id"), "media-123")
        self.assertEqual(event.media_type, "image/jpeg")
        self.assertEqual(event.text, "look")

    def test_malformed_missing_id_or_sender_returns_none(self):
        cases = [
            {"payload": {"message": "nope"}, "external_message_id": None, "external_sender_id": None},
            {"payload": {"message": {"type": "text"}}, "external_message_id": None, "external_sender_id": None},
            {"payload": {"message": {"id": "x", "type": "text"}}, "external_message_id": "x", "external_sender_id": None},
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                self.assertIsNone(self.provider.normalize_inbound_message(self.wa_a, raw))


class CommonProcessingTests(InboxTestCase):

    def process(self, raw, channel=None):
        provider = get_provider(ChannelType.WHATSAPP)
        event = provider.normalize_inbound_message(channel or self.wa_a, raw)
        result = inbound_event_service.process_inbound_event(self.db, event)
        self.db.commit()
        return result

    # Test 5: text inbound creates Contact -> Conversation -> Message
    def test_creates_contact_conversation_message(self):
        events = self.process(raw_text())
        self.assertEqual(len(events), 2)  # message.created + conversation.updated

        self.db.expire_all()
        contacts = self.db.query(Contact).filter_by(
            tenant_id=self.tenant_a.id, normalized_phone_number=CUSTOMER_E164,
        ).all()
        self.assertEqual(len(contacts), 1)
        conversations = self.db.query(Conversation).filter_by(tenant_id=self.tenant_a.id).all()
        self.assertEqual(len(conversations), 1)
        messages = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).all()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, "Hello there")

    # Test 6: media inbound works through the boundary
    def test_media_inbound_registers_message(self):
        self.process(raw_image())
        self.db.expire_all()
        [message] = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).all()
        self.assertEqual(message.message_type, "image")

    # Test 2: duplicate external message id does not reprocess
    def test_duplicate_external_message_is_idempotent(self):
        self.process(raw_text(message_id="wamid.DUP"))
        second = self.process(raw_text(message_id="wamid.DUP"))
        self.assertEqual(second, [])
        self.db.expire_all()
        self.assertEqual(
            self.db.query(Message).filter_by(
                tenant_id=self.tenant_a.id, external_message_id="wamid.DUP",
            ).count(),
            1,
        )

    # Test 3: same wa_id resolves to the same contact + single identity
    def test_same_sender_resolves_single_identity(self):
        self.process(raw_text(message_id="wamid.A"))
        self.process(raw_text(message_id="wamid.B"))
        self.db.expire_all()
        contacts = self.db.query(Contact).filter_by(
            tenant_id=self.tenant_a.id, normalized_phone_number=CUSTOMER_E164,
        ).all()
        self.assertEqual(len(contacts), 1)
        identities = self.db.query(ContactIdentity).filter_by(
            tenant_id=self.tenant_a.id, channel_type="whatsapp", external_id=CUSTOMER,
        ).all()
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0].contact_id, contacts[0].id)

    def test_same_number_across_whatsapp_lines_uses_one_thread(self):
        other_line = self.make_channel(
            self.tenant_a, "WA A2", "phone-id-a2", WABA_A, TOKEN_A,
        )
        self.process(raw_text(message_id="wamid.LINE_A"), channel=self.wa_a)

        latest_time = BASE_TIME + timedelta(minutes=10)
        latest = raw_text(message_id="wamid.LINE_B")
        latest["occurred_at"] = latest_time
        self.process(latest, channel=other_line)

        # A delayed webhook from the older line must not change the reply route.
        older = raw_text(message_id="wamid.LINE_A_OLD")
        older["occurred_at"] = BASE_TIME + timedelta(minutes=5)
        self.process(older, channel=self.wa_a)

        self.db.expire_all()
        conversations = self.db.query(Conversation).filter_by(
            tenant_id=self.tenant_a.id,
        ).all()
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].channel_connection_id, other_line.id)
        self.assertEqual(conversations[0].last_inbound_at, latest_time)

        messages = self.db.query(Message).filter_by(
            tenant_id=self.tenant_a.id,
        ).all()
        self.assertEqual(len(messages), 3)
        self.assertEqual({message.conversation_id for message in messages}, {conversations[0].id})
        self.assertEqual(
            {message.channel_connection_id for message in messages},
            {self.wa_a.id, other_line.id},
        )

    # Test 4: a tenant A event never resolves a tenant B identity
    def test_tenant_isolation_of_identity_resolution(self):
        # Tenant B first owns an identity for this sender.
        self.process(raw_text(message_id="wamid.B1"), channel=self.wa_b)
        self.db.expire_all()
        b_contact = self.db.query(Contact).filter_by(tenant_id=self.tenant_b.id).one()

        # The same sender arriving on tenant A resolves a separate contact.
        self.process(raw_text(message_id="wamid.A1"), channel=self.wa_a)
        self.db.expire_all()
        a_contact = self.db.query(Contact).filter_by(tenant_id=self.tenant_a.id).one()

        self.assertNotEqual(a_contact.id, b_contact.id)
        self.assertEqual(
            self.db.query(ContactIdentity).filter_by(external_id=CUSTOMER).count(), 2,
        )
        self.assertEqual(
            {i.tenant_id for i in self.db.query(ContactIdentity).filter_by(external_id=CUSTOMER)},
            {self.tenant_a.id, self.tenant_b.id},
        )
