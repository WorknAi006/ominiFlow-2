import uuid
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

class Keyword(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "keywords"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    keyword_text: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(String(50), nullable=False, default="exact", server_default="exact")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    # The visual chat-flow this keyword triggers on a match (tenant-scoped).
    flow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="SET NULL"), nullable=True)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("match_type IN ('exact', 'contains', 'starts_with', 'ends_with')", name="ck_keywords_match_type"),
        Index("ix_keywords_tenant_id", "tenant_id"),
        UniqueConstraint("tenant_id", "keyword_text", "match_type", name="uq_keywords_tenant_text_match"),
    )
