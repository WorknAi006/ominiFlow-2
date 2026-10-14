import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class FlowStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"


class Flow(Base, UUIDMixin, TimestampMixin):
    """
    A visual chat-flow (chatbot) configuration. The builder stores its
    canvas as ``nodes`` and ``edges`` JSON; one flow can target one or more
    channels (WhatsApp / Instagram / Messenger / Omnichannel).
    """

    __tablename__ = "flows"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default=FlowStatus.DRAFT, server_default=FlowStatus.DRAFT.value, nullable=False)
    # Selected channels, e.g. ["whatsapp", "instagram"] or ["omnichannel"].
    channels: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    # React Flow canvas graph.
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('draft','active')", name="ck_flows_status"),
        Index("ix_flows_tenant_updated", "tenant_id", "updated_at"),
    )
