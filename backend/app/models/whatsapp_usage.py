import uuid
from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WhatsAppUsageRecord(Base, UUIDMixin, TimestampMixin):
    """
    Detailed, auditable ledger for WhatsApp provider messaging events and charges.
    Tracks estimated and confirmed provider (Meta) conversation costs per tenant.
    """
    __tablename__ = "whatsapp_usage_records"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_connections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    external_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    recipient_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    direction: Mapped[str] = mapped_column(
        String(20),
        default="outbound",
        server_default="outbound",
        nullable=False,
    )

    # WhatsApp conversation category: service, marketing, utility, authentication, or general
    category: Mapped[str] = mapped_column(
        String(50),
        default="service",
        server_default="service",
        nullable=False,
        index=True,
    )

    pricing_model: Mapped[str] = mapped_column(
        String(50),
        default="CBP",
        server_default="CBP",
        nullable=False,
    )

    billable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Rates stored in exact decimal minor units or exact decimal
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        server_default="0.0000",
        nullable=False,
    )

    actual_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        server_default="INR",
        nullable=False,
    )

    # Status: 'estimated', 'confirmed', 'reconciled', 'failed'
    status: Mapped[str] = mapped_column(
        String(20),
        default="estimated",
        server_default="estimated",
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_whatsapp_usage_tenant_created", "tenant_id", "created_at"),
    )
