import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class OAuthStatus(StrEnum):
    PENDING = "pending"        # dialog opened, awaiting Meta callback
    DISCOVERED = "discovered"  # callback done, assets ready for selection
    CONSUMED = "consumed"      # finished (connected) or spent/cancelled


class OAuthState(Base, UUIDMixin, TimestampMixin):
    """
    Short-lived, single-use server-side state for a tenant's Meta OAuth
    onboarding. Binds the flow to a tenant, the user who started it, and the
    provider, and carries replay protection (unique tokens + status/expiry).

    Nothing here is trusted from the browser: the callback is authorized by
    the random `state_token` alone, and the tenant/user are read from this
    row, never from request input.
    """

    __tablename__ = "oauth_states"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Channel type being connected: "facebook" or "instagram".
    provider: Mapped[str] = mapped_column(String(20), nullable=False)

    # CSRF token sent to Meta and returned on the callback (phase 1 -> 2).
    state_token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    # Issued after the callback for the authenticated selection step
    # (phase 3 -> 4). Separate from state_token so the value exposed in the
    # Meta redirect cannot be used to complete a connection.
    selection_token: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=OAuthStatus.PENDING,
        server_default=OAuthStatus.PENDING.value,
        nullable=False,
    )

    # Long-lived user token (Fernet ciphertext), stored only between the
    # callback and selection, then cleared when the row is consumed.
    user_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Safe, non-secret discovered assets for the selection UI (no tokens).
    assets: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    # Sanitized, user-facing failure reason (e.g. "no_pages"). Never secrets.
    error: Mapped[str | None] = mapped_column(String(200), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "provider IN ('facebook', 'instagram')",
            name="ck_oauth_states_provider",
        ),
        CheckConstraint(
            "status IN ('pending', 'discovered', 'consumed')",
            name="ck_oauth_states_status",
        ),
        Index("ix_oauth_states_expires_at", "expires_at"),
    )
