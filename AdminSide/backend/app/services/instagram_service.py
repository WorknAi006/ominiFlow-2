"""
Instagram service: channel connect flow, read-only health check, and
inbound webhook processing.

Tenant isolation:
- Connect/check are scoped to the authenticated tenant's channel.
- Webhook events are routed only through find_connected_channel()
  (verified Instagram account id -> channel -> tenant). Nothing in the
  webhook payload is trusted to choose a tenant; an Instagram account id
  resolves to at most one connected channel (unique partial index), so
  OnlineGo's webhook can never create data under AI Tourism.

Provider-specific parsing stays in InstagramProvider; this service only
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
from app.integrations.instagram.provider import InstagramProvider
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Message,
)
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.instagram import InstagramConnectRequest
from app.services import channel_service, inbound_event_service, realtime_service
from app.services.channel_service import (
    ChannelAlreadyExistsError,
    ChannelNotFoundError,
)
from app.services.credential_service import get_credential_service

logger = logging.getLogger(__name__)

WEBHOOK_OBJECT = "instagram"


# =========================
# ERRORS
# =========================

class InstagramServiceError(Exception):
    """Base Instagram service error."""


class NotInstagramChannelError(InstagramServiceError):
    """Raised when the channel is not an Instagram channel."""


class InstagramVerificationFailedError(InstagramServiceError):
    """Raised when Meta verification of the account fails."""


class InstagramUnavailableError(InstagramServiceError):
    """Raised when Meta cannot be reached."""


class InstagramNotConfiguredError(InstagramServiceError):
    """Raised when the Meta app is not configured."""


# =========================
# HELPERS
# =========================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _provider() -> InstagramProvider:
    provider = get_provider(ChannelType.INSTAGRAM)
    assert isinstance(provider, InstagramProvider)
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


def _ensure_account_available(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    instagram_id: str,
) -> None:
    """
    An Instagram account may appear once per tenant, and may be connected to
    only one channel across all tenants. Which tenant holds it is never
    revealed.
    """
    conflict = (
        db.query(ChannelConnection.id)
        .filter(
            ChannelConnection.id != channel_id,
            ChannelConnection.channel_type == ChannelType.INSTAGRAM,
            ChannelConnection.external_account_id == instagram_id,
            ChannelConnection.is_deleted.is_(False),
            (ChannelConnection.tenant_id == tenant_id)
            | (ChannelConnection.status == ChannelStatus.CONNECTED),
        )
        .first()
    )
    if conflict:
        raise ChannelAlreadyExistsError(
            "This Instagram account is already connected to another channel."
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
            "Could not record Instagram connect failure for channel %s.",
            channel_id,
        )


# =========================
# CONNECT
# =========================

def connect_instagram_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    data: InstagramConnectRequest,
) -> ChannelConnectionResponse:
    """
    Verify the Page access token and the Page->Instagram link with Meta,
    subscribe the Page's webhooks, then store encrypted credentials and mark
    the channel connected.
    """
    channel = _load_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.INSTAGRAM:
        raise NotInstagramChannelError("Channel is not an Instagram channel.")

    provider = _provider()
    if not provider.is_configured():
        raise InstagramNotConfiguredError(
            "Instagram integration is not configured."
        )

    _ensure_account_available(db, tenant_id, channel_id, data.instagram_id)

    # End the read transaction: no locks held while waiting on Meta.
    db.rollback()

    try:
        credentials = ProviderCredentials(
            access_token=data.access_token.get_secret_value(),
        )
        info = provider.verify_account(credentials, data.instagram_id, data.page_id)
        provider.subscribe_webhooks(credentials, data.page_id)
    except ProviderNotConfiguredError:
        raise InstagramNotConfiguredError(
            "Instagram integration is not configured."
        ) from None
    except ProviderVerificationError as exc:
        message = str(exc)
        _record_failure(db, tenant_id, channel_id, message)
        logger.warning(
            "Instagram verification failed for channel %s: %s",
            channel_id, message,
        )
        raise InstagramVerificationFailedError(message) from None
    except ProviderUnavailableError as exc:
        message = str(exc)
        _record_failure(db, tenant_id, channel_id, message)
        raise InstagramUnavailableError(message) from None

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
            "This Instagram account is already connected to another channel."
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise

    logger.info(
        "Instagram channel %s connected for tenant %s.", channel_id, tenant_id,
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
    username: str | None = None
    account_id: str | None = None
    last_event_at: datetime | None = None


def check_instagram_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ConnectionCheckResult:
    """
    Verify a connected Instagram channel against Meta without mutating it.
    The stored token is decrypted in memory only; never returns secrets.
    """
    channel = _load_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.INSTAGRAM:
        raise NotInstagramChannelError("Channel is not an Instagram channel.")

    provider = _provider()
    if not provider.is_configured():
        raise InstagramNotConfiguredError(
            "Instagram integration is not configured."
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
            detail="This Instagram channel is not connected.",
            last_event_at=last_event_at,
        )

    token = get_credential_service().decrypt(channel.access_token_encrypted)
    credentials = ProviderCredentials(access_token=token)

    try:
        info = provider.get_account_info(channel, credentials)
        subscribed = (
            provider.is_webhook_subscribed(credentials, channel.external_business_id)
            if channel.external_business_id else None
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
            detail="Could not reach Instagram. Please try again later.",
            last_event_at=last_event_at,
        )
    finally:
        del token

    healthy = subscribed is not False
    detail = (
        "Instagram connection is healthy."
        if healthy
        else "Connected, but the account is not subscribed to our webhooks."
    )
    return ConnectionCheckResult(
        healthy=healthy,
        detail=detail,
        webhook_subscribed=subscribed,
        username=info.display_name,
        account_id=info.external_account_id,
        last_event_at=last_event_at,
    )


# =========================
# INBOUND WEBHOOK
# =========================

def handle_webhook(db: Session, payload: dict[str, Any]) -> None:
    """
    Process a verified Instagram webhook. The signature is verified by the
    caller before this runs. Each entry is routed by its Instagram account id
    to a connected channel; unroutable entries are dropped. Messages are
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
        account_id = entry.get("id")
        messaging = entry.get("messaging")
        if not account_id or not isinstance(messaging, list):
            continue

        # Tenant is derived here, from the verified Instagram account id —
        # never from the payload. An account id maps to at most one connected
        # channel.
        channel = channel_service.find_connected_channel(
            db, ChannelType.INSTAGRAM, str(account_id),
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
        # WhatsApp, Facebook and Web Chat inbound paths.
        for event in realtime_events:
            realtime_service.publish_event(event)
