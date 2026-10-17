"""
Tests for realtime inbox: message.created publishing (after commit,
tenant-scoped, safe payload) and the /api/v1/ws/inbox WebSocket.
"""
import asyncio
import json
import logging
import time
import uuid
from unittest import mock

from sqlalchemy import event as sa_event
from starlette.websockets import WebSocketDisconnect

from app.api import realtime as realtime_api
from app.core.config import settings
from app.core.security import create_access_token
from app.models import Message, TenantMembership
from app.services import realtime_service
from app.services.realtime_service import (
    InMemoryBroker,
    RealtimeBroker,
    RealtimeUnavailableError,
    RedisBroker,
    inbox_channel,
)
from app.services.whatsapp_event_processor import process_event
from tests.inbox_fixtures import APP_SECRET, CUSTOMER, CUSTOMER_E164, TOKEN_A, InboxTestCase

WS_URL = "/api/v1/ws/inbox"

FORBIDDEN_FRAGMENTS = (
    TOKEN_A, APP_SECRET, "access_token", "_encrypted", "password", "secret",
    "messaging_product", "phone_number_id", "profile", "metadata",
)


class RealtimeTestCase(InboxTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.realtime.published.clear()

    def process(self, event, session=None):
        own = session is None
        session = session or self.make_session()
        try:
            return process_event(session, event.id)
        finally:
            if own:
                session.close()

    def inbound(self, channel=None, body="Hello", sender=CUSTOMER):
        return self.message_event(channel or self.wa_a, self.text_message(body=body, sender=sender))

    def published(self, tenant=None, event_type="message.created"):
        channel = inbox_channel((tenant or self.tenant_a).id)
        events = [json.loads(p) for c, p in self.realtime.published if c == channel]
        return [e for e in events if event_type is None or e["event"] == event_type]

    def connect(self, actor, tenant, **extra):
        ws = self.client.websocket_connect(WS_URL)
        session = ws.__enter__()
        session.send_json({"type": "auth", "token": self.token_for(actor, tenant), **extra})
        self.assertEqual(session.receive_json(), {"event": "ready"})
        self.addCleanup(self._disconnect, ws, session, inbox_channel(tenant.id))
        return session

    def _disconnect(self, ws, session, channel):
        """
        Disconnect like a real client and let the server finish its cleanup
        before closing the test session. (Starlette's test client otherwise
        cancels the app immediately after sending the disconnect, a race a
        real server does not have.)
        """
        before = self.realtime.subscriber_count(channel)
        session.close(1000)
        deadline = time.monotonic() + 5
        while self.realtime.subscriber_count(channel) >= before and time.monotonic() < deadline:
            time.sleep(0.02)
        ws.__exit__(None, None, None)

    def close_code(self, auth_message):
        with self.client.websocket_connect(WS_URL) as ws:
            if auth_message is not None:
                ws.send_text(auth_message if isinstance(auth_message, str) else json.dumps(auth_message))
            with self.assertRaises(WebSocketDisconnect) as ctx:
                ws.receive_json()
        return ctx.exception.code


# =========================
# PUBLISHING
# =========================

class PublishTests(RealtimeTestCase):

    def test_message_created_payload_and_channel(self):
        self.assertEqual(self.process(self.inbound(body="Hi team")), "processed")

        [event] = self.published()
        message = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).one()

        self.assertEqual(set(event), {"event", "event_id", "tenant_id", "conversation_id", "message_id", "timestamp", "data"})
        self.assertEqual(event["event"], "message.created")
        self.assertEqual(event["tenant_id"], str(self.tenant_a.id))
        self.assertEqual(event["message_id"], str(message.id))
        self.assertEqual(event["conversation_id"], str(message.conversation_id))
        uuid.UUID(event["event_id"])
        self.assertEqual(event["data"]["direction"], "inbound")
        self.assertEqual(event["data"]["type"], "text")
        self.assertEqual(event["data"]["text"], "Hi team")
        self.assertEqual(event["data"]["contact"], {
            "id": str(message.contact_id), "name": "Jane Customer", "phone_number": CUSTOMER_E164,
        })

        # Only the tenant's own channel; nothing global or for tenant B.
        self.assertEqual(
            {c for c, _ in self.realtime.published}, {f"omniflow:tenant:{self.tenant_a.id}:inbox"},
        )
        self.assertEqual(self.published(self.tenant_b), [])

    def test_no_secrets_in_event(self):
        self.process(self.inbound())
        self.assertTrue(self.realtime.published)
        raw = "\n".join(payload for _, payload in self.realtime.published)
        for fragment in FORBIDDEN_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, raw)

    def test_tenant_comes_from_routing_not_payload(self):
        message = self.text_message()
        event = self.make_event(self.wa_a, "message", {
            "message": message,
            "contact": {"wa_id": CUSTOMER, "profile": {"name": "X"}},
            "tenant_id": str(self.tenant_b.id),
        }, wa_message_id=message["id"], wa_id=CUSTOMER)
        self.process(event)
        self.assertEqual(len(self.published(self.tenant_a)), 1)
        self.assertEqual(self.published(self.tenant_b), [])

    def test_not_published_without_new_committed_message(self):
        event = self.inbound()
        with mock.patch("app.services.message_service.create_inbound_message", side_effect=RuntimeError("boom")):
            self.assertEqual(self.process(event), "failed")
        self.assertEqual(self.realtime.published, [])

        event = self.inbound()
        self.assertEqual(self.process(event), "processed")
        self.assertEqual(len(self.published()), 1)

        # Replay of the same message: no new message, no new event.
        row = self.reload(type(event), event.id)
        row.processing_status = "received"
        self.db.commit()
        self.process(event)
        self.assertEqual(len(self.published()), 1)

        # Ignored and status events do not publish message.created.
        self.process(self.make_event(self.wa_a, "error", {"error": {}}))
        self.process(self.status_event(self.wa_a, "wamid.unknown", "delivered"))
        self.assertEqual(len(self.published()), 1)

    def test_published_only_after_commit(self):
        order: list[str] = []
        session = self.make_session()
        sa_event.listen(session, "after_commit", lambda s: order.append("commit"))

        class OrderedBroker(InMemoryBroker):
            def publish(self, channel, payload):
                order.append("publish")
                super().publish(channel, payload)

        realtime_service.set_broker(OrderedBroker())
        try:
            self.process(self.inbound(), session=session)
        finally:
            session.close()
            realtime_service.set_broker(self.realtime)

        self.assertIn("publish", order)
        self.assertEqual(order[-1], "publish")
        self.assertEqual(order[order.index("publish") - 1], "commit")

    def test_redis_unavailable_does_not_break_processing(self):
        handler = logging.Handler(level=logging.DEBUG)
        logs: list[str] = []
        handler.emit = lambda record: logs.append(handler.format(record))
        root = logging.getLogger()
        root.addHandler(handler)

        # Closed port; URL contains a password that must never be logged.
        realtime_service.set_broker(RedisBroker("redis://:supersecretpass@127.0.0.1:1/0", timeout=0.5))
        try:
            event = self.inbound(body="Stored anyway")
            self.assertEqual(self.process(event), "processed")
        finally:
            realtime_service.set_broker(self.realtime)
            root.removeHandler(handler)

        self.db.expire_all()
        [message] = self.db.query(Message).filter_by(tenant_id=self.tenant_a.id).all()
        self.assertEqual(message.text, "Stored anyway")
        self.assertEqual(self.reload(type(event), event.id).processing_status, "processed")
        joined = "\n".join(logs)
        self.assertIn("Realtime publish failed", joined)
        self.assertNotIn("supersecretpass", joined)

    def test_real_redis_round_trip(self):
        broker = RedisBroker(settings.redis_url, timeout=1)
        try:
            broker.publish("omniflow:healthcheck", "ping")
        except Exception:  # noqa: BLE001
            self.skipTest("Redis is not reachable")

        channel = inbox_channel(uuid.uuid4())

        async def scenario():
            subscription = await broker.subscribe(channel)
            try:
                await asyncio.to_thread(broker.publish, channel, '{"event": "message.created"}')
                iterator = subscription.__aiter__()
                return await asyncio.wait_for(iterator.__anext__(), timeout=5)
            finally:
                await subscription.close()

        self.assertEqual(asyncio.run(scenario()), '{"event": "message.created"}')


