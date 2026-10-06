import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ChannelType(StrEnum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class ChannelStatus(StrEnum):
    PENDING = "pending"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    REVOKED = "revoked"


def _sql_in(values: type[StrEnum]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class ChannelConnection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "channel_connections"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=ChannelStatus.PENDING,
        server_default=ChannelStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Provider account that webhooks are routed by, e.g. WhatsApp
    # phone_number_id, Instagram account id, Facebook page id.
    external_account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Parent business object, e.g. WhatsApp Business Account id.
    external_business_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Fernet ciphertext (see app/services/credential_service.py).
    access_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    refresh_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Non-secret provider data, managed by provider integrations only.
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Sanitized, user-facing error. Must never contain credentials.
    last_error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Soft delete: future conversations/messages reference channels.
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            f"channel_type IN ({_sql_in(ChannelType)})",
            name="ck_channel_connections_channel_type",
        ),
        CheckConstraint(
            f"status IN ({_sql_in(ChannelStatus)})",
            name="ck_channel_connections_status",
        ),
        # One live connection per external account within a tenant.
        Index(
            "uq_channel_connections_tenant_external_account",
            "tenant_id",
            "channel_type",
            "external_account_id",
            unique=True,
            postgresql_where=text(
                "is_deleted = false AND external_account_id IS NOT NULL"
            ),
        ),
        # Webhook routing: a connected external account belongs to exactly
        # one tenant. Pending (unverified) claims do not block the real
        # owner from connecting.
        Index(
            "uq_channel_connections_connected_external_account",
            "channel_type",
            "external_account_id",
            unique=True,
            postgresql_where=text(
                "status = 'connected' AND is_deleted = false "
                "AND external_account_id IS NOT NULL"
            ),
        ),
    )
