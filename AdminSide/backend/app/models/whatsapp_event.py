import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.channel_connection import _sql_in


class WhatsAppEventType(StrEnum):
    MESSAGE = "message"
    STATUS = "status"
    ERROR = "error"


class WhatsAppEventStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class WhatsAppEvent(Base, UUIDMixin, TimestampMixin):
    """
    Raw inbound WhatsApp webhook event, stored once per channel.

    Acts as an idempotent, durable inbox queue: the future Unified Inbox
    worker consumes RECEIVED events to build contacts, conversations and
    messages. Tenant and channel always come from routing, never from the
    webhook payload.
    """

    __tablename__ = "whatsapp_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Default NO ACTION: blocks hard-deleting a channel that has events,
    # but (unlike RESTRICT) lets a tenant CASCADE remove both together.
    # Channels are soft-deleted in normal use.
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_connections.id"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Provider-derived idempotency key, e.g. "message:<wamid>".
    dedupe_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    wa_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Customer WhatsApp id (phone number in international format).
    wa_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    processing_status: Mapped[str] = mapped_column(
        String(20),
        default=WhatsAppEventStatus.RECEIVED,
        server_default=WhatsAppEventStatus.RECEIVED.value,
        nullable=False,
        index=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Sanitized reason for FAILED / IGNORED (never payload content).
    processing_error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "channel_id",
            "dedupe_key",
            name="uq_whatsapp_events_channel_dedupe_key",
        ),
        CheckConstraint(
            f"event_type IN ({_sql_in(WhatsAppEventType)})",
            name="ck_whatsapp_events_event_type",
        ),
        CheckConstraint(
            f"processing_status IN ({_sql_in(WhatsAppEventStatus)})",
            name="ck_whatsapp_events_processing_status",
        ),
    )
