import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.channel_connection import _sql_in


class MediaStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    FAILED = "failed"


class MessageMedia(Base, UUIDMixin, TimestampMixin):
    """
    A provider media file attached to a message, downloaded server-side
    and stored under an application-generated key.
    """

    __tablename__ = "message_media"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )

    channel_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_connections.id"),
        nullable=False,
    )

    provider_media_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Media kind from the message type: image / video / audio / document.
    media_kind: Mapped[str] = mapped_column(String(20), nullable=False)

    # Verified MIME type (allowlisted), set once known.
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Sanitized display name only; never used for storage paths.
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    storage_backend: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Application-generated, tenant-prefixed key.
    storage_key: Mapped[str | None] = mapped_column(String(400), nullable=True, unique=True)

    status: Mapped[str] = mapped_column(
        String(20),
        default=MediaStatus.PENDING,
        server_default=MediaStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False,
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Sanitized; never contains URLs or credentials.
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    media_info: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "message_id", name="uq_message_media_tenant_message"),
        CheckConstraint(f"status IN ({_sql_in(MediaStatus)})", name="ck_message_media_status"),
        CheckConstraint(
            "media_kind IN ('image', 'video', 'audio', 'document')",
            name="ck_message_media_kind",
        ),
    )
