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

from app.integrations.whatsapp.messages import (
    parse_inbound_message,
    profile_name,
    reply_context_id,
)
from app.models import (
    ChannelConnection,
    ChannelType,
    MessageStatus,
    WhatsAppEvent,
    WhatsAppEventStatus,
    WhatsAppEventType,
)
from app.services import (
    contact_service,
    conversation_service,
    media_service,
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
    Returns realtime events for a newly created message (message.created,
    then conversation.updated), published by process_event only after
    commit. Duplicates return no events.
    """
    payload = event.payload if isinstance(event.payload, dict) else {}
    message = payload.get("message")

    if not isinstance(message, dict):
        raise _IgnoreEvent("Malformed message event.")

    external_id = event.wa_message_id or message.get("id")
    sender = event.wa_id or message.get("from")

    if not external_id or not sender:
        raise _IgnoreEvent("Message has no id or sender.")

    # Already stored (e.g. event replayed): do not touch contact or
    # conversation state.
    if message_service.find_by_external_id(db, event.tenant_id, channel.id, external_id):
        return []

    try:
        contact = contact_service.get_or_create_by_phone(
            db,
            event.tenant_id,
            sender,
            external_identifier=sender,
            profile_name=profile_name(payload.get("contact")),
        )
    except InvalidContactError:
        raise _IgnoreEvent("Sender is not a valid phone number.") from None

    conversation = conversation_service.get_or_create_conversation(
        db, event.tenant_id, contact.id, channel.id,
    )

    content = parse_inbound_message(message)

    reply_to_id = None
    context_id = reply_context_id(message)
    if context_id:
        replied = message_service.find_by_external_id(
            db, event.tenant_id, channel.id, context_id,
        )
        reply_to_id = replied.id if replied else None

    occurred_at = event.occurred_at or event.created_at or _utcnow()

    created = message_service.create_inbound_message(
        db,
        conversation=conversation,
        contact=contact,
        channel=channel,
        external_message_id=external_id,
        message_type=content.message_type,
        sender_identifier=sender,
        recipient_identifier=channel.external_account_id,
        sent_at=occurred_at,
        text=content.text,
        media_type=content.media_type,
        media_metadata=content.media_metadata,
        metadata=content.metadata,
        reply_to_message_id=reply_to_id,
    )

    if created is not None:
        conversation_service.record_activity(db, conversation, occurred_at, inbound=True)

        media = content.media_metadata or {}
        if media.get("id"):
            # Queue the download; the media worker fetches it later (no
            # HTTP inside this transaction).
            media_service.register_pending(
                db,
                created,
                provider_media_id=str(media["id"]),
                media_kind=content.message_type.value,
                declared_mime=media.get("mime_type"),
                declared_filename=media.get("filename"),
                declared_sha256=media.get("sha256"),
            )

        message_created = realtime_service.build_message_created_event(
            tenant_id=event.tenant_id,
            conversation_id=conversation.id,
            message_id=created.id,
            direction=created.direction,
            message_type=created.message_type,
            text=created.text,
            created_at=created.created_at,
            contact_id=contact.id,
            contact_name=contact_service.contact_name(contact),
            contact_phone=contact.normalized_phone_number,
        )
        # State after record_activity (unread +1 once, last_message_at never
        # backwards, latest message by the list's ordering).
        conversation_updated = realtime_service.build_conversation_updated_event(
            tenant_id=event.tenant_id,
            conversation_id=conversation.id,
            **conversation_service.get_update_snapshot(db, conversation),
        )
        return [message_created, conversation_updated]

    return []


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
