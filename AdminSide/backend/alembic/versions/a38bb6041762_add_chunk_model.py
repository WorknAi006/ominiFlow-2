"""add chunk model

Revision ID: a38bb6041762
Revises: e12fdee81373
Create Date: 2026-10-10 11:29:17.149463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a38bb6041762'
down_revision: Union[str, Sequence[str], None] = 'e12fdee81373'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id', 'document_id'], ['knowledge_documents.tenant_id', 'knowledge_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_knowledge_chunks_doc_index'),
        sa.UniqueConstraint('tenant_id', 'id', name='uq_knowledge_chunks_tenant_id')
    )
    op.create_index(op.f('ix_knowledge_document_chunks_document_id'), 'knowledge_document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_knowledge_document_chunks_tenant_id'), 'knowledge_document_chunks', ['tenant_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_document_chunks_tenant_id'), table_name='knowledge_document_chunks')
    op.drop_index(op.f('ix_knowledge_document_chunks_document_id'), table_name='knowledge_document_chunks')
    op.drop_table('knowledge_document_chunks')
