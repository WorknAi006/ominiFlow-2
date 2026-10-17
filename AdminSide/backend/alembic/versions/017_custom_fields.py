"""create custom_field_definitions and contact_field_values

Revision ID: 017
Revises: 016

Adds tenant-scoped custom field definitions and per-contact values. No
existing table is changed; contacts are untouched. Deleting a contact or a
field definition removes only its values.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, Sequence[str], None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TYPES = "field_type IN ('text', 'number', 'date', 'select', 'multiselect', 'boolean')"


def upgrade() -> None:
    op.create_table(
        "custom_field_definitions",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("field_type", sa.String(length=20), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(_TYPES, name="ck_custom_field_type"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_custom_field_tenant_key"),
    )
    op.create_index(op.f("ix_custom_field_definitions_tenant_id"), "custom_field_definitions", ["tenant_id"], unique=False)

    op.create_table(
        "contact_field_values",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["field_id"], ["custom_field_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id", "field_id", name="uq_contact_field_values_contact_field"),
    )
    op.create_index(op.f("ix_contact_field_values_tenant_id"), "contact_field_values", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_contact_field_values_contact_id"), "contact_field_values", ["contact_id"], unique=False)
    op.create_index(op.f("ix_contact_field_values_field_id"), "contact_field_values", ["field_id"], unique=False)
    op.create_index("ix_contact_field_values_tenant_field", "contact_field_values", ["tenant_id", "field_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contact_field_values_tenant_field", table_name="contact_field_values")
    op.drop_index(op.f("ix_contact_field_values_field_id"), table_name="contact_field_values")
    op.drop_index(op.f("ix_contact_field_values_contact_id"), table_name="contact_field_values")
    op.drop_index(op.f("ix_contact_field_values_tenant_id"), table_name="contact_field_values")
    op.drop_table("contact_field_values")
    op.drop_index(op.f("ix_custom_field_definitions_tenant_id"), table_name="custom_field_definitions")
    op.drop_table("custom_field_definitions")
