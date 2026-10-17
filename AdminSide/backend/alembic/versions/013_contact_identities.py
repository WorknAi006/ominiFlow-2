"""create contact_identities

Revision ID: 013
Revises: 012

Adds per-channel contact identities so one contact can be addressed on
multiple channels. The existing contacts.normalized_phone_number column and
its unique index are left untouched for WhatsApp backward compatibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contact_identities",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("channel_type", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "channel_type", "external_id",
            name="uq_contact_identities_tenant_channel_external",
        ),
    )
    op.create_index(op.f("ix_contact_identities_contact_id"), "contact_identities", ["contact_id"], unique=False)
    op.create_index(op.f("ix_contact_identities_tenant_id"), "contact_identities", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contact_identities_tenant_id"), table_name="contact_identities")
    op.drop_index(op.f("ix_contact_identities_contact_id"), table_name="contact_identities")
    op.drop_table("contact_identities")
