"""Create tenant-scoped automation definitions and executions.

Revision ID: 009
Revises: 008
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, Sequence[str], None] = "008"
branch_labels = None
depends_on = None


AUTOMATION_PERMISSIONS = (
    ("automation:read", "View automations and execution history."),
    ("automation:create", "Create automations."),
    ("automation:update", "Edit and validate automations."),
    ("automation:delete", "Archive automations."),
    ("automation:publish", "Activate and pause automations."),
)


def upgrade() -> None:
    op.create_table(
        "automations",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("trigger_type", sa.String(30), server_default="inbound_message", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('draft','active','paused','archived')", name="ck_automations_status"),
        sa.CheckConstraint("trigger_type IN ('inbound_message')", name="ck_automations_trigger_type"),
        sa.CheckConstraint("version >= 1", name="ck_automations_version"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_automations_tenant_id"),
    )
    op.create_index("ix_automations_tenant_status_updated", "automations", ["tenant_id", "status", "updated_at"])

    op.create_table(
        "automation_nodes",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("automation_id", sa.UUID(), nullable=False),
        sa.Column("node_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("node_type IN ('trigger_message','message_contains','send_text','send_template','assign_conversation','change_conversation_status')", name="ck_automation_nodes_type"),
        sa.CheckConstraint("sort_order >= 0", name="ck_automation_nodes_sort_order"),
        sa.ForeignKeyConstraint(["tenant_id", "automation_id"], ["automations.tenant_id", "automations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "automation_id", "id", name="uq_automation_nodes_tenant_automation_id"),
    )
    op.create_index("ix_automation_nodes_automation_order", "automation_nodes", ["tenant_id", "automation_id", "sort_order"])

    op.create_table(
        "automation_edges",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("automation_id", sa.UUID(), nullable=False),
        sa.Column("source_node_id", sa.UUID(), nullable=False),
        sa.Column("target_node_id", sa.UUID(), nullable=False),
        sa.Column("branch", sa.String(10), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_node_id <> target_node_id", name="ck_automation_edges_not_self"),
        sa.CheckConstraint("branch IS NULL OR branch IN ('true','false')", name="ck_automation_edges_branch"),
        sa.ForeignKeyConstraint(["tenant_id", "automation_id"], ["automations.tenant_id", "automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "automation_id", "source_node_id"], ["automation_nodes.tenant_id", "automation_nodes.automation_id", "automation_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "automation_id", "target_node_id"], ["automation_nodes.tenant_id", "automation_nodes.automation_id", "automation_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("automation_id", "source_node_id", "branch", name="uq_automation_edges_source_branch"),
    )
    op.create_index("ix_automation_edges_tenant_automation", "automation_edges", ["tenant_id", "automation_id"])

    op.create_table(
        "automation_executions",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("automation_id", sa.UUID(), nullable=False),
        sa.Column("automation_version", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("trigger_message_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("current_node_id", sa.UUID(), nullable=True),
        sa.Column("flow_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('queued','running','completed','failed','cancelled')", name="ck_automation_executions_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["automation_id"], ["automations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trigger_message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_automation_executions_tenant_id"),
        sa.UniqueConstraint("tenant_id", "automation_id", "trigger_message_id", name="uq_automation_execution_trigger"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_automation_execution_idempotency"),
    )
    op.create_index("ix_automation_executions_worker", "automation_executions", ["status", "updated_at"])
    op.create_index("ix_automation_executions_tenant_started", "automation_executions", ["tenant_id", "started_at"])

    op.create_table(
        "automation_execution_logs",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.UUID(), nullable=True),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "execution_id"], ["automation_executions.tenant_id", "automation_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["automation_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_execution_logs_tenant_execution", "automation_execution_logs", ["tenant_id", "execution_id", "created_at"])

    for name, description in AUTOMATION_PERMISSIONS:
        op.execute(sa.text("INSERT INTO permissions (id,name,description,is_active) VALUES (gen_random_uuid(),:name,:description,true) ON CONFLICT (name) DO UPDATE SET description=EXCLUDED.description,is_active=true").bindparams(name=name, description=description))
    op.execute(sa.text("INSERT INTO role_permissions(role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.name IN ('OWNER','ADMIN','MANAGER') AND p.name LIKE 'automation:%' ON CONFLICT DO NOTHING"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id=p.id AND p.name LIKE 'automation:%'"))
    op.execute(sa.text("DELETE FROM permissions WHERE name LIKE 'automation:%'"))
    op.drop_index("ix_automation_execution_logs_tenant_execution", table_name="automation_execution_logs")
    op.drop_table("automation_execution_logs")
    op.drop_index("ix_automation_executions_tenant_started", table_name="automation_executions")
    op.drop_index("ix_automation_executions_worker", table_name="automation_executions")
    op.drop_table("automation_executions")
    op.drop_index("ix_automation_edges_tenant_automation", table_name="automation_edges")
    op.drop_table("automation_edges")
    op.drop_index("ix_automation_nodes_automation_order", table_name="automation_nodes")
    op.drop_table("automation_nodes")
    op.drop_index("ix_automations_tenant_status_updated", table_name="automations")
    op.drop_table("automations")