# =========================
# WEBSOCKET
# =========================

class WebSocketTests(RealtimeTestCase):

    def test_authenticated_client_receives_message_created(self):
        ws = self.connect(self.viewer, self.tenant_a)
        self.process(self.inbound(body="Realtime hello"))

        received = ws.receive_json()
        [published] = self.published()
        self.assertEqual(received, published)
        self.assertEqual(received["data"]["text"], "Realtime hello")

    def test_invalid_authentication_rejected(self):
        expired = self.token_for(self.owner, self.tenant_a, expires_minutes=-1)
        refresh = self.token_for(self.owner, self.tenant_a, extra={"type": "refresh"})
        no_tenant = create_access_token(subject=str(self.owner.id))
        cases = {
            "garbage jwt": {"type": "auth", "token": "not.a.jwt"},
            "expired jwt": {"type": "auth", "token": expired},
            "wrong token type": {"type": "auth", "token": refresh},
            "missing tenant claim": {"type": "auth", "token": no_tenant},
            "missing token": {"type": "auth"},
            "wrong message type": {"type": "subscribe", "token": self.token_for(self.owner, self.tenant_a)},
            "not json": "hello",
        }
        for name, message in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.close_code(message), 4401)

        self.assertEqual(self.realtime.subscriber_count(inbox_channel(self.tenant_a.id)), 0)

    def test_forbidden_without_tenant_access(self):
        # Valid user, token claims a tenant they are not a member of.
        message = {"type": "auth", "token": self.token_for(self.owner, self.tenant_b)}
        self.assertEqual(self.close_code(message), 4403)

        membership = self.db.query(TenantMembership).filter_by(user_id=self.agent.id).one()
        membership.status = "suspended"
        self.db.commit()
        message = {"type": "auth", "token": self.token_for(self.agent, self.tenant_a)}
        self.assertEqual(self.close_code(message), 4403)

    def test_tenant_isolation(self):
        # Client-sent tenant_id / role are ignored.
        ws_a = self.connect(self.owner, self.tenant_a, tenant_id=str(self.tenant_b.id), role="OWNER")
        ws_b = self.connect(self.owner_b, self.tenant_b)

        self.process(self.inbound(self.wa_a, body="for tenant A"))
        self.process(self.inbound(self.wa_b, body="for tenant B"))

        # B's first event is its own: A's event was never delivered to B.
        self.assertEqual(ws_b.receive_json()["data"]["text"], "for tenant B")
        received_a = ws_a.receive_json()
        self.assertEqual(received_a["data"]["text"], "for tenant A")
        self.assertEqual(received_a["tenant_id"], str(self.tenant_a.id))

    def test_foreign_or_unknown_events_not_forwarded(self):
        ws = self.connect(self.owner, self.tenant_a)
        channel = inbox_channel(self.tenant_a.id)
        self.realtime.publish(channel, json.dumps({"event": "message.created", "tenant_id": str(self.tenant_b.id)}))
        self.realtime.publish(channel, json.dumps({"event": "conversation.assigned", "tenant_id": str(self.tenant_a.id)}))
        self.realtime.publish(channel, "not json")

        self.process(self.inbound(body="the real one"))
        self.assertEqual(ws.receive_json()["data"]["text"], "the real one")

    def test_auth_timeout(self):
        with mock.patch.object(realtime_api, "AUTH_TIMEOUT_SECONDS", 0.2):
            self.assertEqual(self.close_code(None), 4408)

    def test_socket_closed_when_token_expires(self):
        token = self.token_for(self.owner, self.tenant_a, expires_minutes=2 / 60)
        with self.client.websocket_connect(WS_URL) as ws:
            ws.send_json({"type": "auth", "token": token})
            self.assertEqual(ws.receive_json(), {"event": "ready"})
            started = time.monotonic()
            with self.assertRaises(WebSocketDisconnect) as ctx:
                ws.receive_json()
        self.assertEqual(ctx.exception.code, 4401)
        self.assertLess(time.monotonic() - started, 10)

    def test_subscription_released_on_disconnect(self):
        channel = inbox_channel(self.tenant_a.id)
        with self.client.websocket_connect(WS_URL) as ws:
            ws.send_json({"type": "auth", "token": self.token_for(self.owner, self.tenant_a)})
            ws.receive_json()
            self.assertEqual(self.realtime.subscriber_count(channel), 1)

            # Client disconnects; the server must release the subscription on
            # its own. (Waiting inside the session avoids the test client's
            # immediate cancel on exit, which a real server does not do.)
            ws.close(1000)
            deadline = time.monotonic() + 5
            while self.realtime.subscriber_count(channel) and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual(self.realtime.subscriber_count(channel), 0)

    def test_realtime_unavailable_closes_1011(self):
        class DownBroker(RealtimeBroker):
            def publish(self, channel, payload):
                raise RealtimeUnavailableError()

            async def subscribe(self, channel):
                raise RealtimeUnavailableError("Realtime service is unavailable.")

        realtime_service.set_broker(DownBroker())
        try:
            message = {"type": "auth", "token": self.token_for(self.owner, self.tenant_a)}
            self.assertEqual(self.close_code(message), 1011)
        finally:
            realtime_service.set_broker(self.realtime)
