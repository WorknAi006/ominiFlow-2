"""
Turns stored WhatsApp webhook events (whatsapp_events) into inbox data:

    whatsapp_event -> Contact -> Conversation -> Message

Guarantees:
- One transaction per event. The event row is locked with
  FOR UPDATE SKIP LOCKED, so parallel workers never process the same
  event. Domain writes run in a SAVEPOINT; on any failure they are rolled
  back and the event is marked FAILED with a sanitized reason.
- Idempotent: database unique constraints on contacts, active
  conversations and (tenant, channel, external_message_id) make
  reprocessing produce no duplicates.
- Database only: no external HTTP calls while the transaction is open.
- Tenant and channel come from the event row (set by webhook routing),
  never from the payload.

Worker integration: process_pending_events() is the unit of work. It is
run by app/workers/whatsapp_events.py today; a Celery/Redis task can call
the same function later.
"""
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelType,
    MessageStatus,
    WhatsAppEvent,
    WhatsAppEventStatus,
    WhatsAppEventType,
)
from app.services import (
    inbound_event_service,
    message_service,
    realtime_service,
)
from app.services.contact_service import InvalidContactError

logger = logging.getLogger(__name__)

STATUS_MAP = {
    "sent": MessageStatus.SENT,
    "delivered": MessageStatus.DELIVERED,
    "read": MessageStatus.READ,
    "failed": MessageStatus.FAILED,
}


class ProcessOutcome(StrEnum):
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"
    SKIPPED = "skipped"


class _IgnoreEvent(Exception):
    """Event is valid but intentionally not turned into inbox data."""


