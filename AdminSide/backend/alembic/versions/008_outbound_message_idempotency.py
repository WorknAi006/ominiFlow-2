"""Add tenant-scoped outbound request idempotency.

Revision ID: 008
Revises: 007
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("idempotency_key", sa.UUID(), nullable=True))
    op.add_column("messages", sa.Column("idempotency_payload_hash", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_messages_tenant_idempotency_key",
        "messages",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_messages_tenant_idempotency_key", table_name="messages")
    op.drop_column("messages", "idempotency_payload_hash")
    op.drop_column("messages", "idempotency_key")
