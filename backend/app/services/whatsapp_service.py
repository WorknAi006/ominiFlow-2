"""
WhatsApp Cloud API service: channel connect flow and inbound webhook
event storage.

Tenant isolation:
- Connect is scoped to the authenticated tenant's channel.
- Webhook events are routed only through find_connected_channel()
  (provider phone_number_id -> channel -> tenant). Nothing in the webhook
  payload is trusted to choose a tenant.
"""
import hashlib
import json
import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.integrations.base import (
    ProviderCredentials,
    ProviderNotConfiguredError,
    ProviderUnavailableError,
    ProviderVerificationError,
)
from app.integrations.registry import get_provider
from app.integrations.whatsapp.provider import WhatsAppProvider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    WhatsAppEvent,
    WhatsAppEventType,
)
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.whatsapp import WhatsAppConnectRequest
from app.services import channel_service
from app.services.channel_service import (
    ChannelAlreadyExistsError,
    ChannelNotFoundError,
)
from app.core.json_sanitize import strip_nul
from app.services.credential_service import get_credential_service

logger = logging.getLogger(__name__)

WEBHOOK_OBJECT = "whatsapp_business_account"
MAX_KEY_LENGTH = 255


# =========================
# ERRORS
# =========================

class WhatsAppServiceError(Exception):
    """Base WhatsApp service error."""


class NotWhatsAppChannelError(WhatsAppServiceError):
    """Raised when the channel is not a WhatsApp channel."""


class InvalidConnectRequestError(WhatsAppServiceError):
    """Raised when the connect request is incomplete or ambiguous."""


class WhatsAppVerificationFailedError(WhatsAppServiceError):
    """Raised when Meta verification of the account fails."""


class WhatsAppUnavailableError(WhatsAppServiceError):
    """Raised when Meta cannot be reached."""


class WhatsAppNotConfiguredError(WhatsAppServiceError):
    """Raised when the Meta app is not configured."""


# =========================
# HELPERS
# =========================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _provider() -> WhatsAppProvider:
    provider = get_provider(ChannelType.WHATSAPP)
    assert isinstance(provider, WhatsAppProvider)
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


def _ensure_phone_available(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    phone_number_id: str,
) -> None:
    """
    A phone number may appear once per tenant, and may be connected to
    only one channel across all tenants. Which tenant holds it is never
    revealed.
    """

    conflict = (
        db.query(ChannelConnection.id)
        .filter(
            ChannelConnection.id != channel_id,
            ChannelConnection.channel_type == ChannelType.WHATSAPP,
            ChannelConnection.external_account_id == phone_number_id,
            ChannelConnection.is_deleted.is_(False),
            (ChannelConnection.tenant_id == tenant_id)
            | (ChannelConnection.status == ChannelStatus.CONNECTED),
        )
        .first()
    )

    if conflict:
        raise ChannelAlreadyExistsError(
            "This WhatsApp number is already connected to another channel."
        )


def _record_failure(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    message: str,
) -> None:
    """
    Record a failed connect attempt. A channel that is already connected
    keeps working: its status and credentials are left untouched.
    """

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
            "Could not record WhatsApp connect failure for channel %s.",
            channel_id,
        )


# =========================
# CONNECT
# =========================

