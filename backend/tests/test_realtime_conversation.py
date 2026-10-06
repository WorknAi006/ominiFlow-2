"""
Tests for realtime conversation.updated: published after commit with the
conversation-list state (unread count, last activity, latest message
preview), never for duplicates, tenant-scoped, no secrets or PII.
"""
import json
from datetime import timedelta
from unittest import mock

from sqlalchemy import event as sa_event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Conversation, Message, MessageDirection
from app.services import realtime_service
from app.services.realtime_service import InMemoryBroker, RedisBroker, inbox_channel
from tests.inbox_fixtures import APP_SECRET, BASE_TIME, CUSTOMER, CUSTOMER_E164, TOKEN_A, TOKEN_B
from tests.test_realtime import RealtimeTestCase

DATA_FIELDS = {
    "status", "unread_count", "last_message_at", "last_message_id",
    "last_message_direction", "last_message_type", "last_message_preview",
}


class ConversationEventTestCase(RealtimeTestCase):

    def updates(self, tenant=None):
        return self.published(tenant, event_type="conversation.updated")

    def inbound_at(self, minutes, body, channel=None, message_id=None):
        message = self.text_message(message_id, body=body)
        message["timestamp"] = str(int((BASE_TIME + timedelta(minutes=minutes)).timestamp()))
        return self.message_event(
            channel or self.wa_a, message, occurred_at=BASE_TIME + timedelta(minutes=minutes),
        )

    def conversation(self, tenant=None):
        self.db.expire_all()
        return self.db.query(Conversation).filter_by(tenant_id=(tenant or self.tenant_a).id).one()

    def mark_read(self, conversation=None, actor=None, tenant=None):
        conversation = conversation or self.conversation(tenant)
        tenant = tenant or self.tenant_a
        actor = actor or self.agent
        return self.client.post(
            f"/api/v1/conversations/{conversation.id}/read",
            headers=self.auth(actor, tenant),
        )


class ConversationUpdatedTests(ConversationEventTestCase):

    def test_payload_after_first_message(self):
        self.assertEqual(self.process(self.inbound_at(0, "Hello Omniflow")), "processed")

        [update] = self.updates()
        message = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).one()

        self.assertEqual(set(update), {"event", "event_id", "tenant_id", "conversation_id", "timestamp", "data"})
        self.assertEqual(set(update["data"]), DATA_FIELDS)
        self.assertEqual(update["tenant_id"], str(self.tenant_a.id))
        self.assertEqual(update["conversation_id"], str(message.conversation_id))
        self.assertEqual(update["data"], {
            "status": "open",
            "unread_count": 1,
            "last_message_at": BASE_TIME.isoformat(),
            "last_message_id": str(message.id),
            "last_message_direction": "inbound",
            "last_message_type": "text",
            "last_message_preview": "Hello Omniflow",
        })

        # message.created first, then conversation.updated, same channel.
        events = self.published(event_type=None)
        self.assertEqual([e["event"] for e in events], ["message.created", "conversation.updated"])
        self.assertEqual({c for c, _ in self.realtime.published}, {inbox_channel(self.tenant_a.id)})

    def test_mark_read_publishes_snapshot_and_preserves_message_statuses(self):
        self.process(self.inbound_at(0, "Customer message"))
        conversation = self.conversation()
        inbound = self.db.query(Message).filter_by(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
        ).one()
        outbound = self.make_message(
            conversation,
            "Agent reply",
            MessageDirection.OUTBOUND,
            status="sent",
            external_id="wamid.READTEST",
        )
        self.db.commit()

        response = self.mark_read(conversation)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["unread_count"], 0)
        [update] = self.updates()[-1:]
        self.assertEqual(update["tenant_id"], str(self.tenant_a.id))
        self.assertEqual(update["conversation_id"], str(conversation.id))
        self.assertEqual(update["data"]["unread_count"], 0)
        self.assertEqual(update["data"]["last_message_id"], str(outbound.id))
        self.assertEqual(update["data"]["last_message_direction"], "outbound")
        self.assertEqual(update["data"]["last_message_preview"], "Agent reply")

        self.db.refresh(inbound)
        self.db.refresh(outbound)
        self.assertEqual((inbound.status, inbound.read_at), ("received", None))
        self.assertEqual((outbound.status, outbound.read_at), ("sent", None))
        self.assertEqual(self.conversation().unread_count, 0)

        event_count = len(self.updates())
        repeated = self.mark_read(conversation)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()["unread_count"], 0)
        self.assertEqual(len(self.updates()), event_count)


class MarkReadReliabilityTests(ConversationEventTestCase):

    def test_read_update_publishes_after_commit(self):
        self.process(self.inbound_at(0, "Unread"))
        order: list[str] = []

        def after_commit(_session):
            order.append("commit")

        class OrderedBroker(InMemoryBroker):
            def publish(self, channel, payload):
                order.append(json.loads(payload)["event"])
                super().publish(channel, payload)

        sa_event.listen(Session, "after_commit", after_commit)
        realtime_service.set_broker(OrderedBroker())
        try:
            response = self.mark_read()
        finally:
            sa_event.remove(Session, "after_commit", after_commit)
            realtime_service.set_broker(self.realtime)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(order[-2:], ["commit", "conversation.updated"])

    def test_read_transaction_failure_does_not_publish_success(self):
        self.process(self.inbound_at(0, "Unread"))
        updates_before = len(self.updates())

        with mock.patch.object(Session, "commit", side_effect=SQLAlchemyError("synthetic failure")):
            response = self.mark_read()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(self.updates()), updates_before)
        self.assertEqual(self.conversation().unread_count, 1)

    def test_unread_and_preview_follow_new_messages(self):
        self.process(self.inbound_at(0, "First"))
        self.process(self.inbound_at(2, "Second"))

        latest = self.updates()[-1]["data"]
        self.assertEqual(latest["unread_count"], 2)
        self.assertEqual(latest["last_message_preview"], "Second")
        self.assertEqual(latest["last_message_at"], (BASE_TIME + timedelta(minutes=2)).isoformat())
        self.assertEqual(self.conversation().unread_count, 2)

    def test_duplicate_webhook_no_double_increment_or_event(self):
        self.process(self.inbound_at(0, "Once", message_id="wamid.DUP"))
        # Same WhatsApp message delivered again as a separate event row.
        replay = self.message_event(
            self.wa_a, self.text_message("wamid.DUP", body="Once"), dedupe_key="message:replay",
        )
        self.assertEqual(self.process(replay), "processed")

        self.assertEqual(len(self.updates()), 1)
        self.assertEqual(self.conversation().unread_count, 1)

    def test_out_of_order_keeps_newer_data(self):
        self.process(self.inbound_at(5, "Newer message", message_id="wamid.NEW"))
        self.process(self.inbound_at(1, "Older message", message_id="wamid.OLD"))

        newer = self.db.query(Message).filter_by(external_message_id="wamid.NEW").one()
        latest = self.updates()[-1]["data"]
        self.assertEqual(latest["unread_count"], 2)
        self.assertEqual(latest["last_message_at"], (BASE_TIME + timedelta(minutes=5)).isoformat())
        self.assertEqual(latest["last_message_id"], str(newer.id))
        self.assertEqual(latest["last_message_preview"], "Newer message")

        # The conversation list API agrees with the event.
        listing = self.client.get("/api/v1/conversations", headers=self.auth(self.owner, self.tenant_a)).json()
        self.assertEqual(listing["items"][0]["last_message"]["id"], str(newer.id))
        self.assertEqual(listing["items"][0]["last_message"]["text"], "Newer message")

    def test_preview_sanitized_and_bounded(self):
        # (NUL is not storable in PostgreSQL text/JSONB, so other control
        # characters are used here.)
        body = "Line one\nline\ttwo\x1b\x07\r  " + "x" * 500
        self.process(self.inbound_at(0, body))
        preview = self.updates()[0]["data"]["last_message_preview"]
        self.assertTrue(preview.startswith("Line one line two x"))
        self.assertLessEqual(len(preview), 200)
        for bad in ("\n", "\t", "\r", "\x1b", "\x07", "  "):
            self.assertNotIn(bad, preview)

    def test_media_without_caption_has_no_preview(self):
        message = self.text_message(type="image", image={"id": "media-1", "mime_type": "image/jpeg"})
        message.pop("text")
        self.process(self.message_event(self.wa_a, message))
        data = self.updates()[0]["data"]
        self.assertEqual((data["last_message_type"], data["last_message_preview"]), ("image", None))

    def test_status_and_ignored_events_publish_no_conversation_update(self):
        contact = self.make_contact(self.tenant_a, CUSTOMER_E164)
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        self.make_message(conversation, "Out", MessageDirection.OUTBOUND, status="sent", external_id="wamid.OUT")
        self.db.commit()

        self.process(self.status_event(self.wa_a, "wamid.OUT", "delivered"))
        self.process(self.make_event(self.wa_a, "error", {"error": {}}))
        self.process(self.message_event(self.wa_a, self.text_message(sender="not-a-phone")))
        self.assertEqual(self.updates(), [])

    def test_no_secrets_or_contact_pii(self):
        self.process(self.inbound_at(0, "Hello"))
        raw = json.dumps(self.updates()[0])
        for fragment in (TOKEN_A, TOKEN_B, APP_SECRET, "access_token", "_encrypted", "password",
                         CUSTOMER, "Jane Customer", "metadata", "phone_number_id", "messaging_product"):
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, raw)


