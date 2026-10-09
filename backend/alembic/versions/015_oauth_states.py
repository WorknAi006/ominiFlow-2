"""create oauth_states

Revision ID: 015
Revises: 014

Adds a small, short-lived, single-use server-side state table for tenant
self-service Meta (Facebook/Instagram) OAuth onboarding. No existing table
is changed; channel_connections, contacts, contact_identities,
conversations and messages are reused unchanged.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, Sequence[str], None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("state_token", sa.String(length=128), nullable=False),
        sa.Column("selection_token", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("user_token_encrypted", sa.Text(), nullable=True),
        sa.Column("assets", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.String(length=200), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("provider IN ('facebook', 'instagram')", name="ck_oauth_states_provider"),
        sa.CheckConstraint("status IN ('pending', 'discovered', 'consumed')", name="ck_oauth_states_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_token", name="uq_oauth_states_state_token"),
        sa.UniqueConstraint("selection_token", name="uq_oauth_states_selection_token"),
    )
    op.create_index(op.f("ix_oauth_states_tenant_id"), "oauth_states", ["tenant_id"], unique=False)
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_oauth_states_expires_at", table_name="oauth_states")
    op.drop_index(op.f("ix_oauth_states_tenant_id"), table_name="oauth_states")
    op.drop_table("oauth_states")
