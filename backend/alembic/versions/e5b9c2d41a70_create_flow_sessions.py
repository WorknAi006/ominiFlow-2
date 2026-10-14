"""Create flow_sessions (stateful flow execution)

Revision ID: e5b9c2d41a70
Revises: d4e2f7a9c130
Create Date: 2026-10-13 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5b9c2d41a70'
down_revision: Union[str, Sequence[str], None] = 'd4e2f7a9c130'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'flow_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=10), server_default='active', nullable=False),
        sa.Column('current_node_id', sa.String(length=100), nullable=True),
        sa.Column('waiting_node_id', sa.String(length=100), nullable=True),
        sa.Column('wait_kind', sa.String(length=10), nullable=True),
        sa.Column('resume_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('nodes', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('edges', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('pending_reply', sa.String(length=4096), nullable=True),
        sa.Column('pending_reply_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('detail', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active','waiting','completed','failed')", name='ck_flow_sessions_status'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'uq_flow_sessions_active_conversation', 'flow_sessions',
        ['tenant_id', 'conversation_id'], unique=True,
        postgresql_where=sa.text("status IN ('active','waiting')"),
    )
    op.create_index('ix_flow_sessions_resume', 'flow_sessions', ['status', 'wait_kind', 'resume_at'], unique=False)
    op.create_index('ix_flow_sessions_tenant_conv', 'flow_sessions', ['tenant_id', 'conversation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('flow_sessions')
