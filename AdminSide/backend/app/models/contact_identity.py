import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ContactIdentity(Base, UUIDMixin, TimestampMixin):
    """
    A contact's identity on a single channel.

    A Contact is the person; a ContactIdentity is how that person is
    addressed on one channel (WhatsApp wa_id, Instagram-scoped id,
    Facebook PSID, Web Chat session id). One contact may hold several
    identities, one per channel. channel_type is kept as a plain string so
    new channels need no migration here.
    """

    __tablename__ = "contact_identities"

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

    # e.g. "whatsapp", "instagram", "facebook", "web_chat".
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # The provider-scoped address for this channel (WhatsApp wa_id, etc.).
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)

    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    identity_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    __table_args__ = (
        # One identity per channel address within a tenant. The same
        # external_id in another tenant is a different person.
        UniqueConstraint(
            "tenant_id",
            "channel_type",
            "external_id",
            name="uq_contact_identities_tenant_channel_external",
        ),
    )
