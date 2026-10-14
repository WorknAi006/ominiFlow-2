"""Replace flow-graph automations with rule-based automations

Drops the node/edge/execution automation engine and creates the rule-based
model: a single ``automations`` table (WHEN/IF/THEN) plus ``automation_runs``
for monitoring.

Revision ID: b7a1c9e24f10
Revises: 2079f47d4520
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7a1c9e24f10'
down_revision: Union[str, Sequence[str], None] = '2079f47d4520'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # keywords.flow_id references automations; detach it before the drop and
    # clear the now-dangling references (old automation ids are being removed).
    op.drop_constraint('keywords_flow_id_fkey', 'keywords', type_='foreignkey')

    # Drop the old flow-graph engine (children first).
    op.drop_table('automation_execution_logs')
    op.drop_table('automation_executions')
    op.drop_table('automation_edges')
    op.drop_table('automation_nodes')
    op.drop_table('automation_worker_heartbeats')
    op.drop_table('automations')

    op.create_table(
        'automations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('trigger_type', sa.String(length=40), nullable=False),
        sa.Column('trigger_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('match_type', sa.String(length=3), server_default='all', nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('then_mode', sa.String(length=20), server_default='run_actions', nullable=False),
        sa.Column('flow_ref', sa.String(length=150), nullable=True),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('runs_first', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("trigger_type IN ('new_contact_created','tag_added_to_contact','chat_status_changed','chat_stuck_in_mode')", name='ck_automations_trigger_type'),
        sa.CheckConstraint("match_type IN ('all','any')", name='ck_automations_match_type'),
        sa.CheckConstraint("then_mode IN ('run_actions','start_flow')", name='ck_automations_then_mode'),
        sa.CheckConstraint('runs_first >= 0', name='ck_automations_runs_first'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_automations_tenant_trigger_active', 'automations', ['tenant_id', 'trigger_type', 'is_active'], unique=False)
    op.create_index('ix_automations_tenant_updated', 'automations', ['tenant_id', 'updated_at'], unique=False)

    op.create_table(
        'automation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('automation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trigger_type', sa.String(length=40), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('matched', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('actions_run', sa.Integer(), server_default='0', nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('success','failed','skipped')", name='ck_automation_runs_status'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['automation_id'], ['automations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_automation_runs_tenant_created', 'automation_runs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_automation_runs_automation_created', 'automation_runs', ['automation_id', 'created_at'], unique=False)
    op.create_index('ix_automation_runs_dedupe', 'automation_runs', ['automation_id', 'conversation_id', 'created_at'], unique=False)

    # Old automation ids are gone; clear stale keyword links and re-point the FK
    # at the new automations table.
    op.execute('UPDATE keywords SET flow_id = NULL')
    op.create_foreign_key('keywords_flow_id_fkey', 'keywords', 'automations', ['flow_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    # The old flow-graph engine is not restored; only the new tables are dropped.
    op.drop_constraint('keywords_flow_id_fkey', 'keywords', type_='foreignkey')
    op.execute('UPDATE keywords SET flow_id = NULL')
    op.drop_table('automation_runs')
    op.drop_table('automations')