class _FailEvent(Exception):
    """Event cannot be processed. Message must be safe to store."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# =========================
# EVENT HANDLERS
# =========================

def _load_channel(db: Session, event: WhatsAppEvent) -> ChannelConnection:
    channel = db.get(ChannelConnection, event.channel_id)

    if (
        channel is None
        or channel.tenant_id != event.tenant_id
        or channel.channel_type != ChannelType.WHATSAPP
    ):
        raise _FailEvent("Event channel is invalid for this tenant.")

    return channel


def _process_message(
    db: Session,
    event: WhatsAppEvent,
    channel: ChannelConnection,
) -> list[dict[str, Any]]:
    """
    Normalize the WhatsApp event, then hand it to the channel-neutral
    inbound service. All WhatsApp payload parsing happens in the provider's
    normalizer; the common service owns contact/conversation/message
    creation, automation and realtime. Returns realtime events published by
    process_event only after commit; duplicates return no events.
    """
    occurred_at = event.occurred_at or event.created_at or _utcnow()

    provider = get_provider(channel.channel_type)
    normalized = provider.normalize_inbound_message(
        channel,
        {
            "payload": event.payload if isinstance(event.payload, dict) else {},
            "external_message_id": event.wa_message_id,
            "external_sender_id": event.wa_id,
            "external_event_id": event.dedupe_key,
            "occurred_at": occurred_at,
        },
    )

    if normalized is None:
        raise _IgnoreEvent("Malformed or unsupported inbound message.")

    try:
        return inbound_event_service.process_inbound_event(db, normalized)
    except InvalidContactError:
        raise _IgnoreEvent("Sender is not a valid phone number.") from None


def _status_error(status: dict[str, Any]) -> tuple[str | None, str | None]:
    errors = status.get("errors")
    error = errors[0] if isinstance(errors, list) and errors and isinstance(errors[0], dict) else {}

    code = error.get("code")
    title = error.get("title") or error.get("message")
    data = error.get("error_data")
    details = data.get("details") if isinstance(data, dict) else None

    message = "; ".join(str(part) for part in (title, details) if part) or None
    return (str(code)[:50] if code is not None else None), (message[:1000] if message else None)


def _process_status(
    db: Session,
    event: WhatsAppEvent,
    channel: ChannelConnection,
) -> dict[str, Any] | None:
    """
    Apply a delivery status. Returns a message.status_changed event only
    when the status value actually changed (published after commit);
    duplicates and stale/out-of-order statuses return None.
    """
    payload = event.payload if isinstance(event.payload, dict) else {}
    status = payload.get("status")

    if not isinstance(status, dict):
        raise _IgnoreEvent("Malformed status event.")

    external_id = event.wa_message_id or status.get("id")
    new_status = STATUS_MAP.get(status.get("status"))

    if not external_id or new_status is None:
        raise _IgnoreEvent("Unsupported status event.")

    message = message_service.find_by_external_id(
        db, event.tenant_id, channel.id, external_id, for_update=True,
    )
    if message is None:
        raise _IgnoreEvent("No matching outbound message.")

    error_code, error_message = (
        _status_error(status) if new_status == MessageStatus.FAILED else (None, None)
    )

    changed = message_service.update_message_status(
        db,
        message,
        new_status,
        event.occurred_at or _utcnow(),
        error_code,
        error_message,
    )
    if not changed:
        return None

    return realtime_service.build_message_status_changed_event(
        tenant_id=message.tenant_id,
        conversation_id=message.conversation_id,
        message_id=message.id,
        status=message.status,
        sent_at=message.sent_at,
        delivered_at=message.delivered_at,
        read_at=message.read_at,
        failed_at=message.failed_at,
        error_code=message.error_code,
        error_message=message.error_message,
    )


def _dispatch(db: Session, event: WhatsAppEvent) -> list[dict[str, Any]]:
    """Process the event; return realtime events to publish after commit."""
    channel = _load_channel(db, event)

    if event.event_type == WhatsAppEventType.MESSAGE:
        return _process_message(db, event, channel)
    if event.event_type == WhatsAppEventType.STATUS:
        status_event = _process_status(db, event, channel)
        return [status_event] if status_event else []
    raise _IgnoreEvent("Account-level error events are not processed.")


# =========================
# ENTRY POINTS
# =========================

def process_event(db: Session, event_id: uuid.UUID) -> ProcessOutcome:
    """Process one RECEIVED event in its own transaction (commits)."""

    event = (
        db.query(WhatsAppEvent)
        .filter(
            WhatsAppEvent.id == event_id,
            WhatsAppEvent.processing_status == WhatsAppEventStatus.RECEIVED,
        )
        .with_for_update(skip_locked=True)
        .first()
    )

    if event is None:
        db.rollback()
        return ProcessOutcome.SKIPPED

    outcome, error = ProcessOutcome.PROCESSED, None
    realtime_events: list[dict[str, Any]] = []

    try:
        with db.begin_nested():
            realtime_events = _dispatch(db, event)
    except _IgnoreEvent as exc:
        outcome, error = ProcessOutcome.IGNORED, str(exc)
    except _FailEvent as exc:
        outcome, error = ProcessOutcome.FAILED, str(exc)
    except SQLAlchemyError as exc:
        outcome, error = ProcessOutcome.FAILED, "Database error while processing event."
        logger.error("WhatsApp event %s failed: %s", event_id, type(exc).__name__)
    except Exception as exc:  # noqa: BLE001 - a bad event must not stop the worker
        outcome, error = ProcessOutcome.FAILED, "Unexpected error while processing event."
        logger.error("WhatsApp event %s failed: %s", event_id, type(exc).__name__)

    event.processing_status = outcome.value
    event.processing_error = error
    event.processed_at = _utcnow()

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    # Only after a successful commit; best effort (never raises).
    if outcome == ProcessOutcome.PROCESSED:
        for realtime_event in realtime_events:
            realtime_service.publish_event(realtime_event)

        logger.info("WhatsApp event %s %s.", event_id, outcome.value)
    return outcome


def process_pending_events(db: Session, limit: int = 100) -> dict[str, int]:
    """Process up to `limit` RECEIVED events, oldest first."""

    event_ids = db.scalars(
        select(WhatsAppEvent.id)
        .where(WhatsAppEvent.processing_status == WhatsAppEventStatus.RECEIVED)
        .order_by(WhatsAppEvent.created_at.asc(), WhatsAppEvent.id.asc())
        .limit(limit)
    ).all()
    db.rollback()

    counts: Counter[str] = Counter()
    for event_id in event_ids:
        counts[process_event(db, event_id).value] += 1

    return dict(counts)
