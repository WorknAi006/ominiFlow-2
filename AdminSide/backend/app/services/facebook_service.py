"""
Facebook Messenger service: channel connect flow, read-only health check,
and inbound webhook processing.

Tenant isolation:
- Connect/check are scoped to the authenticated tenant's channel.
- Webhook events are routed only through find_connected_channel()
  (verified Page id -> channel -> tenant). Nothing in the webhook payload
  is trusted to choose a tenant; a Page id resolves to at most one
  connected channel (unique partial index), so OnlineGo's webhook can
  never create data under AI Tourism.

Provider-specific parsing stays in FacebookProvider; this service only
routes, then hands normalized events to the channel-neutral
inbound_event_service, exactly like every other channel.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.base import (
    ProviderCredentials,
    ProviderNotConfiguredError,
    ProviderUnavailableError,
    ProviderVerificationError,
)
from app.integrations.facebook.provider import FacebookProvider
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Message,
)
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.facebook import FacebookConnectRequest
from app.services import channel_service, inbound_event_service, realtime_service
from app.services.channel_service import (
    ChannelAlreadyExistsError,
    ChannelNotFoundError,
)
from app.services.credential_service import get_credential_service

logger = logging.getLogger(__name__)

WEBHOOK_OBJECT = "page"


# =========================
# ERRORS
# =========================

class FacebookServiceError(Exception):
    """Base Facebook service error."""


class NotFacebookChannelError(FacebookServiceError):
    """Raised when the channel is not a Facebook channel."""


class FacebookVerificationFailedError(FacebookServiceError):
    """Raised when Meta verification of the Page fails."""


class FacebookUnavailableError(FacebookServiceError):
    """Raised when Meta cannot be reached."""


class FacebookNotConfiguredError(FacebookServiceError):
    """Raised when the Meta app is not configured."""


# =========================
# HELPERS
# =========================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _provider() -> FacebookProvider:
    provider = get_provider(ChannelType.FACEBOOK)
    assert isinstance(provider, FacebookProvider)
    return provider


def _load_channel(
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


def _ensure_page_available(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    page_id: str,
) -> None:
    """
    A Page may appear once per tenant, and may be connected to only one
    channel across all tenants. Which tenant holds it is never revealed.
    """
    conflict = (
        db.query(ChannelConnection.id)
        .filter(
            ChannelConnection.id != channel_id,
            ChannelConnection.channel_type == ChannelType.FACEBOOK,
            ChannelConnection.external_account_id == page_id,
            ChannelConnection.is_deleted.is_(False),
            (ChannelConnection.tenant_id == tenant_id)
            | (ChannelConnection.status == ChannelStatus.CONNECTED),
        )
        .first()
    )
    if conflict:
        raise ChannelAlreadyExistsError(
            "This Facebook Page is already connected to another channel."
        )


def _record_failure(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    message: str,
) -> None:
    """Record a failed connect attempt; a connected channel is untouched."""
    db.rollback()
    try:
        channel = _load_channel(db, tenant_id, channel_id, for_update=True)
        if channel.status != ChannelStatus.CONNECTED:
            channel.status = ChannelStatus.ERROR
            channel.last_error = message[:1000]
        db.commit()
    except (ChannelNotFoundError, SQLAlchemyError):
        db.rollback()
        logger.warning(
            "Could not record Facebook connect failure for channel %s.",
            channel_id,
        )


# =========================
# CONNECT
# =========================

def connect_facebook_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    data: FacebookConnectRequest,
) -> ChannelConnectionResponse:
    """
    Verify the Page access token with Meta, subscribe the Page's webhooks,
    then store encrypted credentials and mark the channel connected.
    """
    channel = _load_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.FACEBOOK:
        raise NotFacebookChannelError("Channel is not a Facebook channel.")

    provider = _provider()
    if not provider.is_configured():
        raise FacebookNotConfiguredError(
            "Facebook integration is not configured."
        )

    _ensure_page_available(db, tenant_id, channel_id, data.page_id)

    # End the read transaction: no locks held while waiting on Meta.
    db.rollback()

    try:
        credentials = ProviderCredentials(
            access_token=data.access_token.get_secret_value(),
        )
        info = provider.verify_page(credentials, data.page_id)
        provider.subscribe_webhooks(credentials, data.page_id)
    except ProviderNotConfiguredError:
        raise FacebookNotConfiguredError(
            "Facebook integration is not configured."
        ) from None
    except ProviderVerificationError as exc:
        message = str(exc)
        _record_failure(db, tenant_id, channel_id, message)
        logger.warning(
            "Facebook verification failed for channel %s: %s",
            channel_id, message,
        )
        raise FacebookVerificationFailedError(message) from None
    except ProviderUnavailableError as exc:
        message = str(exc)
        _record_failure(db, tenant_id, channel_id, message)
        raise FacebookUnavailableError(message) from None

    encrypted_token = get_credential_service().encrypt(credentials.access_token)

    channel = _load_channel(db, tenant_id, channel_id, for_update=True)
    channel.status = ChannelStatus.CONNECTED
    channel.external_account_id = info.external_account_id
    channel.external_business_id = info.external_business_id
    channel.access_token_encrypted = encrypted_token
    channel.refresh_token_encrypted = None
    channel.token_expires_at = None
    channel.provider_metadata = info.metadata
    channel.last_connected_at = _utcnow()
    channel.last_error = None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ChannelAlreadyExistsError(
            "This Facebook Page is already connected to another channel."
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise

    logger.info(
        "Facebook channel %s connected for tenant %s.", channel_id, tenant_id,
    )
    return channel_service.get_channel(db, tenant_id, channel_id)


# =========================
# CONNECTION HEALTH CHECK (read-only)
# =========================

@dataclass(frozen=True)
class ConnectionCheckResult:
    healthy: bool
    detail: str
    webhook_subscribed: bool | None = None
    page_name: str | None = None
    last_event_at: datetime | None = None


def check_facebook_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ConnectionCheckResult:
    """
    Verify a connected Facebook channel against Meta without mutating it.
    The stored token is decrypted in memory only; never returns secrets.
    """
    channel = _load_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.FACEBOOK:
        raise NotFacebookChannelError("Channel is not a Facebook channel.")

    provider = _provider()
    if not provider.is_configured():
        raise FacebookNotConfiguredError(
            "Facebook integration is not configured."
        )

    last_event_at = (
        db.query(func.max(Message.sent_at))
        .filter(
            Message.tenant_id == tenant_id,
            Message.channel_connection_id == channel.id,
        )
        .scalar()
    )

    if (
        channel.status != ChannelStatus.CONNECTED
        or not channel.external_account_id
        or not channel.access_token_encrypted
    ):
        return ConnectionCheckResult(
            healthy=False,
            detail="This Facebook channel is not connected.",
            last_event_at=last_event_at,
        )

    token = get_credential_service().decrypt(channel.access_token_encrypted)
    credentials = ProviderCredentials(access_token=token)

    try:
        info = provider.get_account_info(channel, credentials)
        subscribed = provider.is_webhook_subscribed(
            credentials, channel.external_account_id,
        )
    except ProviderVerificationError as exc:
        return ConnectionCheckResult(
            healthy=False,
            detail=str(exc),
            last_event_at=last_event_at,
        )
    except ProviderUnavailableError:
        return ConnectionCheckResult(
            healthy=False,
            detail="Could not reach Facebook. Please try again later.",
            last_event_at=last_event_at,
        )
    finally:
        del token

    detail = (
        "Facebook Page connection is healthy."
        if subscribed
        else "Connected, but the Page is not subscribed to our webhooks."
    )
    return ConnectionCheckResult(
        healthy=bool(subscribed),
        detail=detail,
        webhook_subscribed=subscribed,
        page_name=info.display_name,
        last_event_at=last_event_at,
    )


# =========================
# INBOUND WEBHOOK
# =========================

def handle_webhook(db: Session, payload: dict[str, Any]) -> None:
    """
    Process a verified Messenger webhook. The signature is verified by the
    caller before this runs. Each entry is routed by its Page id to a
    connected channel; unroutable entries are dropped. Messages are
    deduplicated by their Meta `mid` through the common inbound pipeline, so
    Meta retries never create duplicate messages.
    """
    if not isinstance(payload, dict) or payload.get("object") != WEBHOOK_OBJECT:
        return

    entries = payload.get("entry")
    if not isinstance(entries, list):
        return

    provider = _provider()
    realtime_events: list[dict[str, Any]] = []
    wrote = False

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        page_id = entry.get("id")
        messaging = entry.get("messaging")
        if not page_id or not isinstance(messaging, list):
            continue

        # Tenant is derived here, from the verified Page id — never from the
        # payload. A Page id maps to at most one connected channel.
        channel = channel_service.find_connected_channel(
            db, ChannelType.FACEBOOK, str(page_id),
        )
        if channel is None:
            continue

        for event in messaging:
            normalized = provider.normalize_inbound_message(channel, event)
            if normalized is None:
                continue
            realtime_events.extend(
                inbound_event_service.process_inbound_event(db, normalized)
            )
            wrote = True

    if wrote:
        db.commit()
        # Only after commit; best effort (never raises) — same rule as the
        # WhatsApp and Web Chat inbound paths.
        for event in realtime_events:
            realtime_service.publish_event(event)
