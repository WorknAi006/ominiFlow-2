import uuid
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

class TenantAiConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenant_ai_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        default="platform",
        server_default="platform",
        nullable=False,
    )
    
    model: Mapped[str] = mapped_column(
        String(100),
        default="gpt-4o",
        server_default="gpt-4o",
        nullable=False,
    )

    api_key_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    is_verified: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )
