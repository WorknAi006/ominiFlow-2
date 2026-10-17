"""
Tests for realtime message.status_changed: published after commit,
only on real status changes, tenant-scoped, safe payload.
"""
import json
import logging
from datetime import timedelta
from unittest import mock

from sqlalchemy import event as sa_event

from app.models import Message, MessageDirection
from app.services import realtime_service
from app.services.realtime_service import InMemoryBroker, RedisBroker, inbox_channel
from tests.inbox_fixtures import APP_SECRET, BASE_TIME, CUSTOMER_E164, TOKEN_A, TOKEN_B
from tests.test_realtime import RealtimeTestCase

STATUS_FIELDS = {"status", "sent_at", "delivered_at", "read_at", "failed_at", "error_code", "error_message"}


class StatusTestCase(RealtimeTestCase):

    def setUp(self) -> None:
        super().setUp()
        contact = self.make_contact(self.tenant_a, CUSTOMER_E164)
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        self.outbound = self.make_message(
            conversation, "Your order shipped", MessageDirection.OUTBOUND,
            status="pending", external_id="wamid.OUT-A",
        )
        contact_b = self.make_contact(self.tenant_b, CUSTOMER_E164)
        conversation_b = self.make_conversation(self.tenant_b, contact_b, self.wa_b)
        self.outbound_b = self.make_message(
            conversation_b, "Tenant B message", MessageDirection.OUTBOUND,
            status="pending", external_id="wamid.OUT-B",
        )
        self.db.commit()

    def status(self, state, minutes=1, external_id="wamid.OUT-A", channel=None, **kwargs):
        return self.status_event(
            channel or self.wa_a, external_id, state,
            occurred_at=BASE_TIME + timedelta(minutes=minutes), **kwargs,
        )

    def status_events(self, tenant=None):
        return self.published(tenant, event_type="message.status_changed")

    def current(self):
        return self.reload(Message, self.outbound.id)


class StatusPublishTests(StatusTestCase):

    def test_sent_delivered_read_each_publish(self):
        for minutes, state in ((1, "sent"), (2, "delivered"), (3, "read")):
            with self.subTest(state=state):
                self.assertEqual(self.process(self.status(state, minutes)), "processed")
                event = self.status_events()[-1]
                self.assertEqual(event["data"]["status"], state)
                self.assertEqual(self.current().status, state)

        events = self.status_events()
        self.assertEqual([e["data"]["status"] for e in events], ["sent", "delivered", "read"])

        final = events[-1]
        self.assertEqual(set(final), {"event", "event_id", "tenant_id", "conversation_id", "message_id", "timestamp", "data"})
        self.assertEqual(set(final["data"]), STATUS_FIELDS)
        self.assertEqual(final["tenant_id"], str(self.tenant_a.id))
        self.assertEqual(final["message_id"], str(self.outbound.id))
        self.assertEqual(final["conversation_id"], str(self.outbound.conversation_id))
        self.assertEqual(final["data"]["sent_at"], (BASE_TIME + timedelta(minutes=1)).isoformat())
        self.assertEqual(final["data"]["delivered_at"], (BASE_TIME + timedelta(minutes=2)).isoformat())
        self.assertEqual(final["data"]["read_at"], (BASE_TIME + timedelta(minutes=3)).isoformat())
        self.assertIsNone(final["data"]["failed_at"])

        # Only tenant A's channel was used.
        self.assertEqual({c for c, _ in self.realtime.published}, {inbox_channel(self.tenant_a.id)})

    def test_failed_status_sanitized(self):
        self.process(self.status("sent"))
        errors = [{
            "code": 131047,
            "title": "Re-engagement\nmessage\t" + "x" * 2000,
            "error_data": {"details": "outside window"},
        }]
        self.assertEqual(self.process(self.status("failed", 2, errors=errors)), "processed")

        data = self.status_events()[-1]["data"]
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error_code"], "131047")
        self.assertIsNotNone(data["failed_at"])
        self.assertNotIn("\n", data["error_message"])
        self.assertNotIn("\t", data["error_message"])
        self.assertTrue(data["error_message"].startswith("Re-engagement message"))
        self.assertLessEqual(len(data["error_message"]), 500)

    def test_duplicate_status_publishes_once(self):
        self.process(self.status("delivered", 2))
        self.process(self.status("delivered", 2))
        self.process(self.status("delivered", 3))
        self.assertEqual([e["data"]["status"] for e in self.status_events()], ["delivered"])

    def test_out_of_order_never_downgrades(self):
        self.process(self.status("read", 3))
        self.process(self.status("delivered", 2))
        self.process(self.status("sent", 1))
        self.process(self.status("failed", 4, errors=[{"code": 1, "title": "late"}]))

        self.assertEqual([e["data"]["status"] for e in self.status_events()], ["read"])
        message = self.current()
        self.assertEqual(message.status, "read")
        # Late timestamps are still recorded, without a new event.
        self.assertIsNotNone(message.delivered_at)
        self.assertIsNotNone(message.sent_at)
        self.assertIsNone(message.error_code)

    def test_failed_is_terminal(self):
        self.process(self.status("failed", 1, errors=[{"code": 2, "title": "bad"}]))
        self.process(self.status("delivered", 2))
        self.assertEqual([e["data"]["status"] for e in self.status_events()], ["failed"])
        self.assertEqual(self.current().status, "failed")

    def test_unknown_message_id_not_published(self):
        self.assertEqual(self.process(self.status("delivered", external_id="wamid.unknown")), "ignored")
        self.assertEqual(self.status_events(), [])

    def test_wrong_tenant_or_channel(self):
        # Tenant A's wamid reported on tenant B's channel: no match.
        self.assertEqual(self.process(self.status("read", channel=self.wa_b)), "ignored")
        # Event claims tenant A but uses tenant B's channel: rejected.
        forged = self.make_event(
            self.wa_b, "status",
            {"status": {"id": "wamid.OUT-B", "status": "read"}, "metadata": {}},
            wa_message_id="wamid.OUT-B", tenant=self.tenant_a,
        )
        self.assertEqual(self.process(forged), "failed")

        self.assertEqual(self.realtime.published, [])
        self.assertEqual(self.current().status, "pending")
        self.assertEqual(self.reload(Message, self.outbound_b.id).status, "pending")

    def test_tenant_b_status_goes_only_to_tenant_b(self):
        self.process(self.status("delivered", external_id="wamid.OUT-B", channel=self.wa_b))
        self.assertEqual(self.status_events(self.tenant_a), [])
        [event] = self.status_events(self.tenant_b)
        self.assertEqual(event["message_id"], str(self.outbound_b.id))

    def test_no_secrets_in_payload(self):
        self.process(self.status("sent"))
        self.process(self.status("failed", 2, errors=[{"code": 1, "title": "x"}]))
        for _, raw in self.realtime.published:
            for fragment in (TOKEN_A, TOKEN_B, APP_SECRET, "access_token", "_encrypted",
                             "recipient_id", "phone_number_id", "errors", "error_data", "metadata"):
                with self.subTest(fragment=fragment):
                    self.assertNotIn(fragment, raw)


