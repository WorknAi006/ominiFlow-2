import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TenantRoutingConfig(Base, UUIDMixin, TimestampMixin):
    """
    Tenant-level global routing: how inbound messages that match no keyword
    rule are handled. When ``fallback_action`` is ``flow`` and a
    ``fallback_flow_id`` is set, that flow runs for every unmatched message
    (the "master flow collection").
    """

    __tablename__ = "tenant_routing_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # "none" = do nothing; "flow" = run fallback_flow_id.
    fallback_action: Mapped[str] = mapped_column(
        String(20),
        default="none",
        server_default="none",
        nullable=False,
    )

    fallback_flow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flows.id", ondelete="SET NULL"),
        nullable=True,
    )
