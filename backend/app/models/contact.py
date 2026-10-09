import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.contact_identity import ContactIdentity


class Contact(Base, UUIDMixin, TimestampMixin):
    """A tenant's customer. Never shared across tenants."""

    __tablename__ = "contacts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider identity, e.g. WhatsApp wa_id. System-managed.
    external_identifier: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # As entered / received, for display.
    phone_number: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    # E.164 (app/core/phone.py). Unique per tenant.
    normalized_phone_number: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Name set by the team.
    display_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # Name reported by the provider (WhatsApp profile name).
    profile_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    contact_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # Per-channel identities (WhatsApp wa_id, Facebook PSID, etc.). Read-only
    # here: identities are written through contact_service with an idempotent
    # upsert. Lets a provider resolve its own recipient address (e.g. the
    # Facebook PSID) from a contact without the core services needing to know
    # any channel-specific addressing.
    identities: Mapped[list["ContactIdentity"]] = relationship(
        "ContactIdentity",
        viewonly=True,
        lazy="select",
    )

    __table_args__ = (
        # Different tenants may share a customer; within a tenant a phone
        # number identifies exactly one contact.
        Index(
            "uq_contacts_tenant_normalized_phone",
            "tenant_id",
            "normalized_phone_number",
            unique=True,
            postgresql_where=text("normalized_phone_number IS NOT NULL"),
        ),
    )
