import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class FlowSessionStatus(StrEnum):
    ACTIVE = "active"        # being walked right now
    WAITING = "waiting"      # paused for a customer reply or a delay
    COMPLETED = "completed"
    FAILED = "failed"


class FlowSessionWait(StrEnum):
    REPLY = "reply"
    DELAY = "delay"


_STATUS_SQL = ",".join(f"'{s.value}'" for s in FlowSessionStatus)


class FlowSession(Base, UUIDMixin, TimestampMixin):
    """
    One running instance of a flow for a conversation. The flow graph is
    snapshotted at start so mid-flow edits never break a live run. The engine
    walks nodes, pausing (WAITING) at button/list/get-user-data nodes until the
    customer replies, or at delay nodes until ``resume_at``.
    """

    __tablename__ = "flow_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    flow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(10), default=FlowSessionStatus.ACTIVE, server_default=FlowSessionStatus.ACTIVE.value, nullable=False)
    current_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    waiting_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    wait_kind: Mapped[str | None] = mapped_column(String(10), nullable=True)
    resume_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Graph snapshot + captured variables.
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    variables: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    # A customer reply captured in the inbound transaction; the worker resumes
    # the flow with it (sending happens outside the webhook).
    pending_reply: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    pending_reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_SQL})", name="ck_flow_sessions_status"),
        # At most one live session per conversation.
        Index(
            "uq_flow_sessions_active_conversation",
            "tenant_id", "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('active','waiting')"),
        ),
        Index("ix_flow_sessions_resume", "status", "wait_kind", "resume_at"),
        Index("ix_flow_sessions_tenant_conv", "tenant_id", "conversation_id"),
    )
