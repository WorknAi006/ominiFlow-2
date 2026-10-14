import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AutomationTrigger(StrEnum):
    """When something happens — the event that starts an automation rule."""

    NEW_CONTACT_CREATED = "new_contact_created"
    TAG_ADDED_TO_CONTACT = "tag_added_to_contact"
    CHAT_STATUS_CHANGED = "chat_status_changed"
    CHAT_STUCK_IN_MODE = "chat_stuck_in_mode"


class AutomationThenMode(StrEnum):
    RUN_ACTIONS = "run_actions"
    START_FLOW = "start_flow"


class AutomationMatchType(StrEnum):
    ALL = "all"
    ANY = "any"


class AutomationRunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


_TRIGGERS_SQL = ",".join(f"'{t.value}'" for t in AutomationTrigger)
_RUN_STATUS_SQL = ",".join(f"'{s.value}'" for s in AutomationRunStatus)


class Automation(Base, UUIDMixin, TimestampMixin):
    """
    A WHEN / IF / THEN rule. On its trigger event the conditions are
    evaluated (match all or any) and, when they pass, the ordered actions
    run. Rules are tenant-scoped and run in ascending ``runs_first`` order.
    """

    __tablename__ = "automations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # Extra trigger params, e.g. {"mode": "bot", "hours": 3} for chat_stuck_in_mode.
    trigger_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    match_type: Mapped[str] = mapped_column(String(3), default=AutomationMatchType.ALL, server_default=AutomationMatchType.ALL.value, nullable=False)
    # List of {"field": str, "operator": str, "value": str}.
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    then_mode: Mapped[str] = mapped_column(String(20), default=AutomationThenMode.RUN_ACTIONS, server_default=AutomationThenMode.RUN_ACTIONS.value, nullable=False)
    # Optional reference used when then_mode == start_flow.
    flow_ref: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # List of {"type": str, "config": dict}.
    actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    runs_first: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint(f"trigger_type IN ({_TRIGGERS_SQL})", name="ck_automations_trigger_type"),
        CheckConstraint("match_type IN ('all','any')", name="ck_automations_match_type"),
        CheckConstraint("then_mode IN ('run_actions','start_flow')", name="ck_automations_then_mode"),
        CheckConstraint("runs_first >= 0", name="ck_automations_runs_first"),
        Index("ix_automations_tenant_trigger_active", "tenant_id", "trigger_type", "is_active"),
        Index("ix_automations_tenant_updated", "tenant_id", "updated_at"),
    )


class AutomationRun(Base, UUIDMixin, TimestampMixin):
    """One evaluation of a rule against a trigger event, for monitoring."""

    __tablename__ = "automation_runs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    automation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    actions_run: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(f"status IN ({_RUN_STATUS_SQL})", name="ck_automation_runs_status"),
        Index("ix_automation_runs_tenant_created", "tenant_id", "created_at"),
        Index("ix_automation_runs_automation_created", "automation_id", "created_at"),
        Index("ix_automation_runs_dedupe", "automation_id", "conversation_id", "created_at"),
    )
