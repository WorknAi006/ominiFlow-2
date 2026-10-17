"""Add tenant_routing_configs (global fallback routing) and make keyword_triggers.keyword_id nullable

Revision ID: f1a2b3c4d5e6
Revises: e5b9c2d41a70
Create Date: 2026-10-14 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e5b9c2d41a70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tenant_routing_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fallback_action', sa.String(length=20), server_default='none', nullable=False),
        sa.Column('fallback_flow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fallback_flow_id'], ['flows.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_tenant_routing_configs_tenant_id', 'tenant_routing_configs',
        ['tenant_id'], unique=True,
    )

    # A global-routing fallback trigger has no originating keyword.
    op.alter_column(
        'keyword_triggers', 'keyword_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'keyword_triggers', 'keyword_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_index('ix_tenant_routing_configs_tenant_id', table_name='tenant_routing_configs')
    op.drop_table('tenant_routing_configs')
