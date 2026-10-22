"""Add whatsapp_usage_records and billing_invoices tables.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create whatsapp_usage_records
    op.create_table(
        "whatsapp_usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("recipient_phone", sa.String(length=50), nullable=True),
        sa.Column("direction", sa.String(length=20), server_default="outbound", nullable=False),
        sa.Column("category", sa.String(length=50), server_default="service", nullable=False, index=True),
        sa.Column("pricing_model", sa.String(length=50), server_default="CBP", nullable=False),
        sa.Column("billable", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=4), server_default="0.0000", nullable=False),
        sa.Column("actual_cost", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="estimated", nullable=False, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_whatsapp_usage_tenant_created",
        "whatsapp_usage_records",
        ["tenant_id", "created_at"],
    )

    # 2. Create billing_invoices
    op.create_table(
        "billing_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("invoice_number", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), server_default="18.00", nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="paid", nullable=False, index=True),
        sa.Column("payment_transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payment_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("line_items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_billing_invoices_tenant_created",
        "billing_invoices",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("billing_invoices")
    op.drop_table("whatsapp_usage_records")
