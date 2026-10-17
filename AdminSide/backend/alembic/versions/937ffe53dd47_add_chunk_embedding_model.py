"""add chunk embedding model

Revision ID: 937ffe53dd47
Revises: a38bb6041762
Create Date: 2026-10-10 11:38:59.899426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '937ffe53dd47'
down_revision: Union[str, Sequence[str], None] = 'a38bb6041762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_chunk_embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('chunk_id', sa.UUID(), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('embedding_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('embedding', sa.ARRAY(sa.Float()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['chunk_id'], ['knowledge_document_chunks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id', 'chunk_id'], ['knowledge_document_chunks.tenant_id', 'knowledge_document_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_id', 'embedding_model', 'embedding_version', name='uq_chunk_embedding_model_version'),
        sa.UniqueConstraint('tenant_id', 'id', name='uq_knowledge_embeddings_tenant_id')
    )
    op.create_index(op.f('ix_knowledge_chunk_embeddings_chunk_id'), 'knowledge_chunk_embeddings', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_knowledge_chunk_embeddings_tenant_id'), 'knowledge_chunk_embeddings', ['tenant_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_chunk_embeddings_tenant_id'), table_name='knowledge_chunk_embeddings')
    op.drop_index(op.f('ix_knowledge_chunk_embeddings_chunk_id'), table_name='knowledge_chunk_embeddings')
    op.drop_table('knowledge_chunk_embeddings')
