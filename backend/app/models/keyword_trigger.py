import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class KeywordTriggerStatus(StrEnum):
    MATCHED = "matched"      # a keyword matched; action recorded
    DELIVERED = "delivered"  # reply / flow entry message was dispatched
    FAILED = "failed"        # dispatch attempted but failed
    SKIPPED = "skipped"      # matched but nothing to do (no flow, no text)


class KeywordTriggerAction(StrEnum):
    RUN_FLOW = "run_flow"
    SEND_TEXT = "send_text"
    NONE = "none"


_STATUS_SQL = ",".join(f"'{s.value}'" for s in KeywordTriggerStatus)
_ACTION_SQL = ",".join(f"'{a.value}'" for a in KeywordTriggerAction)


class KeywordTrigger(Base, UUIDMixin, TimestampMixin):
    """
    One recorded keyword match against an inbound message. The unique
    (tenant_id, message_id) pair makes triggering idempotent: a replayed
    webhook or re-processed message never fires a second time.
    """

    __tablename__ = "keyword_triggers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    keyword_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False)
    flow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_SQL})", name="ck_keyword_triggers_status"),
        CheckConstraint(f"action IN ({_ACTION_SQL})", name="ck_keyword_triggers_action"),
        UniqueConstraint("tenant_id", "message_id", name="uq_keyword_triggers_message"),
        Index("ix_keyword_triggers_tenant_created", "tenant_id", "created_at"),
        Index("ix_keyword_triggers_keyword", "keyword_id", "created_at"),
    )
