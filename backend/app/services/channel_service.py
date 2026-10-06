import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Tenant,
    User,
)
from app.schemas.channel import (
    ChannelConnectionCreate,
    ChannelConnectionListResponse,
    ChannelConnectionResponse,
    ChannelConnectionUpdate,
)
from app.services.credential_service import get_credential_service

logger = logging.getLogger(__name__)


# =========================
# ERRORS
# =========================

class ChannelServiceError(Exception):
    """Base channel service error."""


class ChannelNotFoundError(ChannelServiceError):
    """Raised when the channel does not exist in the current tenant."""


class ChannelAlreadyExistsError(ChannelServiceError):
    """Raised when the external account is already connected here."""


# =========================
# HELPERS
# =========================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _to_response(channel: ChannelConnection) -> ChannelConnectionResponse:
    return ChannelConnectionResponse(
        id=channel.id,
        name=channel.name,
        channel_type=channel.channel_type,
        status=channel.status,
        external_account_id=channel.external_account_id,
        external_business_id=channel.external_business_id,
        has_credentials=channel.access_token_encrypted is not None,
        token_expires_at=channel.token_expires_at,
        is_active=channel.is_active,
        last_connected_at=channel.last_connected_at,
        last_error=channel.last_error,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ChannelAlreadyExistsError(
            "A channel for this external account already exists."
        )
    except SQLAlchemyError:
        db.rollback()
        raise


def _get_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    for_update: bool = False,
) -> ChannelConnection:
    query = db.query(ChannelConnection).filter(
        ChannelConnection.id == channel_id,
        ChannelConnection.tenant_id == tenant_id,
        ChannelConnection.is_deleted.is_(False),
    )

    if for_update:
        query = query.with_for_update()

    channel = query.first()

    if channel is None:
        raise ChannelNotFoundError("Channel not found.")

    return channel


def _clear_credentials(channel: ChannelConnection) -> None:
    channel.access_token_encrypted = None
    channel.refresh_token_encrypted = None
    channel.token_expires_at = None


# =========================
# CHANNELS
# =========================

def list_channels(
    db: Session,
    tenant_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    channel_type: ChannelType | None = None,
    status: ChannelStatus | None = None,
) -> ChannelConnectionListResponse:

    query = db.query(ChannelConnection).filter(
        ChannelConnection.tenant_id == tenant_id,
        ChannelConnection.is_deleted.is_(False),
    )

    if channel_type is not None:
        query = query.filter(ChannelConnection.channel_type == channel_type)

    if status is not None:
        query = query.filter(ChannelConnection.status == status)

    if search:
        pattern = f"%{_escape_like(search)}%"
        query = query.filter(
            or_(
                ChannelConnection.name.ilike(pattern, escape="\\"),
                ChannelConnection.external_account_id.ilike(
                    pattern, escape="\\",
                ),
            )
        )

    total = query.count()

    channels = (
        query.order_by(
            ChannelConnection.created_at.asc(),
            ChannelConnection.id.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ChannelConnectionListResponse(
        items=[_to_response(channel) for channel in channels],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ChannelConnectionResponse:

    return _to_response(_get_channel(db, tenant_id, channel_id))


def create_channel(
    db: Session,
    tenant_id: uuid.UUID,
    actor: User,
    data: ChannelConnectionCreate,
) -> ChannelConnectionResponse:
    """
    Create a pending connection. Provider authorization (OAuth) will be
    completed by provider-specific modules; nothing here marks a channel
    as connected.
    """

    if data.external_account_id is not None:
        duplicate = (
            db.query(ChannelConnection.id)
            .filter(
                ChannelConnection.tenant_id == tenant_id,
                ChannelConnection.channel_type == data.channel_type,
                ChannelConnection.external_account_id
                == data.external_account_id,
                ChannelConnection.is_deleted.is_(False),
            )
            .first()
        )

        if duplicate:
            raise ChannelAlreadyExistsError(
                "A channel for this external account already exists."
            )

    channel = ChannelConnection(
        tenant_id=tenant_id,
        channel_type=data.channel_type,
        name=data.name,
        status=ChannelStatus.PENDING,
        external_account_id=data.external_account_id,
        external_business_id=data.external_business_id,
        is_active=True,
        created_by=actor.id,
    )

    if data.access_token is not None:
        credentials = get_credential_service()

        channel.access_token_encrypted = credentials.encrypt(
            data.access_token.get_secret_value()
        )

        if data.refresh_token is not None:
            channel.refresh_token_encrypted = credentials.encrypt(
                data.refresh_token.get_secret_value()
            )

        channel.token_expires_at = data.token_expires_at

    db.add(channel)
    _commit(db)
    db.refresh(channel)

    logger.info(
        "Channel %s (%s) created for tenant %s.",
        channel.id,
        channel.channel_type,
        tenant_id,
    )

    return _to_response(channel)


def update_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    data: ChannelConnectionUpdate,
) -> ChannelConnectionResponse:

    channel = _get_channel(db, tenant_id, channel_id, for_update=True)

    changes = data.model_dump(
        include={"name", "is_active"},
        exclude_unset=True,
    )

    for field, value in changes.items():
        setattr(channel, field, value)

    _commit(db)
    db.refresh(channel)

    return _to_response(channel)


def disconnect_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ChannelConnectionResponse:
    """
    Disconnect locally: stored credentials are wiped and the channel stops
    being routable. The record and its history are kept.

    TODO: when provider modules exist, call provider.disconnect() first to
    revoke access / unsubscribe webhooks at the provider.
    """

    channel = _get_channel(db, tenant_id, channel_id, for_update=True)

    channel.status = ChannelStatus.DISCONNECTED
    _clear_credentials(channel)

    _commit(db)
    db.refresh(channel)

    logger.info(
        "Channel %s disconnected for tenant %s.", channel.id, tenant_id,
    )

    return _to_response(channel)


def delete_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> None:
    """
    Soft delete. Future conversations/messages keep referencing the row,
    so it is never physically removed. Credentials are wiped.
    """

    channel = _get_channel(db, tenant_id, channel_id, for_update=True)

    channel.is_deleted = True
    channel.deleted_at = _utcnow()
    channel.is_active = False
    channel.status = ChannelStatus.DISCONNECTED
    _clear_credentials(channel)

    _commit(db)

    logger.info("Channel %s deleted for tenant %s.", channel.id, tenant_id)


# =========================
# WEBHOOK ROUTING (foundation)
# =========================

def find_connected_channel(
    db: Session,
    channel_type: ChannelType,
    external_account_id: str,
) -> ChannelConnection | None:
    """
    Resolve the tenant's channel for an incoming provider webhook.

    Intentionally not tenant-scoped: the tenant is derived from the
    verified provider account, never from caller input. Only connected,
    active, non-deleted channels are routable; a unique partial index
    guarantees at most one match.
    """

    return (
        db.query(ChannelConnection)
        .join(Tenant, Tenant.id == ChannelConnection.tenant_id)
        .filter(
            ChannelConnection.channel_type == channel_type,
            ChannelConnection.external_account_id == external_account_id,
            ChannelConnection.status == ChannelStatus.CONNECTED,
            ChannelConnection.is_active.is_(True),
            ChannelConnection.is_deleted.is_(False),
            Tenant.is_active.is_(True),
            Tenant.is_deleted.is_(False),
        )
        .first()
    )
