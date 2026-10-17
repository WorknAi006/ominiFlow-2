import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# Meta template statuses that may be sent.
USABLE_TEMPLATE_STATUSES = ("approved",)


class MessageTemplate(Base, UUIDMixin, TimestampMixin):
    """
    A WhatsApp message template synchronized from Meta for one channel.

    Provider data (components, quality, parameter format) is kept as
    JSONB so new Meta structures are preserved without schema changes.
    Status is stored lowercase as reported by Meta (approved, pending,
    rejected, paused, disabled, ...); it is not constrained because Meta
    adds statuses over time.
    """

    __tablename__ = "message_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_connections.id"),
        nullable=False,
        index=True,
    )

    external_template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    components: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    template_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True,
    )

    # False when the template was absent from the latest full sync.
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "channel_connection_id", "name", "language",
            name="uq_message_templates_tenant_channel_name_language",
        ),
    )
