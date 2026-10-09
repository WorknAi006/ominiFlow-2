import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CustomFieldType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    MULTISELECT = "multiselect"
    BOOLEAN = "boolean"


def _types_sql() -> str:
    return ", ".join(f"'{t.value}'" for t in CustomFieldType)


class CustomFieldDefinition(Base, UUIDMixin, TimestampMixin):
    """A tenant-scoped custom field a tenant can set on its contacts."""

    __tablename__ = "custom_field_definitions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    # Stable machine key (slug), unique per tenant; used in CSV/export/API.
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Choices for select/multiselect; null for the others.
    options: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(f"field_type IN ({_types_sql()})", name="ck_custom_field_type"),
        UniqueConstraint("tenant_id", "key", name="uq_custom_field_tenant_key"),
    )


class ContactFieldValue(Base, UUIDMixin, TimestampMixin):
    """A single custom-field value on one contact (tenant-scoped)."""

    __tablename__ = "contact_field_values"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_field_definitions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    # Stored as JSONB so every field type (string/number/bool/list/date-string)
    # round-trips without a column per type.
    value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("contact_id", "field_id", name="uq_contact_field_values_contact_field"),
        Index("ix_contact_field_values_tenant_field", "tenant_id", "field_id"),
    )
