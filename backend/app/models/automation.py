import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AutomationStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AutomationTrigger(StrEnum):
    INBOUND_MESSAGE = "inbound_message"


class AutomationNodeType(StrEnum):
    TRIGGER_MESSAGE = "trigger_message"
    MESSAGE_CONTAINS = "message_contains"
    SEND_TEXT = "send_text"
    SEND_TEMPLATE = "send_template"
    ASSIGN_CONVERSATION = "assign_conversation"
    CHANGE_CONVERSATION_STATUS = "change_conversation_status"
    DELAY = "delay"
    BUSINESS_HOURS = "business_hours"


class AutomationExecutionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Automation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=AutomationStatus.DRAFT, server_default=AutomationStatus.DRAFT.value, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(30), default=AutomationTrigger.INBOUND_MESSAGE, server_default=AutomationTrigger.INBOUND_MESSAGE.value, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('draft','active','paused','archived')", name="ck_automations_status"),
        CheckConstraint("trigger_type IN ('inbound_message')", name="ck_automations_trigger_type"),
        CheckConstraint("version >= 1", name="ck_automations_version"),
        UniqueConstraint("tenant_id", "id", name="uq_automations_tenant_id"),
        Index("ix_automations_tenant_status_updated", "tenant_id", "status", "updated_at"),
    )


class AutomationNode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automation_nodes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    automation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "automation_id"], ["automations.tenant_id", "automations.id"], ondelete="CASCADE"),
        CheckConstraint("node_type IN ('trigger_message','message_contains','send_text','send_template','assign_conversation','change_conversation_status','delay','business_hours')", name="ck_automation_nodes_type"),
        CheckConstraint("sort_order >= 0", name="ck_automation_nodes_sort_order"),
        UniqueConstraint("tenant_id", "automation_id", "id", name="uq_automation_nodes_tenant_automation_id"),
        Index("ix_automation_nodes_automation_order", "tenant_id", "automation_id", "sort_order"),
    )


class AutomationEdge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automation_edges"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    automation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(10), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "automation_id"], ["automations.tenant_id", "automations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["tenant_id", "automation_id", "source_node_id"], ["automation_nodes.tenant_id", "automation_nodes.automation_id", "automation_nodes.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["tenant_id", "automation_id", "target_node_id"], ["automation_nodes.tenant_id", "automation_nodes.automation_id", "automation_nodes.id"], ondelete="CASCADE"),
        CheckConstraint("source_node_id <> target_node_id", name="ck_automation_edges_not_self"),
        CheckConstraint("branch IS NULL OR branch IN ('true','false')", name="ck_automation_edges_branch"),
        UniqueConstraint("automation_id", "source_node_id", "branch", name="uq_automation_edges_source_branch"),
        Index("ix_automation_edges_tenant_automation", "tenant_id", "automation_id"),
    )


class AutomationExecution(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automation_executions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    automation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False)
    automation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    trigger_message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AutomationExecutionStatus.QUEUED, server_default=AutomationExecutionStatus.QUEUED.value, nullable=False)
    current_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    flow_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resume_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('queued','running','retrying','completed','failed','cancelled')", name="ck_automation_executions_status"),
        CheckConstraint("attempt_count >= 0 AND max_attempts >= 1 AND step_count >= 0", name="ck_automation_executions_attempts"),
        UniqueConstraint("tenant_id", "id", name="uq_automation_executions_tenant_id"),
        UniqueConstraint("tenant_id", "automation_id", "trigger_message_id", name="uq_automation_execution_trigger"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_automation_execution_idempotency"),
        Index("ix_automation_executions_worker", "status", "next_retry_at", "created_at"),
        Index("ix_automation_executions_claimed", "status", "claimed_at"),
        Index("ix_automation_executions_tenant_started", "tenant_id", "started_at"),
    )


class AutomationExecutionLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "automation_execution_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("automation_nodes.id", ondelete="SET NULL"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "execution_id"], ["automation_executions.tenant_id", "automation_executions.id"], ondelete="CASCADE"),
        Index("ix_automation_execution_logs_tenant_execution", "tenant_id", "execution_id", "created_at"),
    )


class AutomationWorkerHeartbeat(Base):
    __tablename__ = "automation_worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_batch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("processed_count >= 0", name="ck_automation_worker_processed_count"),
        Index("ix_automation_worker_heartbeat_last_seen", "last_seen_at"),
    )