class StatusReliabilityTests(StatusTestCase):

    def test_published_only_after_commit(self):
        order: list[str] = []
        session = self.make_session()
        sa_event.listen(session, "after_commit", lambda s: order.append("commit"))

        class OrderedBroker(InMemoryBroker):
            def publish(self, channel, payload):
                order.append("publish:" + json.loads(payload)["event"])
                super().publish(channel, payload)

        realtime_service.set_broker(OrderedBroker())
        try:
            self.process(self.status("delivered"), session=session)
        finally:
            session.close()
            realtime_service.set_broker(self.realtime)

        self.assertEqual(order[-1], "publish:message.status_changed")
        self.assertEqual(order[-2], "commit")

    def test_no_event_after_transaction_failure(self):
        def apply_then_fail(db, message, *args, **kwargs):
            message.status = "delivered"
            raise RuntimeError("database exploded")

        with mock.patch("app.services.message_service.update_message_status", side_effect=apply_then_fail):
            self.assertEqual(self.process(self.status("delivered")), "failed")

        self.assertEqual(self.realtime.published, [])
        self.assertEqual(self.current().status, "pending")

    def test_redis_unavailable_keeps_committed_update(self):
        logs: list[str] = []
        handler = logging.Handler(level=logging.DEBUG)
        handler.emit = lambda record: logs.append(handler.format(record))
        root = logging.getLogger()
        root.addHandler(handler)
        realtime_service.set_broker(RedisBroker("redis://:supersecretpass@127.0.0.1:1/0", timeout=0.5))
        try:
            self.assertEqual(self.process(self.status("read")), "processed")
        finally:
            realtime_service.set_broker(self.realtime)
            root.removeHandler(handler)

        self.assertEqual(self.current().status, "read")
        joined = "\n".join(logs)
        self.assertIn("Realtime publish failed for message.status_changed", joined)
        self.assertNotIn("supersecretpass", joined)


class StatusWebSocketTests(StatusTestCase):

    def test_websocket_delivers_status_to_owning_tenant_only(self):
        ws_a = self.connect(self.viewer, self.tenant_a)
        ws_b = self.connect(self.owner_b, self.tenant_b)

        self.process(self.status("delivered"))
        self.process(self.status("read", external_id="wamid.OUT-B", channel=self.wa_b))

        received_b = ws_b.receive_json()
        self.assertEqual((received_b["event"], received_b["message_id"]), ("message.status_changed", str(self.outbound_b.id)))

        received_a = ws_a.receive_json()
        self.assertEqual(received_a["event"], "message.status_changed")
        self.assertEqual(received_a["message_id"], str(self.outbound.id))
        self.assertEqual(received_a["data"]["status"], "delivered")
        self.assertEqual(received_a, self.status_events(self.tenant_a)[0])
