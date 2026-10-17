"""Add automation retry, delay, worker health, and advanced conditions.

Revision ID: 011
Revises: 010
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, Sequence[str], None] = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_automation_nodes_type", "automation_nodes", type_="check")
    op.create_check_constraint(
        "ck_automation_nodes_type", "automation_nodes",
        "node_type IN ('trigger_message','message_contains','send_text','send_template','assign_conversation','change_conversation_status','delay','business_hours')",
    )
    op.drop_constraint("ck_automation_executions_status", "automation_executions", type_="check")
    op.create_check_constraint(
        "ck_automation_executions_status", "automation_executions",
        "status IN ('queued','running','retrying','completed','failed','cancelled')",
    )
    op.add_column("automation_executions", sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False))
    op.add_column("automation_executions", sa.Column("step_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("automation_executions", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("automation_executions", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("automation_executions", sa.Column("worker_id", sa.String(100), nullable=True))
    op.add_column("automation_executions", sa.Column("resume_node_id", sa.UUID(), nullable=True))
    op.add_column("automation_executions", sa.Column("last_error_type", sa.String(50), nullable=True))
    op.create_check_constraint("ck_automation_executions_attempts", "automation_executions", "attempt_count >= 0 AND max_attempts >= 1 AND step_count >= 0")
    op.execute("UPDATE automation_executions SET claimed_at = updated_at WHERE status = 'running' AND claimed_at IS NULL")
    op.drop_index("ix_automation_executions_worker", table_name="automation_executions")
    op.create_index("ix_automation_executions_worker", "automation_executions", ["status", "next_retry_at", "created_at"])
    op.create_index("ix_automation_executions_claimed", "automation_executions", ["status", "claimed_at"])
    op.create_table(
        "automation_worker_heartbeats",
        sa.Column("worker_id", sa.String(100), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_batch_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("processed_count >= 0", name="ck_automation_worker_processed_count"),
        sa.PrimaryKeyConstraint("worker_id"),
    )
    op.create_index("ix_automation_worker_heartbeat_last_seen", "automation_worker_heartbeats", ["last_seen_at"])


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM automation_nodes WHERE node_type IN ('delay','business_hours'))
        OR EXISTS (SELECT 1 FROM automation_executions WHERE status = 'retrying' OR resume_node_id IS NOT NULL OR next_retry_at IS NOT NULL)
      THEN RAISE EXCEPTION 'Cannot downgrade automation reliability while Phase 2 node or scheduled execution data exists.';
      END IF;
    END $$;
    """)
    op.drop_index("ix_automation_worker_heartbeat_last_seen", table_name="automation_worker_heartbeats")
    op.drop_table("automation_worker_heartbeats")
    op.drop_index("ix_automation_executions_claimed", table_name="automation_executions")
    op.drop_index("ix_automation_executions_worker", table_name="automation_executions")
    op.create_index("ix_automation_executions_worker", "automation_executions", ["status", "updated_at"])
    op.drop_constraint("ck_automation_executions_attempts", "automation_executions", type_="check")
    for column in ("last_error_type", "resume_node_id", "worker_id", "next_retry_at", "claimed_at", "step_count", "max_attempts"):
        op.drop_column("automation_executions", column)
    op.drop_constraint("ck_automation_executions_status", "automation_executions", type_="check")
    op.create_check_constraint("ck_automation_executions_status", "automation_executions", "status IN ('queued','running','completed','failed','cancelled')")
    op.drop_constraint("ck_automation_nodes_type", "automation_nodes", type_="check")
    op.create_check_constraint("ck_automation_nodes_type", "automation_nodes", "node_type IN ('trigger_message','message_contains','send_text','send_template','assign_conversation','change_conversation_status')")
