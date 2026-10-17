"""Create flows (visual chat-flow builder)

Revision ID: c3f8d1a6b920
Revises: b7a1c9e24f10
Create Date: 2026-10-13 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3f8d1a6b920'
down_revision: Union[str, Sequence[str], None] = 'b7a1c9e24f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'flows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('status', sa.String(length=10), server_default='draft', nullable=False),
        sa.Column('channels', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('nodes', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('edges', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('draft','active')", name='ck_flows_status'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_flows_tenant_updated', 'flows', ['tenant_id', 'updated_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('flows')
