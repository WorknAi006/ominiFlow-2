"""
Realtime inbox events over Redis pub/sub.

Channel per tenant: omniflow:tenant:{tenant_id}:inbox (never global).
Publishing is best effort and only happens AFTER the database commit:
a Redis failure is logged (without the Redis URL, which may contain a
password) and never affects stored data.

The broker is pluggable: RedisBroker in production, InMemoryBroker for
tests / local development without Redis.
"""
import asyncio
import json
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import redis
import redis.asyncio as redis_async

from app.core.config import settings

logger = logging.getLogger(__name__)

MESSAGE_CREATED = "message.created"
MESSAGE_STATUS_CHANGED = "message.status_changed"
CONVERSATION_UPDATED = "conversation.updated"
# Events the inbox WebSocket may forward to clients.
CLIENT_EVENTS = frozenset({MESSAGE_CREATED, MESSAGE_STATUS_CHANGED, CONVERSATION_UPDATED})
# Same bound as the conversation list preview.
MAX_PREVIEW_LENGTH = 200
MAX_TEXT_LENGTH = 4096
MAX_ERROR_MESSAGE_LENGTH = 500


def inbox_channel(tenant_id: uuid.UUID | str) -> str:
    return f"omniflow:tenant:{tenant_id}:inbox"


class RealtimeUnavailableError(Exception):
    """The realtime broker cannot be reached."""


# =========================
# BROKERS
# =========================

class Subscription(ABC):

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[str]:
        """Yield raw event payloads."""

    @abstractmethod
    async def close(self) -> None:
        """Unsubscribe and release resources."""


class RealtimeBroker(ABC):

    @abstractmethod
    def publish(self, channel: str, payload: str) -> None:
        """Publish synchronously (called from sync workers). May raise."""

    @abstractmethod
    async def subscribe(self, channel: str) -> Subscription:
        """Subscribe to exactly one channel. Raises RealtimeUnavailableError."""


class _RedisSubscription(Subscription):

    def __init__(self, client: redis_async.Redis, pubsub: Any) -> None:
        self._client = client
        self._pubsub = pubsub

    async def __aiter__(self) -> AsyncIterator[str]:
        async for message in self._pubsub.listen():
            if message.get("type") == "message":
                data = message.get("data")
                yield data.decode("utf-8") if isinstance(data, bytes) else str(data)

    async def close(self) -> None:
        try:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
        finally:
            await self._client.aclose()


class RedisBroker(RealtimeBroker):

    def __init__(self, url: str, timeout: float = 2.0) -> None:
        self._url = url
        self._timeout = timeout
        self._client: redis.Redis | None = None
        self._lock = threading.Lock()

    def _sync_client(self) -> redis.Redis:
        with self._lock:
            if self._client is None:
                self._client = redis.Redis.from_url(
                    self._url,
                    socket_connect_timeout=self._timeout,
                    socket_timeout=self._timeout,
                )
            return self._client

    def publish(self, channel: str, payload: str) -> None:
        self._sync_client().publish(channel, payload)

    async def subscribe(self, channel: str) -> Subscription:
        client = redis_async.Redis.from_url(
            self._url, socket_connect_timeout=self._timeout,
        )
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(channel)
        except (redis.RedisError, OSError):
            await client.aclose()
            raise RealtimeUnavailableError("Realtime service is unavailable.") from None
        return _RedisSubscription(client, pubsub)


class _MemorySubscription(Subscription):

    def __init__(self, broker: "InMemoryBroker", channel: str) -> None:
        self._broker = broker
        self.channel = channel
        self.loop = asyncio.get_running_loop()
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    async def __aiter__(self) -> AsyncIterator[str]:
        while True:
            yield await self.queue.get()

    async def close(self) -> None:
        self._broker._remove(self)


