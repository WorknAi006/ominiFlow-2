import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.message import MessageResponse
from app.services import media_service, message_service
from app.services.media_service import MediaNotFoundError, MediaNotReadyError
from app.services.message_service import MessageNotFoundError

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("message:read"))],
)
def get_message(message_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors({MessageNotFoundError: status.HTTP_404_NOT_FOUND}):
        return message_service.get_message(db, tenant.id, message_id)


@router.get(
    "/{message_id}/media",
    response_class=StreamingResponse,
    dependencies=[Depends(require_permission("message:read"))],
)
def get_message_media(message_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    """
    Stream downloaded media through Omniflow (tenant-scoped). Provider URLs
    and credentials are never exposed.
    """

    with service_errors({
        MediaNotFoundError: status.HTTP_404_NOT_FOUND,
        MediaNotReadyError: status.HTTP_409_CONFLICT,
    }):
        media, chunks = media_service.open_media(db, tenant.id, message_id)

    disposition = "attachment" if media.media_kind == "document" else "inline"
    filename = media.original_filename or f"{media.media_kind}"

    return StreamingResponse(
        chunks,
        media_type=media.mime_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Content-Length": str(media.file_size),
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, no-store",
        },
    )
