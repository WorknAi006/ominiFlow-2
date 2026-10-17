"""Add credit_usages ledger and ai_reply keyword-trigger action

Revision ID: b3c4d5e6f7a8
Revises: fb1a501b938a
Create Date: 2026-10-14 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'fb1a501b938a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'credit_usages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('credits', sa.Numeric(10, 2), nullable=False),
        sa.Column('balance_after', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_credit_usages_tenant_id', 'credit_usages', ['tenant_id'])
    op.create_index('ix_credit_usages_tenant_created', 'credit_usages', ['tenant_id', 'created_at'])

    # Allow the new ai_reply action on keyword_triggers.
    op.drop_constraint('ck_keyword_triggers_action', 'keyword_triggers', type_='check')
    op.create_check_constraint(
        'ck_keyword_triggers_action', 'keyword_triggers',
        "action IN ('run_flow','send_text','ai_reply','none')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_keyword_triggers_action', 'keyword_triggers', type_='check')
    op.create_check_constraint(
        'ck_keyword_triggers_action', 'keyword_triggers',
        "action IN ('run_flow','send_text','none')",
    )
    op.drop_index('ix_credit_usages_tenant_created', table_name='credit_usages')
    op.drop_index('ix_credit_usages_tenant_id', table_name='credit_usages')
    op.drop_table('credit_usages')