class InMemoryBroker(RealtimeBroker):
    """Process-local broker (thread-safe publish into asyncio subscribers)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscriptions: list[_MemorySubscription] = []
        self.published: list[tuple[str, str]] = []

    def publish(self, channel: str, payload: str) -> None:
        with self._lock:
            self.published.append((channel, payload))
            targets = [s for s in self._subscriptions if s.channel == channel]
        for subscription in targets:
            subscription.loop.call_soon_threadsafe(subscription.queue.put_nowait, payload)

    async def subscribe(self, channel: str) -> Subscription:
        subscription = _MemorySubscription(self, channel)
        with self._lock:
            self._subscriptions.append(subscription)
        return subscription

    def _remove(self, subscription: _MemorySubscription) -> None:
        with self._lock:
            if subscription in self._subscriptions:
                self._subscriptions.remove(subscription)

    def subscriber_count(self, channel: str) -> int:
        with self._lock:
            return sum(1 for s in self._subscriptions if s.channel == channel)


_broker: RealtimeBroker | None = None


def get_broker() -> RealtimeBroker:
    global _broker
    if _broker is None:
        _broker = RedisBroker(settings.redis_url)
    return _broker


def set_broker(broker: RealtimeBroker | None) -> None:
    """Override the broker (tests); None restores the default on next use."""
    global _broker
    _broker = broker


# =========================
# EVENTS
# =========================

def build_message_created_event(
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    direction: str,
    message_type: str,
    text: str | None,
    created_at: datetime | None,
    contact_id: uuid.UUID,
    contact_name: str | None,
    contact_phone: str | None,
) -> dict[str, Any]:
    """Only safe, explicitly chosen fields. No raw provider payload."""

    return {
        "event": MESSAGE_CREATED,
        "event_id": str(uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "direction": direction,
            "type": message_type,
            "text": text[:MAX_TEXT_LENGTH] if text else None,
            "created_at": created_at.isoformat() if created_at else None,
            "contact": {
                "id": str(contact_id),
                "name": contact_name,
                "phone_number": contact_phone,
            },
        },
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _safe_error_message(value: str | None) -> str | None:
    """Provider error text for display: control characters removed, bounded."""
    if not value:
        return None
    cleaned = "".join(ch if ch.isprintable() else " " for ch in value).strip()
    return cleaned[:MAX_ERROR_MESSAGE_LENGTH] or None


def build_message_status_changed_event(
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    status: str,
    sent_at: datetime | None,
    delivered_at: datetime | None,
    read_at: datetime | None,
    failed_at: datetime | None,
    error_code: str | None,
    error_message: str | None,
) -> dict[str, Any]:
    """Status snapshot of a message after a committed status change."""

    return {
        "event": MESSAGE_STATUS_CHANGED,
        "event_id": str(uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "status": status,
            "sent_at": _iso(sent_at),
            "delivered_at": _iso(delivered_at),
            "read_at": _iso(read_at),
            "failed_at": _iso(failed_at),
            "error_code": error_code,
            "error_message": _safe_error_message(error_message),
        },
    }


def _safe_preview(value: str | None) -> str | None:
    """Single-line preview: control characters/whitespace runs collapsed, bounded."""
    if not value:
        return None
    cleaned = " ".join("".join(ch if ch.isprintable() else " " for ch in value).split())
    return cleaned[:MAX_PREVIEW_LENGTH] or None


def build_conversation_updated_event(
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    status: str,
    unread_count: int,
    last_message_at: datetime | None,
    last_message_id: uuid.UUID | None,
    last_message_direction: str | None,
    last_message_type: str | None,
    last_message_text: str | None,
) -> dict[str, Any]:
    """Conversation-list state after a committed change. No contact PII."""

    return {
        "event": CONVERSATION_UPDATED,
        "event_id": str(uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "conversation_id": str(conversation_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "status": status,
            "unread_count": unread_count,
            "last_message_at": _iso(last_message_at),
            "last_message_id": str(last_message_id) if last_message_id else None,
            "last_message_direction": last_message_direction,
            "last_message_type": last_message_type,
            "last_message_preview": _safe_preview(last_message_text),
        },
    }


def publish_event(event: dict[str, Any]) -> bool:
    """
    Publish to the event's tenant inbox channel. Call only after the
    database commit. Never raises; returns False if publishing failed.
    """

    try:
        get_broker().publish(inbox_channel(event["tenant_id"]), json.dumps(event))
        return True
    except Exception as exc:  # noqa: BLE001 - realtime must never break processing
        logger.warning(
            "Realtime publish failed for %s on message %s: %s",
            event.get("event"),
            event.get("message_id"),
            type(exc).__name__,
        )
        return False


# Backwards-compatible name used by existing callers.
publish_message_created = publish_event
