"""Keyword → flow triggers: repoint FK to flows, add ends_with, add trigger log

Revision ID: d4e2f7a9c130
Revises: c3f8d1a6b920
Create Date: 2026-10-13 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e2f7a9c130'
down_revision: Union[str, Sequence[str], None] = 'c3f8d1a6b920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) Allow 'ends_with' as a match type.
    op.drop_constraint('ck_keywords_match_type', 'keywords', type_='check')
    op.create_check_constraint(
        'ck_keywords_match_type', 'keywords',
        "match_type IN ('exact', 'contains', 'starts_with', 'ends_with')",
    )

    # 2) Re-point keywords.flow_id from automations -> flows. Existing values
    #    referenced rule automations, not flows, so clear them.
    op.drop_constraint('keywords_flow_id_fkey', 'keywords', type_='foreignkey')
    op.execute('UPDATE keywords SET flow_id = NULL')
    op.create_foreign_key('keywords_flow_id_fkey', 'keywords', 'flows', ['flow_id'], ['id'], ondelete='SET NULL')

    # 3) Durable, idempotent keyword-trigger log.
    op.create_table(
        'keyword_triggers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('keyword_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_type', sa.String(length=20), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('matched','delivered','failed','skipped')", name='ck_keyword_triggers_status'),
        sa.CheckConstraint("action IN ('run_flow','send_text','none')", name='ck_keyword_triggers_action'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['keyword_id'], ['keywords.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'message_id', name='uq_keyword_triggers_message'),
    )
    op.create_index('ix_keyword_triggers_tenant_created', 'keyword_triggers', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_keyword_triggers_keyword', 'keyword_triggers', ['keyword_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('keyword_triggers')
    op.drop_constraint('keywords_flow_id_fkey', 'keywords', type_='foreignkey')
    op.execute('UPDATE keywords SET flow_id = NULL')
    op.create_foreign_key('keywords_flow_id_fkey', 'keywords', 'automations', ['flow_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('ck_keywords_match_type', 'keywords', type_='check')
    op.create_check_constraint(
        'ck_keywords_match_type', 'keywords',
        "match_type IN ('exact', 'contains', 'starts_with')",
    )
