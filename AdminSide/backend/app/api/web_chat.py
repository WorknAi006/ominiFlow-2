import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.web_chat import (
    WebChatConfigResponse,
    WebChatInboundRequest,
    WebChatInboundResponse,
    WebChatMessagesResponse,
)
from app.services import web_chat_service
from app.services.web_chat_service import (
    NotWebChatChannelError,
    WebChatChannelNotFoundError,
    WebChatError,
)

logger = logging.getLogger(__name__)

# Public widget keys are "wc_" + url-safe token.
PUBLIC_KEY = Path(..., min_length=8, max_length=255, pattern=r"^[A-Za-z0-9._\-]+$")

router = APIRouter(tags=["Web Chat"])


@contextmanager
def _handle_errors() -> Iterator[None]:
    try:
        yield
    except WebChatChannelNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotWebChatChannelError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    except WebChatError:
        # Never expose internal detail to a public caller.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message could not be processed.")
    except SQLAlchemyError:
        logger.error("Database error in Web Chat endpoint.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service temporarily unavailable.")


# =========================
# DASHBOARD (authenticated)
# =========================

@router.post(
    "/channels/{channel_id}/web-chat/connect",
    response_model=ChannelConnectionResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def connect_web_chat(channel_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with _handle_errors():
        return web_chat_service.connect_web_chat_channel(db, tenant.id, channel_id)


# =========================
# PUBLIC WIDGET (no auth; tenant/channel derived from the public key)
# =========================

@router.get("/web-chat/{public_key}/config", response_model=WebChatConfigResponse)
def web_chat_config(db: DbSession, public_key: str = PUBLIC_KEY):
    with _handle_errors():
        return web_chat_service.get_config(db, public_key)


@router.post(
    "/web-chat/{public_key}/messages",
    response_model=WebChatInboundResponse,
    status_code=status.HTTP_201_CREATED,
)
def web_chat_inbound(data: WebChatInboundRequest, db: DbSession, public_key: str = PUBLIC_KEY):
    with _handle_errors():
        return web_chat_service.process_inbound(db, public_key, data)


@router.get("/web-chat/{public_key}/messages", response_model=WebChatMessagesResponse)
def web_chat_messages(
    db: DbSession,
    public_key: str = PUBLIC_KEY,
    visitor_id: str = Query(..., min_length=1, max_length=200),
    after: datetime | None = Query(default=None),
):
    with _handle_errors():
        return web_chat_service.list_visitor_messages(db, public_key, visitor_id, after)
