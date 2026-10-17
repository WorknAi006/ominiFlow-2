"""add storage fields to KnowledgeDocument

Revision ID: e12fdee81373
Revises: d9134a6ef247
Create Date: 2026-10-10 11:01:49.593303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e12fdee81373'
down_revision: Union[str, Sequence[str], None] = 'd9134a6ef247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('knowledge_documents', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('knowledge_documents', sa.Column('mime_type', sa.String(length=100), nullable=True))
    op.add_column('knowledge_documents', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('knowledge_documents', sa.Column('storage_key', sa.String(length=400), nullable=True))
    op.add_column('knowledge_documents', sa.Column('storage_backend', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('knowledge_documents', 'storage_backend')
    op.drop_column('knowledge_documents', 'storage_key')
    op.drop_column('knowledge_documents', 'file_size')
    op.drop_column('knowledge_documents', 'mime_type')
    op.drop_column('knowledge_documents', 'original_filename')
