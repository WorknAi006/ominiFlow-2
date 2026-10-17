"""Align automation node and edge tenant constraints with ORM metadata.

Revision ID: 010
Revises: 009
"""
from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, Sequence[str], None] = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_automation_nodes_tenant_id_tenants",
        "automation_nodes", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_automation_edges_tenant_id_tenants",
        "automation_edges", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_automation_edges_tenant_id_tenants", "automation_edges", type_="foreignkey")
    op.drop_constraint("fk_automation_nodes_tenant_id_tenants", "automation_nodes", type_="foreignkey")
