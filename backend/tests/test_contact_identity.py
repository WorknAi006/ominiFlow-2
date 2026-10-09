"""
Contact identities and the generic outbound send path.

Covers the Task 1 contract: a Contact (person) is decoupled from its
per-channel ContactIdentity, WhatsApp keeps resolving by wa_id, and
outbound text goes through ChannelProvider.send_text without any
WhatsApp-specific branching in the generic service.
"""
import uuid
from unittest import mock

from app.models import (
    ChannelType,
    Contact,
    ContactIdentity,
    Conversation,
    MessageStatus,
)
from app.schemas.message import TextMessageCreate
from app.services import contact_service, outbound_message_service
from app.services.outbound_message_service import RecipientUnavailableError
from app.services.whatsapp_event_processor import ProcessOutcome, process_event
from tests.inbox_fixtures import CUSTOMER, CUSTOMER_E164, InboxTestCase


class ContactIdentityResolverTests(InboxTestCase):

    def identities(self, tenant, channel_type=None, external_id=None):
        self.db.expire_all()
        query = self.db.query(ContactIdentity).filter_by(tenant_id=tenant.id)
        if channel_type is not None:
            query = query.filter_by(channel_type=str(channel_type))
        if external_id is not None:
            query = query.filter_by(external_id=external_id)
        return query.all()

    # Test 1
    def test_same_tenant_channel_external_resolves_to_one_contact(self):
        first = contact_service.get_or_create_by_identity(
            self.db, self.tenant_a.id, ChannelType.WHATSAPP, "wa-ext-1",
        )
        second = contact_service.get_or_create_by_identity(
            self.db, self.tenant_a.id, ChannelType.WHATSAPP, "wa-ext-1",
        )
        self.assertEqual(first.id, second.id)
        rows = self.identities(self.tenant_a, ChannelType.WHATSAPP, "wa-ext-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].contact_id, first.id)

    # Test 2
    def test_same_external_id_different_channel_is_channel_specific(self):
        wa_contact = contact_service.get_or_create_by_identity(
            self.db, self.tenant_a.id, ChannelType.WHATSAPP, "shared-ext",
        )
        ig_contact = contact_service.get_or_create_by_identity(
            self.db, self.tenant_a.id, ChannelType.INSTAGRAM, "shared-ext",
        )
        rows = self.identities(self.tenant_a, external_id="shared-ext")
        self.assertEqual({row.channel_type for row in rows}, {"whatsapp", "instagram"})
        self.assertEqual(len(rows), 2)
        # No cross-channel auto-merge yet: each identity owns its own contact.
        self.assertNotEqual(wa_contact.id, ig_contact.id)

    # Test 3
    def test_same_external_id_different_tenants_are_separate(self):
        a_contact = contact_service.get_or_create_by_identity(
            self.db, self.tenant_a.id, ChannelType.WHATSAPP, "dup-ext",
        )
        b_contact = contact_service.get_or_create_by_identity(
            self.db, self.tenant_b.id, ChannelType.WHATSAPP, "dup-ext",
        )
        self.assertNotEqual(a_contact.id, b_contact.id)
        self.assertEqual(a_contact.tenant_id, self.tenant_a.id)
        self.assertEqual(b_contact.tenant_id, self.tenant_b.id)
        self.assertEqual(len(self.identities(self.tenant_a, external_id="dup-ext")), 1)
        self.assertEqual(len(self.identities(self.tenant_b, external_id="dup-ext")), 1)


class WhatsAppInboundIdentityTests(InboxTestCase):

    def process(self, event) -> ProcessOutcome:
        session = self.make_session()
        try:
            return process_event(session, event.id)
        finally:
            session.close()

    # Test 4
    def test_two_inbound_from_same_wa_id_make_one_contact_and_identity(self):
        first = self.message_event(self.wa_a, self.text_message(message_id="wamid.IN1", sender=CUSTOMER))
        second = self.message_event(self.wa_a, self.text_message(message_id="wamid.IN2", sender=CUSTOMER))

        self.assertEqual(self.process(first), ProcessOutcome.PROCESSED)
        self.assertEqual(self.process(second), ProcessOutcome.PROCESSED)

        self.db.expire_all()
        contacts = (
            self.db.query(Contact)
            .filter_by(tenant_id=self.tenant_a.id, normalized_phone_number=CUSTOMER_E164)
            .all()
        )
        self.assertEqual(len(contacts), 1)

        identities = (
            self.db.query(ContactIdentity)
            .filter_by(tenant_id=self.tenant_a.id, channel_type="whatsapp", external_id=CUSTOMER)
            .all()
        )
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0].contact_id, contacts[0].id)

        conversations = (
            self.db.query(Conversation).filter_by(tenant_id=self.tenant_a.id).all()
        )
        self.assertEqual(len(conversations), 1)


class GenericOutboundSendTests(InboxTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.contact = self.make_contact(self.tenant_a, CUSTOMER_E164)
        self.conversation = self.make_conversation(self.tenant_a, self.contact, self.wa_a)
        self.ig_conversation = self.make_conversation(self.tenant_a, self.contact, self.ig_a)
        self.db.commit()

    def send(self, conversation_id, text, idempotency_key=None):
        """Send through the service on a fresh session, as a request would."""
        session = self.make_session()
        try:
            return outbound_message_service.send_message(
                session,
                self.tenant_a.id,
                self.owner,
                conversation_id,
                TextMessageCreate(type="text", text=text),
                idempotency_key=idempotency_key,
            )
        finally:
            session.close()

    # Test 5
    def test_whatsapp_text_send_goes_through_provider_send_text(self):
        with mock.patch.object(
            self.provider, "send_text", wraps=self.provider.send_text,
        ) as spy:
            result = self.send(self.conversation.id, "Hello from the generic path.")
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(result.status, MessageStatus.SENT)
        self.assertTrue(result.external_message_id.startswith("wamid.OUT"))
        self.assertEqual(len(self.send_api.requests), 1)

    # Test 6
    def test_whatsapp_idempotency_sends_once(self):
        key = uuid.uuid4()
        first = self.send(self.conversation.id, "Only once please.", idempotency_key=key)
        second = self.send(self.conversation.id, "Only once please.", idempotency_key=key)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.status, MessageStatus.SENT)
        # The provider was called exactly once for the reused key.
        self.assertEqual(len(self.send_api.requests), 1)

    # Test 7
    def test_send_on_channel_without_contact_identity_fails_cleanly(self):
        # Instagram is a real provider now, but this contact has no Instagram
        # identity, so the recipient cannot be resolved. It fails before any
        # provider HTTP call rather than guessing an address.
        with self.assertRaises(RecipientUnavailableError):
            self.send(self.ig_conversation.id, "No Instagram identity for this contact.")
        self.assertEqual(self.send_api.requests, [])


class WhatsAppContactApiStillWorksTests(InboxTestCase):

    # Test 8
    def test_existing_contact_apis_still_work(self):
        headers = self.auth(self.owner, self.tenant_a)

        created = self.client.post(
            "/api/v1/contacts",
            headers=headers,
            json={"phone_number": "+14155550123", "first_name": "Zoe"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()
        self.assertEqual(body["normalized_phone_number"], "+14155550123")

        fetched = self.client.get(f"/api/v1/contacts/{body['id']}", headers=headers)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["name"], "Zoe")

        listing = self.client.get("/api/v1/contacts", headers=headers)
        self.assertEqual(listing.status_code, 200)
        self.assertIn(body["id"], {item["id"] for item in listing.json()["items"]})
