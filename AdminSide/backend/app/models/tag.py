import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# Default tag colour (Omniflow green); the UI may override per tag.
DEFAULT_TAG_COLOR = "#176b59"


class Tag(Base, UUIDMixin, TimestampMixin):
    """A tenant-scoped contact tag. Tag names are unique per tenant."""

    __tablename__ = "tags"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    color: Mapped[str] = mapped_column(
        String(9), default=DEFAULT_TAG_COLOR, server_default=DEFAULT_TAG_COLOR, nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tags_tenant_name"),
    )


class ContactTag(Base, UUIDMixin, TimestampMixin):
    """
    Association between a contact and a tag. Tenant-scoped on both sides;
    deleting a contact or a tag removes the association (CASCADE), never the
    other side's record beyond the link itself.
    """

    __tablename__ = "contact_tags"

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
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("contact_id", "tag_id", name="uq_contact_tags_contact_tag"),
        Index("ix_contact_tags_tenant_tag", "tenant_id", "tag_id"),
    )
