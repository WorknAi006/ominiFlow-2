import json
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.core.config import settings
from app.integrations.meta.graph_client import is_meta_configured
from app.integrations.meta.webhooks import verify_signature, verify_subscription
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.whatsapp import WhatsAppConnectionCheck, WhatsAppConnectRequest
from app.services import whatsapp_service
from app.services.channel_service import (
    ChannelAlreadyExistsError,
    ChannelNotFoundError,
)
from app.services.credential_service import CredentialEncryptionError
from app.services.whatsapp_service import (
    InvalidConnectRequestError,
    NotWhatsAppChannelError,
    WhatsAppNotConfiguredError,
    WhatsAppUnavailableError,
    WhatsAppVerificationFailedError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])

MAX_WEBHOOK_BODY_BYTES = 1_000_000


ERROR_STATUS_CODES: dict[type[Exception], int] = {
    ChannelNotFoundError: status.HTTP_404_NOT_FOUND,
    ChannelAlreadyExistsError: status.HTTP_409_CONFLICT,
    NotWhatsAppChannelError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidConnectRequestError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    WhatsAppVerificationFailedError: status.HTTP_400_BAD_REQUEST,
    WhatsAppUnavailableError: status.HTTP_502_BAD_GATEWAY,
    WhatsAppNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


@contextmanager
def handle_service_errors() -> Iterator[None]:
    try:
        yield

    except tuple(ERROR_STATUS_CODES) as exc:
        raise HTTPException(
            status_code=ERROR_STATUS_CODES[type(exc)],
            detail=str(exc),
        )

    except CredentialEncryptionError:
        logger.error("Channel credential encryption is unavailable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is temporarily unavailable.",
        )

    except SQLAlchemyError:
        logger.exception("Database error during WhatsApp connect.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )


# =========================
# CONNECT
# =========================

@router.post(
    "/channels/{channel_id}/whatsapp/connect",
    response_model=ChannelConnectionResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def connect_whatsapp(
    channel_id: uuid.UUID,
    data: WhatsAppConnectRequest,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return whatsapp_service.connect_whatsapp_channel(
            db, tenant.id, channel_id, data,
        )


# =========================
# TEST CONNECTION (read-only health check)
# =========================

@router.post(
    "/channels/{channel_id}/whatsapp/test",
    response_model=WhatsAppConnectionCheck,
    dependencies=[Depends(require_permission("channel:update"))],
)
def test_whatsapp_connection(
    channel_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return whatsapp_service.check_whatsapp_channel(
            db, tenant.id, channel_id,
        )


# =========================
# WEBHOOKS (public, authenticated by Meta)
# =========================

@router.get(
    "/webhooks/whatsapp",
    response_class=PlainTextResponse,
)
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if not verify_subscription(
        settings.whatsapp_webhook_verify_token,
        hub_mode,
        hub_verify_token,
        hub_challenge,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification failed.",
        )

    return PlainTextResponse(hub_challenge)


async def _read_limited_body(request: Request) -> bytes:
    too_large = HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail="Payload too large.",
    )

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > MAX_WEBHOOK_BODY_BYTES:
            raise too_large

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BODY_BYTES:
            raise too_large

    return bytes(body)


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    db: DbSession,
):
    """
    Signature is verified against the raw body before anything is parsed.
    Always 200 for verified payloads (even if unroutable) so Meta does not
    retry; 500 on storage failure so Meta does retry (storage is
    idempotent).
    """

    if not is_meta_configured():
        logger.error("WhatsApp webhook received but Meta app is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook receiver is not configured.",
        )

    raw_body = await _read_limited_body(request)

    if not verify_signature(
        settings.meta_app_secret,
        raw_body,
        request.headers.get("x-hub-signature-256"),
    ):
        logger.warning("WhatsApp webhook rejected: invalid signature.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature.",
        )

    try:
        payload = json.loads(raw_body)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    try:
        await run_in_threadpool(whatsapp_service.handle_webhook, db, payload)
    except SQLAlchemyError as exc:
        # Type only: SQLAlchemy error text includes SQL parameters, i.e.
        # webhook payload content (customer data).
        logger.error("Database error while storing WhatsApp webhook: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed.",
        )

    return {"status": "ok"}
