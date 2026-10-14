"""fix missing server_defaults for chunks and embeddings

Revision ID: 30d0b0ddc02e
Revises: 937ffe53dd47
Create Date: 2026-10-10 12:46:26.886111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30d0b0ddc02e'
down_revision: Union[str, Sequence[str], None] = '937ffe53dd47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('knowledge_document_chunks', 'created_at', server_default=sa.text('now()'))
    op.alter_column('knowledge_document_chunks', 'updated_at', server_default=sa.text('now()'))
    op.alter_column('knowledge_chunk_embeddings', 'created_at', server_default=sa.text('now()'))
    op.alter_column('knowledge_chunk_embeddings', 'updated_at', server_default=sa.text('now()'))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('knowledge_chunk_embeddings', 'updated_at', server_default=None)
    op.alter_column('knowledge_chunk_embeddings', 'created_at', server_default=None)
    op.alter_column('knowledge_document_chunks', 'updated_at', server_default=None)
    op.alter_column('knowledge_document_chunks', 'created_at', server_default=None)
