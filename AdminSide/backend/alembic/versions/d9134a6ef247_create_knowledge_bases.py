"""create knowledge bases

Revision ID: d9134a6ef247
Revises: cfedf99f27ca
Create Date: 2026-10-10 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd9134a6ef247'
down_revision: Union[str, Sequence[str], None] = 'cfedf99f27ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('knowledge_bases',
    sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'id', name='uq_knowledge_bases_tenant_id')
    )
    op.create_index(op.f('ix_knowledge_bases_tenant_id'), 'knowledge_bases', ['tenant_id'], unique=False)
    
    op.create_table('knowledge_documents',
    sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('knowledge_base_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('source_type', sa.String(length=50), nullable=False),
    sa.Column('source_reference', sa.Text(), nullable=True),
    sa.Column('processing_status', sa.String(length=50), server_default='pending', nullable=False),
    sa.Column('error_summary', sa.Text(), nullable=True),
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id', 'knowledge_base_id'], ['knowledge_bases.tenant_id', 'knowledge_bases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'id', name='uq_knowledge_documents_tenant_id')
    )
    op.create_index(op.f('ix_knowledge_documents_knowledge_base_id'), 'knowledge_documents', ['knowledge_base_id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_tenant_id'), 'knowledge_documents', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_documents_tenant_id'), table_name='knowledge_documents')
    op.drop_index(op.f('ix_knowledge_documents_knowledge_base_id'), table_name='knowledge_documents')
    op.drop_table('knowledge_documents')
    op.drop_index(op.f('ix_knowledge_bases_tenant_id'), table_name='knowledge_bases')
    op.drop_table('knowledge_bases')
