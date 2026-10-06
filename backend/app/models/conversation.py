import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.channel_connection import _sql_in


class ConversationStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


# A contact has at most one active conversation per channel.
ACTIVE_CONVERSATION_STATUSES = (
    ConversationStatus.OPEN,
    ConversationStatus.PENDING,
)


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Channels are soft-deleted; NO ACTION keeps history intact while
    # still allowing a tenant CASCADE.
    channel_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_connections.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=ConversationStatus.OPEN,
        server_default=ConversationStatus.OPEN.value,
        nullable=False,
        index=True,
    )

    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    unread_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    conversation_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_sql_in(ConversationStatus)})",
            name="ck_conversations_status",
        ),
        CheckConstraint(
            "unread_count >= 0",
            name="ck_conversations_unread_count_non_negative",
        ),
        Index(
            "uq_conversations_active_contact_channel",
            "tenant_id",
            "contact_id",
            "channel_connection_id",
            unique=True,
            postgresql_where=text("status IN ('open', 'pending')"),
        ),
        Index(
            "ix_conversations_tenant_last_message_at",
            "tenant_id",
            "last_message_at",
        ),
    )
