import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    ChannelConnection,
    Contact,
    Conversation,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.schemas.message import MessageListResponse, MessageResponse
from app.services.conversation_service import get_conversation_model
from app.services.query_utils import page_offset


class MessageServiceError(Exception):
    """Base message service error."""


class MessageNotFoundError(MessageServiceError):
    """Raised when the message does not exist in the current tenant."""


# Outbound delivery progress; statuses never move backwards.
_OUTBOUND_RANK = {
    MessageStatus.PENDING: 0,
    MessageStatus.SENT: 1,
    MessageStatus.DELIVERED: 2,
    MessageStatus.READ: 3,
}

_TIMESTAMP_FIELD = {
    MessageStatus.SENT: "sent_at",
    MessageStatus.DELIVERED: "delivered_at",
    MessageStatus.READ: "read_at",
    MessageStatus.FAILED: "failed_at",
}


def to_message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        contact_id=message.contact_id,
        channel_connection_id=message.channel_connection_id,
        direction=message.direction,
        message_type=message.message_type,
        status=message.status,
        external_message_id=message.external_message_id,
        text=message.text,
        media_url=message.media_url,
        media_type=message.media_type,
        media_metadata=message.media_metadata,
        metadata=message.message_metadata,
        reply_to_message_id=message.reply_to_message_id,
        sent_by_user_id=message.sent_by_user_id,
        sent_at=message.sent_at,
        delivered_at=message.delivered_at,
        read_at=message.read_at,
        failed_at=message.failed_at,
        error_code=message.error_code,
        error_message=message.error_message,
        created_at=message.created_at,
    )


# =========================
# QUERIES
# =========================

def get_message_model(
    db: Session,
    tenant_id: uuid.UUID,
    message_id: uuid.UUID,
    for_update: bool = False,
) -> Message:
    query = db.query(Message).filter(
        Message.id == message_id,
        Message.tenant_id == tenant_id,
    )
    if for_update:
        query = query.with_for_update()

    message = query.first()
    if message is None:
        raise MessageNotFoundError("Message not found.")
    return message


def get_message(
    db: Session,
    tenant_id: uuid.UUID,
    message_id: uuid.UUID,
) -> MessageResponse:
    return to_message_response(get_message_model(db, tenant_id, message_id))


def list_messages(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    page: int,
    page_size: int,
) -> MessageListResponse:
    """Newest first. 404 if the conversation is not in this tenant."""

    get_conversation_model(db, tenant_id, conversation_id)

    query = db.query(Message).filter(
        Message.tenant_id == tenant_id,
        Message.conversation_id == conversation_id,
    )

    total = query.count()

    messages = (
        query.order_by(Message.created_at.desc(), Message.id.desc())
        .offset(page_offset(page, page_size))
        .limit(page_size)
        .all()
    )

    return MessageListResponse(
        items=[to_message_response(message) for message in messages],
        total=total,
        page=page,
        page_size=page_size,
    )


def find_by_external_id(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    external_message_id: str,
    for_update: bool = False,
) -> Message | None:
    query = db.query(Message).filter(
        Message.tenant_id == tenant_id,
        Message.channel_connection_id == channel_id,
        Message.external_message_id == external_message_id,
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


# =========================
# COMMANDS (caller commits)
# =========================

def create_inbound_message(
    db: Session,
    *,
    conversation: Conversation,
    contact: Contact,
    channel: ChannelConnection,
    external_message_id: str,
    message_type: MessageType,
    sender_identifier: str | None,
    recipient_identifier: str | None,
    sent_at: datetime | None,
    text: str | None = None,
    media_type: str | None = None,
    media_metadata: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    reply_to_message_id: uuid.UUID | None = None,
) -> Message | None:
    """
    Insert an inbound message once. Returns None if the provider message
    was already stored (unique tenant + channel + external_message_id).
    """

    message_id = db.execute(
        insert(Message)
        .values(
            id=uuid.uuid4(),
            tenant_id=conversation.tenant_id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            channel_connection_id=channel.id,
            direction=MessageDirection.INBOUND,
            message_type=message_type,
            external_message_id=external_message_id,
            sender_identifier=sender_identifier,
            recipient_identifier=recipient_identifier,
            text=text,
            media_type=media_type,
            media_metadata=media_metadata,
            message_metadata=metadata,
            status=MessageStatus.RECEIVED,
            reply_to_message_id=reply_to_message_id,
            sent_at=sent_at,
        )
        .on_conflict_do_nothing(
            index_elements=["tenant_id", "channel_connection_id", "external_message_id"],
            index_where=sql_text("external_message_id IS NOT NULL"),
        )
        .returning(Message.id)
    ).scalar_one_or_none()

    return db.get(Message, message_id) if message_id else None


def create_outbound_message(
    db: Session,
    *,
    conversation: Conversation,
    contact: Contact,
    channel: ChannelConnection,
    text: str,
    sender_identifier: str | None,
    recipient_identifier: str,
    sent_by_user_id: uuid.UUID | None,
    reply_to_message_id: uuid.UUID | None = None,
    message_type: MessageType = MessageType.TEXT,
    metadata: dict[str, Any] | None = None,
) -> Message:
    message = Message(
        tenant_id=conversation.tenant_id,
        conversation_id=conversation.id,
        contact_id=contact.id,
        channel_connection_id=channel.id,
        direction=MessageDirection.OUTBOUND,
        message_type=message_type,
        message_metadata=metadata,
        text=text,
        sender_identifier=sender_identifier,
        recipient_identifier=recipient_identifier,
        status=MessageStatus.PENDING,
        sent_by_user_id=sent_by_user_id,
        reply_to_message_id=reply_to_message_id,
    )
    db.add(message)
    db.flush()
    return message


def update_message_status(
    db: Session,
    message: Message,
    status: MessageStatus,
    at: datetime,
    error_code: str | None = None,
    error_message: str | None = None,
) -> bool:
    """
    Apply a provider delivery status to an outbound message.

    - Timestamps are recorded the first time each status is seen.
    - Status only moves forward (pending < sent < delivered < read).
    - failed applies unless the message was already delivered or read.
    Returns True if the status value changed.
    """

    if message.direction != MessageDirection.OUTBOUND:
        return False

    timestamp_field = _TIMESTAMP_FIELD.get(status)
    if timestamp_field and getattr(message, timestamp_field) is None:
        setattr(message, timestamp_field, at)

    current = MessageStatus(message.status)

    if status == MessageStatus.FAILED:
        if current in (MessageStatus.DELIVERED, MessageStatus.READ, MessageStatus.FAILED):
            return False
        message.status = MessageStatus.FAILED
        message.error_code = error_code
        message.error_message = error_message[:1000] if error_message else None
        return True

    if current == MessageStatus.FAILED:
        return False

    if _OUTBOUND_RANK.get(status, -1) > _OUTBOUND_RANK.get(current, -1):
        message.status = status
        return True

    return False


def mark_message_delivered(db: Session, message: Message, at: datetime) -> bool:
    return update_message_status(db, message, MessageStatus.DELIVERED, at)


def mark_message_read(db: Session, message: Message, at: datetime) -> bool:
    return update_message_status(db, message, MessageStatus.READ, at)


def mark_message_failed(
    db: Session,
    message: Message,
    at: datetime,
    error_code: str | None,
    error_message: str | None,
) -> bool:
    return update_message_status(
        db, message, MessageStatus.FAILED, at, error_code, error_message,
    )
