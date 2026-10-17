import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import (
    CurrentTenant,
    CurrentUser,
    DbSession,
    require_permission,
)
from app.models import ChannelStatus, ChannelType
from app.schemas.channel import (
    ChannelConnectionCreate,
    ChannelConnectionListResponse,
    ChannelConnectionResponse,
    ChannelConnectionUpdate,
)
from app.services import channel_service
from app.services.channel_service import (
    ChannelAlreadyExistsError,
    ChannelNotFoundError,
    ChannelServiceError,
)
from app.services.credential_service import CredentialEncryptionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Channels"])


ERROR_STATUS_CODES: dict[type[ChannelServiceError], int] = {
    ChannelNotFoundError: status.HTTP_404_NOT_FOUND,
    ChannelAlreadyExistsError: status.HTTP_409_CONFLICT,
}


@contextmanager
def handle_service_errors() -> Iterator[None]:
    try:
        yield

    except ChannelServiceError as exc:
        raise HTTPException(
            status_code=ERROR_STATUS_CODES.get(
                type(exc),
                status.HTTP_400_BAD_REQUEST,
            ),
            detail=str(exc),
        )

    except CredentialEncryptionError:
        # Misconfigured key: log without any credential or key material.
        logger.error("Channel credential encryption is unavailable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is temporarily unavailable.",
        )

    except SQLAlchemyError:
        logger.exception("Database error during channel management.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )


@router.get(
    "",
    response_model=ChannelConnectionListResponse,
    dependencies=[Depends(require_permission("channel:read"))],
)
def list_channels(
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    channel_type: ChannelType | None = Query(default=None),
    channel_status: ChannelStatus | None = Query(default=None, alias="status"),
):
    search = search.strip() if search else None

    with handle_service_errors():
        return channel_service.list_channels(
            db,
            tenant.id,
            page,
            page_size,
            search or None,
            channel_type,
            channel_status,
        )


@router.post(
    "",
    response_model=ChannelConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("channel:create"))],
)
def create_channel(
    data: ChannelConnectionCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return channel_service.create_channel(db, tenant.id, user, data)


@router.get(
    "/{channel_id}",
    response_model=ChannelConnectionResponse,
    dependencies=[Depends(require_permission("channel:read"))],
)
def get_channel(
    channel_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return channel_service.get_channel(db, tenant.id, channel_id)


@router.patch(
    "/{channel_id}",
    response_model=ChannelConnectionResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def update_channel(
    channel_id: uuid.UUID,
    data: ChannelConnectionUpdate,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return channel_service.update_channel(db, tenant.id, channel_id, data)


@router.post(
    "/{channel_id}/disconnect",
    response_model=ChannelConnectionResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def disconnect_channel(
    channel_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return channel_service.disconnect_channel(db, tenant.id, channel_id)


@router.delete(
    "/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("channel:delete"))],
)
def delete_channel(
    channel_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        channel_service.delete_channel(db, tenant.id, channel_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