def connect_whatsapp_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    data: WhatsAppConnectRequest,
) -> ChannelConnectionResponse:
    """
    Verify the WhatsApp account with Meta, subscribe webhooks, then store
    encrypted credentials and mark the channel connected.
    """

    if (data.access_token is None) == (data.code is None):
        raise InvalidConnectRequestError(
            "Provide exactly one of access_token or code."
        )

    channel = _load_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.WHATSAPP:
        raise NotWhatsAppChannelError("Channel is not a WhatsApp channel.")

    provider = _provider()

    if not provider.is_configured():
        raise WhatsAppNotConfiguredError(
            "WhatsApp integration is not configured."
        )

    _ensure_phone_available(db, tenant_id, channel_id, data.phone_number_id)

    # End the read transaction: no locks or open transaction are held
    # while waiting on Meta.
    db.rollback()

    try:
        if data.code is not None:
            credentials = provider.exchange_code(data.code.get_secret_value())
        else:
            credentials = ProviderCredentials(
                access_token=data.access_token.get_secret_value(),
            )

        info, credentials = provider.verify_account(
            credentials, data.phone_number_id, data.waba_id,
        )
        provider.subscribe_webhooks(credentials, data.waba_id)

    except ProviderNotConfiguredError:
        raise WhatsAppNotConfiguredError(
            "WhatsApp integration is not configured."
        ) from None

    except ProviderVerificationError as exc:
        message = str(exc)
        _record_failure(db, tenant_id, channel_id, message)
        logger.warning(
            "WhatsApp verification failed for channel %s: %s",
            channel_id, message,
        )
        raise WhatsAppVerificationFailedError(message) from None

    except ProviderUnavailableError as exc:
        message = str(exc)
        _record_failure(db, tenant_id, channel_id, message)
        raise WhatsAppUnavailableError(message) from None

    encrypted_token = get_credential_service().encrypt(credentials.access_token)

    channel = _load_channel(db, tenant_id, channel_id, for_update=True)

    channel.status = ChannelStatus.CONNECTED
    channel.external_account_id = info.external_account_id
    channel.external_business_id = info.external_business_id
    channel.access_token_encrypted = encrypted_token
    channel.refresh_token_encrypted = None
    channel.token_expires_at = credentials.expires_at
    channel.provider_metadata = info.metadata
    channel.last_connected_at = _utcnow()
    channel.last_error = None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ChannelAlreadyExistsError(
            "This WhatsApp number is already connected to another channel."
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise

    logger.info(
        "WhatsApp channel %s connected for tenant %s.", channel_id, tenant_id,
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
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    last_event_at: datetime | None = None


def check_whatsapp_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ConnectionCheckResult:
    """
    Verify a connected WhatsApp channel against Meta without mutating it:
    the stored token is decrypted in memory only, the account is read back,
    and the WABA's webhook subscription is checked. Never returns secrets.
    """

    channel = _load_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.WHATSAPP:
        raise NotWhatsAppChannelError("Channel is not a WhatsApp channel.")

    provider = _provider()

    if not provider.is_configured():
        raise WhatsAppNotConfiguredError(
            "WhatsApp integration is not configured."
        )

    last_event_at = (
        db.query(func.max(WhatsAppEvent.occurred_at))
        .filter(WhatsAppEvent.channel_id == channel.id)
        .scalar()
    )

    if (
        channel.status != ChannelStatus.CONNECTED
        or channel.access_token_encrypted is None
    ):
        return ConnectionCheckResult(
            healthy=False,
            detail="Channel is not connected. Connect it to send and receive messages.",
            last_event_at=last_event_at,
        )

    waba_id = channel.external_business_id
    token = get_credential_service().decrypt(channel.access_token_encrypted)
    credentials = ProviderCredentials(access_token=token)

    # No DB transaction is held while waiting on Meta.
    db.rollback()
    channel = _load_channel(db, tenant_id, channel_id)

    try:
        info = provider.get_account_info(channel, credentials)
        webhook_subscribed = (
            provider.is_webhook_subscribed(credentials, waba_id)
            if waba_id else None
        )
    except ProviderVerificationError as exc:
        return ConnectionCheckResult(
            healthy=False,
            detail=str(exc)[:1000],
            last_event_at=last_event_at,
        )
    except ProviderUnavailableError as exc:
        raise WhatsAppUnavailableError(str(exc)) from None

    return ConnectionCheckResult(
        healthy=True,
        detail="WhatsApp connection is healthy.",
        webhook_subscribed=webhook_subscribed,
        display_phone_number=info.metadata.get("display_phone_number"),
        verified_name=info.metadata.get("verified_name"),
        quality_rating=info.metadata.get("quality_rating"),
        last_event_at=last_event_at,
    )


# =========================
# WEBHOOK EVENTS
# =========================

@dataclass
class WebhookResult:
    stored: int = 0
    duplicates: int = 0
    unrouted: int = 0
    ignored: int = 0


@dataclass(frozen=True)
class _ParsedEvent:
    event_type: WhatsAppEventType
    dedupe_key: str
    wa_message_id: str | None
    wa_id: str | None
    occurred_at: datetime | None
    payload: dict[str, Any]


def _dicts(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _text(value: Any, max_length: int) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value)
    return text[:max_length] if text else None


def _timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _key(raw: str) -> str:
    if len(raw) <= MAX_KEY_LENGTH:
        return raw
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_events(value: dict[str, Any]) -> Iterator[_ParsedEvent]:
    metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}

    contacts = {
        str(contact.get("wa_id")): contact
        for contact in _dicts(value.get("contacts"))
        if contact.get("wa_id")
    }

    for message in _dicts(value.get("messages")):
        message_id = _text(message.get("id"), MAX_KEY_LENGTH)
        if not message_id:
            continue
        sender = _text(message.get("from"), 64)
        yield _ParsedEvent(
            event_type=WhatsAppEventType.MESSAGE,
            dedupe_key=_key(f"message:{message_id}"),
            wa_message_id=message_id,
            wa_id=sender,
            occurred_at=_timestamp(message.get("timestamp")),
            payload={
                "message": message,
                "contact": contacts.get(sender) if sender else None,
                "metadata": metadata,
            },
        )

    for status in _dicts(value.get("statuses")):
        message_id = _text(status.get("id"), MAX_KEY_LENGTH)
        state = _text(status.get("status"), 50)
        if not message_id or not state:
            continue
        yield _ParsedEvent(
            event_type=WhatsAppEventType.STATUS,
            dedupe_key=_key(f"status:{message_id}:{state}"),
            wa_message_id=message_id,
            wa_id=_text(status.get("recipient_id"), 64),
            occurred_at=_timestamp(status.get("timestamp")),
            payload={"status": status, "metadata": metadata},
        )

    for error in _dicts(value.get("errors")):
        digest = hashlib.sha256(
            json.dumps(error, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        yield _ParsedEvent(
            event_type=WhatsAppEventType.ERROR,
            dedupe_key=f"error:{digest}",
            wa_message_id=None,
            wa_id=None,
            occurred_at=None,
            payload={"error": error, "metadata": metadata},
        )


def _store_event(
    db: Session,
    channel: ChannelConnection,
    event: _ParsedEvent,
) -> bool:
    """Insert once per (channel, dedupe_key). Returns False on duplicate."""

    statement = (
        insert(WhatsAppEvent)
        .values(
            id=uuid.uuid4(),
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            event_type=event.event_type,
            dedupe_key=event.dedupe_key,
            wa_message_id=event.wa_message_id,
            wa_id=event.wa_id,
            occurred_at=event.occurred_at,
            payload=event.payload,
        )
        .on_conflict_do_nothing(
            constraint="uq_whatsapp_events_channel_dedupe_key",
        )
        # RETURNING (not rowcount, which is unreliable for ORM-enabled
        # inserts) tells a new row from a skipped duplicate.
        .returning(WhatsAppEvent.id)
    )

    return db.execute(statement).scalar_one_or_none() is not None


def handle_webhook(db: Session, payload: Any) -> WebhookResult:
    """
    Store events from a signature-verified webhook payload.

    Each change is routed by its metadata.phone_number_id; the entry's
    WABA id must also match the routed channel. Unroutable changes are
    dropped. The payload is never logged (it contains customer data).
    """

    # PostgreSQL cannot store NUL in text/JSONB; remove it before anything
    # is extracted or written. (The signature was already verified against
    # the original request bytes by the caller.)
    payload, removed = strip_nul(payload)
    if removed:
        logger.warning("Removed %d NUL character(s) from a WhatsApp webhook payload.", removed)

    result = WebhookResult()

    if not isinstance(payload, dict) or payload.get("object") != WEBHOOK_OBJECT:
        result.ignored += 1
        return result

    for entry in _dicts(payload.get("entry")):
        waba_id = _text(entry.get("id"), 64)

        for change in _dicts(entry.get("changes")):
            value = change.get("value")

            if change.get("field") != "messages" or not isinstance(value, dict):
                result.ignored += 1
                continue

            metadata = value.get("metadata")
            phone_number_id = (
                _text(metadata.get("phone_number_id"), 64)
                if isinstance(metadata, dict) else None
            )

            if not phone_number_id or not waba_id:
                result.ignored += 1
                continue

            channel = channel_service.find_connected_channel(
                db, ChannelType.WHATSAPP, phone_number_id,
            )

            if channel is None or channel.external_business_id != waba_id:
                result.unrouted += 1
                logger.info(
                    "WhatsApp webhook change for unrouted phone_number_id %s dropped.",
                    phone_number_id,
                )
                continue

            for event in _extract_events(value):
                if _store_event(db, channel, event):
                    result.stored += 1
                else:
                    result.duplicates += 1

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    logger.info(
        "WhatsApp webhook processed: stored=%d duplicates=%d unrouted=%d ignored=%d",
        result.stored, result.duplicates, result.unrouted, result.ignored,
    )

    return result
