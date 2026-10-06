import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    func,
    Index,
    String,
    Text,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.channel_connection import _sql_in


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    LOCATION = "location"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    REACTION = "reaction"
    UNKNOWN = "unknown"


class MessageStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    RECEIVED = "received"


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_connections.id"),
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False)

    message_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Provider message id (WhatsApp wamid).
    external_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    sender_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    media_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    media_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False)

    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Team member who sent an outbound message.
    sent_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # clock_timestamp() (not now(), which is the transaction start time) so
    # messages inserted in the same transaction still order correctly.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            f"direction IN ({_sql_in(MessageDirection)})",
            name="ck_messages_direction",
        ),
        CheckConstraint(
            f"message_type IN ({_sql_in(MessageType)})",
            name="ck_messages_message_type",
        ),
        CheckConstraint(
            f"status IN ({_sql_in(MessageStatus)})",
            name="ck_messages_status",
        ),
        # Idempotency: a provider message is stored once per channel.
        Index(
            "uq_messages_tenant_channel_external_id",
            "tenant_id",
            "channel_connection_id",
            "external_message_id",
            unique=True,
            postgresql_where=sql_text("external_message_id IS NOT NULL"),
        ),
        # Conversation timeline pagination.
        Index(
            "ix_messages_conversation_created_at",
            "conversation_id",
            "created_at",
        ),
        Index("ix_messages_created_at", "created_at"),
    )
