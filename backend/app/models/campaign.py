import enum
import uuid
from typing import Optional, Any
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"

class Campaign(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "campaigns"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("channel_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("message_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # E.g., {"tags": ["uuid1", "uuid2"]}
    audience_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