class ConversationReliabilityTests(ConversationEventTestCase):

    def test_published_only_after_commit(self):
        order: list[str] = []
        session = self.make_session()
        sa_event.listen(session, "after_commit", lambda s: order.append("commit"))

        class OrderedBroker(InMemoryBroker):
            def publish(self, channel, payload):
                order.append(json.loads(payload)["event"])
                super().publish(channel, payload)

        realtime_service.set_broker(OrderedBroker())
        try:
            self.process(self.inbound_at(0, "Hi"), session=session)
        finally:
            session.close()
            realtime_service.set_broker(self.realtime)

        self.assertEqual(order[-3:], ["commit", "message.created", "conversation.updated"])

    def test_no_event_when_transaction_fails(self):
        with mock.patch(
            "app.services.conversation_service.get_update_snapshot",
            side_effect=RuntimeError("snapshot failed"),
        ):
            self.assertEqual(self.process(self.inbound_at(0, "Lost")), "failed")

        self.assertEqual(self.realtime.published, [])
        self.assertEqual(self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).count(), 0)
        self.assertEqual(self.db.query(Conversation).filter_by(tenant_id=self.tenant_a.id).count(), 0)

    def test_redis_unavailable_keeps_committed_state(self):
        realtime_service.set_broker(RedisBroker("redis://:supersecretpass@127.0.0.1:1/0", timeout=0.5))
        try:
            self.assertEqual(self.process(self.inbound_at(0, "Stored")), "processed")
        finally:
            realtime_service.set_broker(self.realtime)

        conversation = self.conversation()
        self.assertEqual(conversation.unread_count, 1)
        self.assertEqual(conversation.last_message_at, BASE_TIME)


class ConversationIsolationTests(ConversationEventTestCase):

    def test_events_only_on_owning_tenant_channel(self):
        self.process(self.inbound_at(0, "For B", channel=self.wa_b))
        self.assertEqual(self.updates(self.tenant_a), [])
        [update] = self.updates(self.tenant_b)
        self.assertEqual(update["tenant_id"], str(self.tenant_b.id))
        self.assertEqual(update["conversation_id"], str(self.conversation(self.tenant_b).id))

    def test_mark_read_event_uses_authenticated_tenant_channel(self):
        self.process(self.inbound_at(0, "For B", channel=self.wa_b))
        conversation_b = self.conversation(self.tenant_b)

        response = self.mark_read(
            conversation_b,
            actor=self.owner_b,
            tenant=self.tenant_b,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.updates(self.tenant_a), [])
        [update] = self.updates(self.tenant_b)[-1:]
        self.assertEqual(update["tenant_id"], str(self.tenant_b.id))
        self.assertEqual(update["conversation_id"], str(conversation_b.id))
        self.assertEqual(update["data"]["unread_count"], 0)

    def test_websocket_delivery_and_isolation(self):
        ws_a = self.connect(self.viewer, self.tenant_a)
        ws_b = self.connect(self.owner_b, self.tenant_b)

        self.process(self.inbound_at(0, "Hello A"))
        self.process(self.inbound_at(0, "Hello B", channel=self.wa_b))

        received_b = [ws_b.receive_json(), ws_b.receive_json()]
        self.assertEqual([e["event"] for e in received_b], ["message.created", "conversation.updated"])
        self.assertTrue(all(e["tenant_id"] == str(self.tenant_b.id) for e in received_b))

        received_a = [ws_a.receive_json(), ws_a.receive_json()]
        self.assertEqual([e["event"] for e in received_a], ["message.created", "conversation.updated"])
        self.assertEqual(received_a[1], self.updates(self.tenant_a)[0])
        self.assertEqual(received_a[1]["data"]["last_message_preview"], "Hello A")
