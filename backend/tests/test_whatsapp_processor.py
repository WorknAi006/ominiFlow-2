"""
Tests for the WhatsApp event processor (event -> contact -> conversation
-> message), delivery statuses, outbound sending and end-to-end flow.
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import timedelta
from unittest import mock

from cryptography.fernet import Fernet
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import realtime_service
from app.services.realtime_service import inbox_channel
from app.models import (
    Contact,
    Conversation,
    ConversationStatus,
    Message,
    MessageDirection,
    WhatsAppEvent,
)
from app.services.credential_service import ChannelCredentialService
from app.services.whatsapp_event_processor import (
    ProcessOutcome,
    process_event,
    process_pending_events,
)
from tests.base import bearer
from tests.inbox_fixtures import (
    APP_SECRET,
    BASE_TIME,
    CUSTOMER,
    CUSTOMER_E164,
    PHONE_ID_A,
    TOKEN_A,
    TOKEN_B,
    WABA_A,
    InboxTestCase,
)


class _AppLogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record) + (record.exc_text or ""))

    def __enter__(self):
        root = logging.getLogger()
        self._level = root.level
        root.addHandler(self)
        root.setLevel(logging.DEBUG)
        return self

    def __exit__(self, *exc):
        root = logging.getLogger()
        root.removeHandler(self)
        root.setLevel(self._level)

    def text(self) -> str:
        return "\n".join(self.messages)


class ProcessorTestCase(InboxTestCase):

    def process(self, event) -> ProcessOutcome:
        session = self.make_session()
        try:
            return process_event(session, event.id)
        finally:
            session.close()

    def messages_for(self, tenant=None, **filters):
        self.db.expire_all()
        query = self.db.query(Message).filter_by(**filters)
        if tenant is not None:
            query = query.filter(Message.tenant_id == tenant.id)
        return query.all()

    def contacts_for(self, tenant):
        self.db.expire_all()
        return self.db.query(Contact).filter_by(tenant_id=tenant.id).all()

    def conversations_for(self, tenant):
        self.db.expire_all()
        return self.db.query(Conversation).filter_by(tenant_id=tenant.id).all()


# =========================
# INBOUND MESSAGES
# =========================

class InboundTests(ProcessorTestCase):

    def test_text_message_creates_contact_conversation_message(self):
        event = self.message_event(self.wa_a, self.text_message("wamid.T1", body="Hi Omniflow"))

        self.assertEqual(self.process(event), ProcessOutcome.PROCESSED)

        [contact] = self.contacts_for(self.tenant_a)
        self.assertEqual(contact.normalized_phone_number, CUSTOMER_E164)
        self.assertEqual(contact.external_identifier, CUSTOMER)
        self.assertEqual(contact.profile_name, "Jane Customer")

        [conversation] = self.conversations_for(self.tenant_a)
        self.assertEqual(conversation.contact_id, contact.id)
        self.assertEqual(conversation.channel_connection_id, self.wa_a.id)
        self.assertEqual(conversation.status, "open")
        self.assertEqual(conversation.unread_count, 1)
        self.assertEqual(conversation.last_message_at, BASE_TIME)

        [message] = self.messages_for(self.tenant_a)
        self.assertEqual(message.direction, "inbound")
        self.assertEqual(message.message_type, "text")
        self.assertEqual(message.text, "Hi Omniflow")
        self.assertEqual(message.status, "received")
        self.assertEqual(message.external_message_id, "wamid.T1")
        self.assertEqual(message.sender_identifier, CUSTOMER)
        self.assertEqual(message.recipient_identifier, PHONE_ID_A)
        self.assertEqual(message.sent_at, BASE_TIME)

        event = self.reload(WhatsAppEvent, event.id)
        self.assertEqual(event.processing_status, "processed")
        self.assertIsNotNone(event.processed_at)
        self.assertIsNone(event.processing_error)

    def test_media_messages(self):
        cases = {
            "image": {"id": "media-img", "mime_type": "image/jpeg", "sha256": "abc", "caption": "Look"},
            "video": {"id": "media-vid", "mime_type": "video/mp4", "caption": "Clip"},
            "audio": {"id": "media-aud", "mime_type": "audio/ogg", "voice": True},
            "document": {"id": "media-doc", "mime_type": "application/pdf",
                         "filename": "invoice.pdf", "caption": "Invoice"},
        }
        for whatsapp_type, media in cases.items():
            with self.subTest(type=whatsapp_type):
                external_id = f"wamid.{whatsapp_type}"
                message = self.text_message(external_id, type=whatsapp_type, **{whatsapp_type: media})
                message.pop("text")
                self.assertEqual(self.process(self.message_event(self.wa_a, message)), "processed")

                [stored] = self.messages_for(external_message_id=external_id)
                self.assertEqual(stored.message_type, whatsapp_type)
                self.assertEqual(stored.media_type, media["mime_type"])
                self.assertEqual(stored.media_metadata["id"], media["id"])
                self.assertEqual(stored.text, media.get("caption"))
                self.assertIsNone(stored.media_url)
                self.assertNotIn("caption", stored.media_metadata)

        self.assertEqual(len(self.conversations_for(self.tenant_a)), 1)
        self.assertEqual(self.conversations_for(self.tenant_a)[0].unread_count, 4)

    def test_location_message(self):
        location = {"latitude": 18.52, "longitude": 73.85, "name": "Office", "address": "Pune"}
        message = self.text_message("wamid.loc", type="location", location=location)
        message.pop("text")
        self.process(self.message_event(self.wa_a, message))

        [stored] = self.messages_for(external_message_id="wamid.loc")
        self.assertEqual(stored.message_type, "location")
        self.assertIsNone(stored.text)
        self.assertEqual(stored.message_metadata["location"], location)

    def test_unknown_message_type_stored_without_fake_content(self):
        message = self.text_message("wamid.stk", type="sticker", sticker={"id": "st-1"})
        message.pop("text")
        self.assertEqual(self.process(self.message_event(self.wa_a, message)), "processed")

        [stored] = self.messages_for(external_message_id="wamid.stk")
        self.assertEqual(stored.message_type, "unknown")
        self.assertIsNone(stored.text)
        self.assertIsNone(stored.media_metadata)
        self.assertEqual(stored.message_metadata, {"unsupported": True, "whatsapp_type": "sticker"})

    def test_same_customer_reuses_contact_and_conversation(self):
        self.process(self.message_event(self.wa_a, self.text_message("wamid.R1")))
        later = BASE_TIME + timedelta(minutes=3)
        self.process(self.message_event(self.wa_a, self.text_message("wamid.R2"), occurred_at=later))

        self.assertEqual(len(self.contacts_for(self.tenant_a)), 1)
        [conversation] = self.conversations_for(self.tenant_a)
        self.assertEqual(conversation.unread_count, 2)
        self.assertEqual(conversation.last_message_at, later)
        self.assertEqual(len(self.messages_for(self.tenant_a)), 2)

    def test_existing_contact_is_reused(self):
        existing = self.make_contact(self.tenant_a, CUSTOMER_E164, display_name="VIP Jane")
        self.db.commit()
        self.process(self.message_event(self.wa_a, self.text_message()))

        [contact] = self.contacts_for(self.tenant_a)
        self.assertEqual(contact.id, existing.id)
        self.assertEqual(contact.display_name, "VIP Jane")
        self.assertEqual(contact.profile_name, "Jane Customer")

    def test_reply_context_links_message(self):
        self.process(self.message_event(self.wa_a, self.text_message("wamid.orig")))
        self.process(self.message_event(
            self.wa_a, self.text_message("wamid.reply", context={"id": "wamid.orig"}),
        ))
        [original] = self.messages_for(external_message_id="wamid.orig")
        [reply] = self.messages_for(external_message_id="wamid.reply")
        self.assertEqual(reply.reply_to_message_id, original.id)

    def test_inbound_reopens_the_existing_conversation(self):
        self.process(self.message_event(self.wa_a, self.text_message("wamid.first")))
        [first] = self.conversations_for(self.tenant_a)
        first.status = ConversationStatus.RESOLVED
        self.db.commit()

        self.process(self.message_event(self.wa_a, self.text_message("wamid.second")))
        conversations = self.conversations_for(self.tenant_a)
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].id, first.id)
        self.assertEqual(conversations[0].status, "open")
        self.assertEqual(conversations[0].unread_count, 2)


# =========================
# IDEMPOTENCY AND SAFETY
# =========================

class IdempotencyTests(ProcessorTestCase):

    def test_duplicate_event_processing(self):
        event = self.message_event(self.wa_a, self.text_message("wamid.D1"))
        self.assertEqual(self.process(event), "processed")
        # Already processed: skipped.
        self.assertEqual(self.process(event), "skipped")

        # Forced replay (e.g. manual reset) still creates nothing new.
        stored = self.reload(WhatsAppEvent, event.id)
        stored.processing_status = "received"
        self.db.commit()
        self.assertEqual(self.process(event), "processed")

        self.assertEqual(len(self.messages_for(self.tenant_a)), 1)
        self.assertEqual(len(self.contacts_for(self.tenant_a)), 1)
        [conversation] = self.conversations_for(self.tenant_a)
        self.assertEqual(conversation.unread_count, 1)

    def test_duplicate_message_in_different_events(self):
        message = self.text_message("wamid.SAME")
        first = self.message_event(self.wa_a, message, dedupe_key="message:copy-1")
        second = self.message_event(self.wa_a, message, dedupe_key="message:copy-2")

        self.assertEqual(self.process(first), "processed")
        self.assertEqual(self.process(second), "processed")

        self.assertEqual(len(self.messages_for(external_message_id="wamid.SAME")), 1)
        self.assertEqual(self.conversations_for(self.tenant_a)[0].unread_count, 1)

    def test_same_external_id_on_other_tenant_channel_is_separate(self):
        self.process(self.message_event(self.wa_a, self.text_message("wamid.X")))
        self.process(self.message_event(self.wa_b, self.text_message("wamid.X")))
        self.assertEqual(len(self.messages_for(self.tenant_a, external_message_id="wamid.X")), 1)
        self.assertEqual(len(self.messages_for(self.tenant_b, external_message_id="wamid.X")), 1)

    def test_transaction_rollback_on_failure(self):
        event = self.message_event(self.wa_a, self.text_message("wamid.boom", body="secret text"))

        with mock.patch(
            "app.services.message_service.create_inbound_message",
            side_effect=RuntimeError("secret text exploded"),
        ):
            outcome = self.process(event)

        self.assertEqual(outcome, "failed")
        # Contact and conversation created before the failure were rolled back.
        self.assertEqual(self.contacts_for(self.tenant_a), [])
        self.assertEqual(self.conversations_for(self.tenant_a), [])
        stored = self.reload(WhatsAppEvent, event.id)
        self.assertEqual(stored.processing_status, "failed")
        self.assertEqual(stored.processing_error, "Unexpected error while processing event.")
        self.assertNotIn("secret", stored.processing_error)

    def test_invalid_channel_and_wrong_tenant(self):
        # Event claims tenant A but references tenant B's channel.
        wrong_tenant = self.message_event(self.wa_b, self.text_message(), tenant=self.tenant_a)
        # Event on a non-WhatsApp channel.
        wrong_type = self.message_event(self.ig_a, self.text_message())

        for event in (wrong_tenant, wrong_type):
            with self.subTest(event=str(event.id)):
                self.assertEqual(self.process(event), "failed")
                stored = self.reload(WhatsAppEvent, event.id)
                self.assertEqual(stored.processing_error, "Event channel is invalid for this tenant.")

        self.assertEqual(self.messages_for(), [])
        self.assertEqual(self.contacts_for(self.tenant_a), [])
        self.assertEqual(self.contacts_for(self.tenant_b), [])

    def test_ignored_events(self):
        cases = {
            "no sender": self.make_event(self.wa_a, "message", {"message": {"id": "wamid.ns", "type": "text"}}),
            "bad phone": self.message_event(self.wa_a, self.text_message(sender="abc")),
            "malformed": self.make_event(self.wa_a, "message", {"message": "nope"}),
            "error event": self.make_event(self.wa_a, "error", {"error": {"code": 1}}),
            "unknown status target": self.status_event(self.wa_a, "wamid.unknown", "delivered"),
            "unsupported status": self.status_event(self.wa_a, "wamid.any", "deleted"),
        }
        for name, event in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.process(event), "ignored")
                self.assertTrue(self.reload(WhatsAppEvent, event.id).processing_error)

        self.assertEqual(self.messages_for(), [])

    def test_process_pending_events(self):
        self.message_event(self.wa_a, self.text_message("wamid.P1"))
        self.message_event(self.wa_b, self.text_message("wamid.P2"))
        self.make_event(self.wa_a, "error", {"error": {}})

        session = self.make_session()
        try:
            counts = process_pending_events(session, limit=10)
            again = process_pending_events(session, limit=10)
        finally:
            session.close()

        self.assertEqual(counts, {"processed": 2, "ignored": 1})
        self.assertEqual(again, {})
        self.assertEqual(len(self.messages_for(self.tenant_a)), 1)
        self.assertEqual(len(self.messages_for(self.tenant_b)), 1)

    def test_tenant_isolation_of_processed_data(self):
        self.process(self.message_event(self.wa_b, self.text_message("wamid.B1")))
        self.assertEqual(self.contacts_for(self.tenant_a), [])
        self.assertEqual(len(self.contacts_for(self.tenant_b)), 1)

        headers = self.auth(self.owner, self.tenant_a)
        self.assertEqual(self.client.get("/api/v1/conversations", headers=headers).json()["total"], 0)
        self.assertEqual(self.client.get("/api/v1/contacts", headers=headers).json()["total"], 0)

    def test_message_content_not_logged(self):
        secret = f"private-{uuid.uuid4().hex}"
        with _AppLogCapture() as logs:
            self.process(self.message_event(self.wa_a, self.text_message(body=secret)))
        app_logs = "\n".join(m for m in logs.messages if "app." in m or "WhatsApp event" in m)
        self.assertIn("processed", app_logs)
        self.assertNotIn(secret, app_logs)
        self.assertNotIn(CUSTOMER, app_logs)


# =========================
# DELIVERY STATUSES
# =========================

class StatusTests(ProcessorTestCase):

    def setUp(self) -> None:
        super().setUp()
        contact = self.make_contact(self.tenant_a, CUSTOMER_E164)
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        self.outbound = self.make_message(
            conversation, "Order shipped", MessageDirection.OUTBOUND,
            status="sent", external_id="wamid.OUT1",
        )
        self.db.commit()

    def current(self):
        return self.reload(Message, self.outbound.id)

    def test_sent_delivered_read(self):
        for minutes, state in ((1, "sent"), (2, "delivered"), (3, "read")):
            event = self.status_event(self.wa_a, "wamid.OUT1", state,
                                      occurred_at=BASE_TIME + timedelta(minutes=minutes))
            self.assertEqual(self.process(event), "processed")
            self.assertEqual(self.current().status, state)

        message = self.current()
        self.assertEqual(message.sent_at, BASE_TIME + timedelta(minutes=1))
        self.assertEqual(message.delivered_at, BASE_TIME + timedelta(minutes=2))
        self.assertEqual(message.read_at, BASE_TIME + timedelta(minutes=3))

    def test_out_of_order_statuses_never_regress(self):
        self.process(self.status_event(self.wa_a, "wamid.OUT1", "read"))
        self.process(self.status_event(self.wa_a, "wamid.OUT1", "delivered",
                                       occurred_at=BASE_TIME + timedelta(minutes=9)))
        self.process(self.status_event(self.wa_a, "wamid.OUT1", "failed",
                                       errors=[{"code": 1, "title": "late"}]))
        message = self.current()
        self.assertEqual(message.status, "read")
        self.assertIsNotNone(message.delivered_at)
        self.assertIsNone(message.error_code)

    def test_failed_status(self):
        errors = [{
            "code": 131047,
            "title": "Re-engagement message",
            "error_data": {"details": "More than 24 hours have passed."},
        }]
        self.process(self.status_event(self.wa_a, "wamid.OUT1", "failed", errors=errors))
        message = self.current()
        self.assertEqual(message.status, "failed")
        self.assertEqual(message.error_code, "131047")
        self.assertEqual(message.error_message, "Re-engagement message; More than 24 hours have passed.")
        self.assertIsNotNone(message.failed_at)

    def test_status_from_other_tenant_channel_does_not_apply(self):
        event = self.status_event(self.wa_b, "wamid.OUT1", "read")
        self.assertEqual(self.process(event), "ignored")
        self.assertEqual(self.current().status, "sent")


# =========================
# OUTBOUND
# =========================

class OutboundTests(ProcessorTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.contact = self.make_contact(self.tenant_a, CUSTOMER_E164)
        self.conversation = self.make_conversation(self.tenant_a, self.contact, self.wa_a)
        self.inbound = self.make_message(self.conversation, "Where is my order?", external_id="wamid.ASK")
        contact_b = self.make_contact(self.tenant_b, CUSTOMER_E164)
        self.conversation_b = self.make_conversation(self.tenant_b, contact_b, self.wa_b)
        self.db.commit()

    def send(self, body=None, actor=None, conversation=None):
        conversation = conversation or self.conversation
        headers = self.auth(actor or self.agent, self.tenant_a)
        headers["Idempotency-Key"] = str(uuid.uuid4())
        return self.client.post(
            f"/api/v1/conversations/{conversation.id}/messages",
            headers=headers,
            json=body if body is not None else {"type": "text", "text": "Your order ships today."},
        )

    def assert_no_credentials(self, text):
        for secret in (TOKEN_A, TOKEN_B, APP_SECRET, "access_token", "_encrypted"):
            self.assertNotIn(secret, text)

    def updates_for_conversation(self, conversation):
        channel = inbox_channel(conversation.tenant_id)
        events = [
            json.loads(payload)
            for published_channel, payload in self.realtime.published
            if published_channel == channel
        ]
        return [
            event for event in events
            if event.get("event") == "conversation.updated"
            and event.get("conversation_id") == str(conversation.id)
        ]

    def test_successful_send(self):
        response = self.send()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["direction"], "outbound")
        self.assertEqual(body["status"], "sent")
        self.assertTrue(body["external_message_id"].startswith("wamid.OUT"))
        self.assertEqual(body["sent_by_user_id"], str(self.agent.id))
        self.assertEqual(body["text"], "Your order ships today.")
        self.assert_no_credentials(response.text)

        [update] = self.updates_for_conversation(self.conversation)
        self.assertEqual(update["tenant_id"], str(self.tenant_a.id))
        self.assertEqual(update["conversation_id"], str(self.conversation.id))
        self.assertEqual(update["data"]["last_message_id"], body["id"])
        self.assertEqual(update["data"]["last_message_direction"], "outbound")
        self.assertEqual(update["data"]["last_message_type"], "text")
        self.assertEqual(update["data"]["last_message_preview"], "Your order ships today.")
        self.assertEqual(update["data"]["unread_count"], 0)

        [request] = self.send_api.requests
        self.assertEqual(request.url.path, f"/v23.0/{PHONE_ID_A}/messages")
        self.assertEqual(request.headers["authorization"], f"Bearer {TOKEN_A}")
        self.assertNotIn(TOKEN_A, str(request.url))
        sent = json.loads(request.content)
        self.assertEqual(sent["to"], CUSTOMER)
        self.assertEqual(sent["text"]["body"], "Your order ships today.")

        conversation = self.reload(Conversation, self.conversation.id)
        self.assertIsNotNone(conversation.last_message_at)
        self.assertEqual(update["data"]["last_message_at"], conversation.last_message_at.isoformat())
        self.assertEqual(conversation.unread_count, 0)

        listing = self.client.get(
            f"/api/v1/conversations/{self.conversation.id}/messages",
            headers=self.auth(self.viewer, self.tenant_a),
        ).json()
        self.assertEqual(listing["items"][0]["id"], body["id"])

    def test_conversation_update_is_published_after_final_commit(self):
        order = []
        original_commit = Session.commit
        original_publish = realtime_service.publish_event

        def tracked_commit(session):
            result = original_commit(session)
            order.append("commit")
            return result

        def tracked_publish(event):
            order.append("publish")
            return original_publish(event)

        with mock.patch.object(Session, "commit", new=tracked_commit), mock.patch.object(
            realtime_service, "publish_event", side_effect=tracked_publish,
        ):
            response = self.send()

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(order[-2:], ["commit", "publish"])

    def test_failed_final_commit_does_not_publish_success_update(self):
        original_commit = Session.commit
        commits = 0

        def fail_final_commit(session):
            nonlocal commits
            commits += 1
            if commits == 2:
                raise SQLAlchemyError("synthetic transaction failure")
            return original_commit(session)

        with mock.patch.object(Session, "commit", new=fail_final_commit):
            response = self.send()

        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(commits, 2)
        self.assertEqual(self.updates_for_conversation(self.conversation), [])

    def test_reply_to_inbound_message(self):
        response = self.send({"type": "text", "text": "Checking now", "reply_to_message_id": str(self.inbound.id)})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["reply_to_message_id"], str(self.inbound.id))
        self.assertEqual(json.loads(self.send_api.requests[0].content)["context"], {"message_id": "wamid.ASK"})

        other = self.make_message(self.conversation_b, "other tenant")
        self.db.commit()
        response = self.send({"type": "text", "text": "x", "reply_to_message_id": str(other.id)})
        self.assertEqual(response.status_code, 422)

    def test_provider_rejection(self):
        self.send_api.fail_with = (400, "(#131047) Re-engagement message. Token {token}", 131047)
        response = self.send()
        self.assertEqual(response.status_code, 502)
        self.assertIn("WhatsApp rejected the message", response.text)
        self.assert_no_credentials(response.text)

        [message] = self.messages_for(direction="outbound")
        self.assertEqual(message.status, "failed")
        self.assertEqual(message.error_code, "131047")
        self.assertIn("[redacted]", message.error_message)
        self.assertNotIn(TOKEN_A, message.error_message)
        self.assertIsNotNone(message.failed_at)
        self.assertEqual(self.updates_for_conversation(self.conversation), [])

    def test_provider_unreachable(self):
        self.send_api.network_down = True
        response = self.send()
        self.assertEqual(response.status_code, 502)
        [message] = self.messages_for(direction="outbound")
        self.assertEqual(message.status, "pending")
        self.assertEqual(self.updates_for_conversation(self.conversation), [])

    def test_rejected_before_any_provider_call(self):
        cases = {}

        channel = self.reload(type(self.wa_a), self.wa_a.id)
        channel.status = "disconnected"
        self.db.commit()
        cases["disconnected"] = (self.send(), 409)
        channel.status = "connected"
        channel.is_active = False
        self.db.commit()
        cases["inactive"] = (self.send(), 409)
        channel.is_active = True
        self.db.commit()

        # Instagram is a real provider now, but this contact has no Instagram
        # identity, so the recipient cannot be resolved (409), still rejected
        # before any provider call.
        ig_conversation = self.make_conversation(self.tenant_a, self.contact, self.ig_a)
        self.db.commit()
        cases["channel without contact identity"] = (self.send(conversation=ig_conversation), 409)

        contact = self.reload(Contact, self.contact.id)
        contact.is_blocked = True
        self.db.commit()
        cases["blocked contact"] = (self.send(), 409)
        contact.is_blocked = False
        self.db.commit()

        cases["other tenant conversation"] = (self.send(conversation=self.conversation_b), 404)

        for name, (response, expected) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(response.status_code, expected, response.text)
                self.assert_no_credentials(response.text)

        self.assertEqual(self.send_api.requests, [])
        self.assertEqual(self.messages_for(direction="outbound"), [])
        self.assertEqual(self.updates_for_conversation(self.conversation), [])
        self.assertEqual(self.updates_for_conversation(self.conversation_b), [])

    def test_invalid_conversation_ids(self):
        headers = self.auth(self.agent, self.tenant_a)
        headers["Idempotency-Key"] = str(uuid.uuid4())
        body = {"type": "text", "text": "hi"}
        self.assertEqual(
            self.client.post(f"/api/v1/conversations/{uuid.uuid4()}/messages", headers=headers, json=body).status_code,
            404,
        )
        self.assertEqual(
            self.client.post("/api/v1/conversations/not-a-uuid/messages", headers={**headers, "Idempotency-Key": str(uuid.uuid4())}, json=body).status_code,
            422,
        )

    def test_token_decryption_failure(self):
        channel = self.reload(type(self.wa_a), self.wa_a.id)
        channel.access_token_encrypted = ChannelCredentialService(
            [Fernet.generate_key().decode()]
        ).encrypt(TOKEN_A)
        self.db.commit()

        response = self.send()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Channel credentials are unavailable. Reconnect the channel."})
        self.assertEqual(self.send_api.requests, [])
        self.assertEqual(self.messages_for(direction="outbound"), [])

    def test_not_configured(self):
        settings.meta_app_secret = ""
        try:
            response = self.send()
        finally:
            settings.meta_app_secret = APP_SECRET
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.send_api.requests, [])

    def test_validation(self):
        invalid = [
            {"type": "text", "text": ""},
            {"type": "text", "text": "   "},
            {"type": "text", "text": "x" * 4097},
            {"type": "image", "text": "x"},
            {"text": "x"},
            {"type": "text", "text": "x", "tenant_id": str(self.tenant_b.id)},
            {"type": "text", "text": "x", "reply_to_message_id": "nope"},
        ]
        for body in invalid:
            with self.subTest(body=str(body)[:40]):
                self.assertEqual(self.send(body).status_code, 422)
        self.assertEqual(self.send({"type": "text", "text": "x" * 4096}).status_code, 201)

    def test_rbac(self):
        for actor in (self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.send(actor=actor).status_code, 403)
        for actor in (self.agent, self.manager, self.admin, self.owner):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.send(actor=actor).status_code, 201)

    def test_status_webhook_updates_sent_message(self):
        external_id = self.send().json()["external_message_id"]
        self.process(self.status_event(self.wa_a, external_id, "delivered"))
        self.process(self.status_event(self.wa_a, external_id, "read"))
        [message] = self.messages_for(external_message_id=external_id)
        self.assertEqual(message.status, "read")

    def test_credentials_not_logged(self):
        with _AppLogCapture() as logs:
            self.send()
            self.send_api.fail_with = (400, "bad {token}", 100)
            self.send()
        self.assert_no_credentials(logs.text())


# =========================
# END TO END
# =========================

class EndToEndTests(ProcessorTestCase):

    def test_webhook_to_inbox_to_reply(self):
        body = {
            "object": "whatsapp_business_account",
            "entry": [{"id": WABA_A, "changes": [{"field": "messages", "value": {
                "messaging_product": "whatsapp",
                "metadata": {"phone_number_id": PHONE_ID_A},
                "contacts": [{"wa_id": CUSTOMER, "profile": {"name": "Jane Customer"}}],
                "messages": [self.text_message("wamid.E2E", body="Is my order ready?")],
            }}]}],
        }
        raw = json.dumps(body).encode()
        signature = "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        response = self.client.post(
            "/api/v1/webhooks/whatsapp", content=raw,
            headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)

        session = self.make_session()
        try:
            self.assertEqual(process_pending_events(session), {"processed": 1})
        finally:
            session.close()

        headers = self.auth(self.agent, self.tenant_a)
        headers["Idempotency-Key"] = str(uuid.uuid4())
        inbox = self.client.get("/api/v1/conversations", headers=headers).json()
        self.assertEqual(inbox["total"], 1)
        [item] = inbox["items"]
        self.assertEqual(item["contact"]["name"], "Jane Customer")
        self.assertEqual(item["contact"]["phone_number"], CUSTOMER_E164)
        self.assertEqual(item["unread_count"], 1)
        self.assertEqual(item["last_message"]["text"], "Is my order ready?")
        self.assertEqual(item["channel"]["id"], str(self.wa_a.id))

        reply = self.client.post(
            f"/api/v1/conversations/{item['id']}/messages",
            headers=headers, json={"type": "text", "text": "Yes, it ships today!"},
        )
        self.assertEqual(reply.status_code, 201)

        read = self.client.post(f"/api/v1/conversations/{item['id']}/read", headers=headers).json()
        self.assertEqual(read["unread_count"], 0)
        self.assertEqual(read["last_message"]["text"], "Yes, it ships today!")
        self.assertEqual(read["last_message"]["direction"], "outbound")

        # Tenant B sees nothing.
        other = self.client.get("/api/v1/conversations", headers=self.auth(self.owner_b, self.tenant_b)).json()
        self.assertEqual(other["total"], 0)
        self.assertEqual(
            self.client.get(f"/api/v1/conversations/{item['id']}",
                            headers=self.auth(self.owner_b, self.tenant_b)).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/conversations/{item['id']}",
                            headers=bearer("bad.jwt")).status_code,
            401,
        )
