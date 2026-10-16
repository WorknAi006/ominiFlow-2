"""Add platform template library and super-admin flag.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_platform_super_admin",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_users_is_platform_super_admin",
        "users",
        ["is_platform_super_admin"],
        unique=False,
    )
    op.create_table(
        "platform_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("label", sa.String(length=150), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "language", name="uq_platform_templates_name_language"),
    )


def downgrade() -> None:
    op.drop_table("platform_templates")
    op.drop_index("ix_users_is_platform_super_admin", table_name="users")
    op.drop_column("users", "is_platform_super_admin")
