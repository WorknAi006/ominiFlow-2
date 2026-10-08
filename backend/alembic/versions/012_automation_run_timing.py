"""Track bounded worker run time separately from persisted delay waits.

Revision ID: 012
Revises: 011
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, Sequence[str], None] = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("automation_executions", sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("automation_executions", "run_started_at")
