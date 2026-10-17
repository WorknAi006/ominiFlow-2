"""
Server-side WhatsApp media download and storage.

Flow (per message_media row):
1. Claim the PENDING row (FOR UPDATE SKIP LOCKED + short lease), count the
   attempt, commit. No transaction is held during network I/O.
2. Meta media endpoint -> short-lived URL + mime/size/sha256.
3. Validate MIME (allowlist per media kind) and declared size.
4. Authenticated download (token only to Meta media hosts, size-capped,
   timeout, no redirects).
5. Verify Content-Type and SHA-256, store under an application-generated
   tenant-prefixed key, mark DOWNLOADED and point message.media_url at the
   authenticated Omniflow endpoint (never a provider URL).

Permanent problems (invalid type, too large, integrity, rejected by Meta)
fail immediately; transient ones (timeouts, outages, storage errors) are
retried up to settings.media_max_download_attempts.
"""
import hashlib
import logging
import re
import uuid
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.base import (
    ProviderCredentials,
    ProviderNotConfiguredError,
    ProviderPayloadTooLargeError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.integrations.registry import get_provider
from app.integrations.whatsapp.provider import WhatsAppProvider
from app.models import (
    ChannelConnection,
    ChannelType,
    MediaStatus,
    Message,
    MessageMedia,
)
from app.services.credential_service import CredentialEncryptionError, get_credential_service
from app.storage import StorageError, get_storage

logger = logging.getLogger(__name__)

MB = 1024 * 1024
LEASE = timedelta(minutes=5)

# WhatsApp Cloud API supported media (allowlist) and size limits.
MEDIA_RULES: dict[str, tuple[int, dict[str, str]]] = {
    "image": (5 * MB, {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }),
    "video": (16 * MB, {
        "video/mp4": ".mp4",
        "video/3gpp": ".3gp",
    }),
    "audio": (16 * MB, {
        "audio/aac": ".aac",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/amr": ".amr",
        "audio/ogg": ".ogg",
    }),
    "document": (100 * MB, {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    }),
}

GENERIC_CONTENT_TYPES = {"application/octet-stream", "binary/octet-stream"}


class MediaServiceError(Exception):
    """Base media error. Messages are safe to return/store."""


class MediaNotFoundError(MediaServiceError):
    """No media for this message in the current tenant."""


class MediaNotReadyError(MediaServiceError):
    """Media exists but is not downloaded (pending or failed)."""


class _PermanentFailure(Exception):
    pass


class _TransientFailure(Exception):
    pass


class MediaOutcome:
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


# =========================
# HELPERS
# =========================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_mime(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.split(";", 1)[0].strip().lower()


def sanitize_filename(name: object, extension: str = "") -> str | None:
    """
    Display-only filename: last path component, safe characters, bounded
    length, and (when known) the extension of the verified MIME type.
    """
    if not isinstance(name, str) or not name.strip():
        return None

    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    stem = base.rsplit(".", 1)[0] if "." in base else base
    stem = re.sub(r"\.{2,}", ".", stem).strip(" .")[:100] or "attachment"

    if extension:
        return f"{stem}{extension}"
    return f"{stem}.{base.rsplit('.', 1)[1][:10]}" if "." in base else stem


def storage_key_for(tenant_id: uuid.UUID, message_id: uuid.UUID, extension: str) -> str:
    return f"tenants/{tenant_id.hex}/messages/{message_id.hex}/{uuid.uuid4().hex}{extension}"


def media_endpoint(message_id: uuid.UUID) -> str:
    return f"/api/v1/messages/{message_id}/media"


# =========================
# REGISTRATION (inside event processing transaction)
# =========================

def register_pending(
    db: Session,
    message: Message,
    *,
    provider_media_id: str,
    media_kind: str,
    declared_mime: str | None,
    declared_filename: str | None,
    declared_sha256: str | None,
) -> None:
    """Create the PENDING media row for a new inbound message (idempotent)."""

    if media_kind not in MEDIA_RULES or not provider_media_id:
        return

    db.execute(
        insert(MessageMedia)
        .values(
            id=uuid.uuid4(),
            tenant_id=message.tenant_id,
            message_id=message.id,
            channel_connection_id=message.channel_connection_id,
            provider_media_id=provider_media_id[:255],
            media_kind=media_kind,
            original_filename=sanitize_filename(declared_filename),
            status=MediaStatus.PENDING,
            attempts=0,
            media_info={
                "declared_mime_type": normalize_mime(declared_mime),
                "declared_sha256": declared_sha256 if isinstance(declared_sha256, str) else None,
            },
        )
        .on_conflict_do_nothing(constraint="uq_message_media_tenant_message")
    )


# =========================
# DOWNLOAD
# =========================

@dataclass(frozen=True)
class _Claim:
    media_id: uuid.UUID
    tenant_id: uuid.UUID
    message_id: uuid.UUID
    media_kind: str
    provider_media_id: str
    phone_number_id: str | None
    encrypted_token: str | None
    declared_sha256: str | None
    original_filename: str | None
    attempts: int


def _claim(db: Session, media_id: uuid.UUID) -> _Claim | None:
    now = _utcnow()

    media = (
        db.query(MessageMedia)
        .filter(
            MessageMedia.id == media_id,
            MessageMedia.status == MediaStatus.PENDING,
            or_(
                MessageMedia.last_attempt_at.is_(None),
                MessageMedia.last_attempt_at < now - LEASE,
            ),
        )
        .with_for_update(skip_locked=True)
        .first()
    )
    if media is None:
        db.rollback()
        return None

    channel = db.get(ChannelConnection, media.channel_connection_id)
    valid_channel = (
        channel is not None
        and channel.tenant_id == media.tenant_id
        and channel.channel_type == ChannelType.WHATSAPP
    )

    media.attempts += 1
    media.last_attempt_at = now

    claim = _Claim(
        media_id=media.id,
        tenant_id=media.tenant_id,
        message_id=media.message_id,
        media_kind=media.media_kind,
        provider_media_id=media.provider_media_id,
        phone_number_id=channel.external_account_id if valid_channel else None,
        encrypted_token=channel.access_token_encrypted if valid_channel else None,
        declared_sha256=(media.media_info or {}).get("declared_sha256"),
        original_filename=media.original_filename,
        attempts=media.attempts,
    )
    db.commit()
    return claim


def _fetch(claim: _Claim) -> tuple[bytes, str, str]:
    """Network part. Returns (data, verified mime, sha256 hex)."""

    if not claim.encrypted_token or not claim.phone_number_id:
        raise _PermanentFailure("Channel credentials are unavailable.")

    try:
        token = get_credential_service().decrypt(claim.encrypted_token)
    except CredentialEncryptionError:
        raise _PermanentFailure("Channel credentials are unavailable.") from None

    provider = get_provider(ChannelType.WHATSAPP)
    assert isinstance(provider, WhatsAppProvider)
    credentials = ProviderCredentials(access_token=token)
    max_bytes, allowed = MEDIA_RULES[claim.media_kind]

    try:
        info = provider.get_media_info(credentials, claim.provider_media_id, claim.phone_number_id)

        mime = normalize_mime(info.get("mime_type"))
        if mime not in allowed:
            raise _PermanentFailure("Unsupported media type.")

        declared_size = info.get("file_size")
        if isinstance(declared_size, (int, str)) and str(declared_size).isdigit():
            if int(declared_size) > max_bytes:
                raise _PermanentFailure("Media exceeds the size limit.")

        url = info.get("url")
        if not isinstance(url, str) or not url:
            raise _PermanentFailure("WhatsApp returned no media URL.")

        data, content_type = provider.download_media(
            credentials, url, max_bytes, settings.media_download_timeout_seconds,
        )

    except ProviderPayloadTooLargeError:
        raise _PermanentFailure("Media exceeds the size limit.") from None
    except ProviderRequestError as exc:
        raise _PermanentFailure(f"WhatsApp media request failed: {exc}"[:1000]) from None
    except ProviderUnavailableError as exc:
        raise _TransientFailure(str(exc)) from None
    except ProviderNotConfiguredError:
        raise _TransientFailure("WhatsApp integration is not configured.") from None

    header_mime = normalize_mime(content_type)
    if header_mime and header_mime not in GENERIC_CONTENT_TYPES and header_mime != mime:
        raise _PermanentFailure("Downloaded media type does not match.")

    digest = hashlib.sha256(data).hexdigest()
    expected = info.get("sha256") or claim.declared_sha256
    if isinstance(expected, str) and expected and expected.lower() != digest:
        raise _PermanentFailure("Media integrity check failed.")

    return data, mime, digest


def _finish_failure(db: Session, claim: _Claim, error: str, permanent: bool) -> str:
    media = db.query(MessageMedia).filter(MessageMedia.id == claim.media_id).with_for_update().one()

    exhausted = claim.attempts >= settings.media_max_download_attempts
    media.error = error[:1000]
    if permanent or exhausted:
        media.status = MediaStatus.FAILED

    db.commit()
    return MediaOutcome.FAILED if (permanent or exhausted) else MediaOutcome.RETRY


def _finish_success(db: Session, claim: _Claim, mime: str, size: int, digest: str, key: str, backend: str) -> None:
    extension = MEDIA_RULES[claim.media_kind][1][mime]

    media = db.query(MessageMedia).filter(MessageMedia.id == claim.media_id).with_for_update().one()
    media.status = MediaStatus.DOWNLOADED
    media.mime_type = mime
    media.file_size = size
    media.sha256 = digest
    media.storage_key = key
    media.storage_backend = backend
    media.downloaded_at = _utcnow()
    media.error = None
    if claim.original_filename:
        media.original_filename = sanitize_filename(claim.original_filename, extension)

    message = db.get(Message, claim.message_id)
    if message is not None and message.tenant_id == claim.tenant_id:
        message.media_url = media_endpoint(message.id)
        message.media_type = mime

    db.commit()


def download_media(db: Session, media_id: uuid.UUID) -> str:
    """Download one media row. Returns a MediaOutcome value."""

    claim = _claim(db, media_id)
    if claim is None:
        return MediaOutcome.SKIPPED

    try:
        data, mime, digest = _fetch(claim)
        storage = get_storage()
        extension = MEDIA_RULES[claim.media_kind][1][mime]
        key = storage_key_for(claim.tenant_id, claim.message_id, extension)
        storage.save(key, data, mime)
    except _PermanentFailure as exc:
        outcome = _finish_failure(db, claim, str(exc), permanent=True)
    except (_TransientFailure, StorageError) as exc:
        outcome = _finish_failure(db, claim, str(exc), permanent=False)
    else:
        try:
            _finish_success(db, claim, mime, len(data), digest, key, storage.backend_name)
        except SQLAlchemyError:
            db.rollback()
            try:
                storage.delete(key)
            except StorageError:
                logger.warning("Could not remove orphaned media for row %s.", claim.media_id)
            raise
        outcome = MediaOutcome.DOWNLOADED

    logger.info("Media %s %s (attempt %d).", claim.media_id, outcome, claim.attempts)
    return outcome


def process_pending_media(db: Session, limit: int = 20) -> dict[str, int]:
    cutoff = _utcnow() - LEASE
    media_ids = db.scalars(
        select(MessageMedia.id)
        .where(
            MessageMedia.status == MediaStatus.PENDING,
            or_(MessageMedia.last_attempt_at.is_(None), MessageMedia.last_attempt_at < cutoff),
        )
        .order_by(MessageMedia.created_at.asc(), MessageMedia.id.asc())
        .limit(limit)
    ).all()
    db.rollback()

    counts: Counter[str] = Counter()
    for media_id in media_ids:
        counts[download_media(db, media_id)] += 1
    return dict(counts)


# =========================
# SERVING (authenticated API)
# =========================

def open_media(
    db: Session,
    tenant_id: uuid.UUID,
    message_id: uuid.UUID,
) -> tuple[MessageMedia, Iterator[bytes]]:
    media = (
        db.query(MessageMedia)
        .filter(MessageMedia.tenant_id == tenant_id, MessageMedia.message_id == message_id)
        .first()
    )
    if media is None:
        raise MediaNotFoundError("Media not found.")
    if media.status != MediaStatus.DOWNLOADED or not media.storage_key:
        raise MediaNotReadyError("Media is not available yet.")

    try:
        chunks = get_storage().iter_chunks(media.storage_key)
    except StorageError:
        raise MediaNotReadyError("Media is not available.") from None

    return media, chunks
