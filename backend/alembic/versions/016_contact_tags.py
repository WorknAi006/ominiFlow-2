"""create tags and contact_tags

Revision ID: 016
Revises: 015

Adds tenant-scoped contact tags and the contact<->tag association. No
existing table is changed; contacts and their identities/conversations are
untouched. Deleting a contact or a tag removes only the association rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, Sequence[str], None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("color", sa.String(length=9), server_default="#176b59", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tags_tenant_name"),
    )
    op.create_index(op.f("ix_tags_tenant_id"), "tags", ["tenant_id"], unique=False)

    op.create_table(
        "contact_tags",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id", "tag_id", name="uq_contact_tags_contact_tag"),
    )
    op.create_index(op.f("ix_contact_tags_tenant_id"), "contact_tags", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_contact_tags_contact_id"), "contact_tags", ["contact_id"], unique=False)
    op.create_index(op.f("ix_contact_tags_tag_id"), "contact_tags", ["tag_id"], unique=False)
    op.create_index("ix_contact_tags_tenant_tag", "contact_tags", ["tenant_id", "tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contact_tags_tenant_tag", table_name="contact_tags")
    op.drop_index(op.f("ix_contact_tags_tag_id"), table_name="contact_tags")
    op.drop_index(op.f("ix_contact_tags_contact_id"), table_name="contact_tags")
    op.drop_index(op.f("ix_contact_tags_tenant_id"), table_name="contact_tags")
    op.drop_table("contact_tags")
    op.drop_index(op.f("ix_tags_tenant_id"), table_name="tags")
    op.drop_table("tags")
