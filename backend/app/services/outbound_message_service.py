"""
Outbound messaging: Conversation -> Message -> Provider -> Meta.

Transaction rule: no database transaction is open during the provider
HTTP call. A PENDING message is committed first, the provider is called,
then the message is updated (SENT with the provider id, or FAILED with a
sanitized error).
"""
import logging
import hashlib
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.base import (
    ProviderCredentials,
    ProviderNotConfiguredError,
    ProviderNotImplementedError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    Contact,
    Conversation,
    MessageStatus,
    MessageType,
    User,
)
from app.schemas.message import (
    InteractiveMessageCreate,
    MediaMessageCreate,
    MessageCreate,
    MessageResponse,
    TemplateMessageCreate,
    TextMessageCreate,
)
from app.services import conversation_service, message_service, realtime_service, template_service
from app.services.credential_service import (
    CredentialEncryptionError,
    get_credential_service,
)
from app.services.message_service import to_message_response

logger = logging.getLogger(__name__)


class OutboundMessageError(Exception):
    """Base outbound messaging error."""


class UnsupportedChannelError(OutboundMessageError):
    """Raised when the conversation's channel cannot send this message."""


class ChannelNotConnectedError(OutboundMessageError):
    """Raised when the channel is not connected / active."""


class RecipientUnavailableError(OutboundMessageError):
    """Raised when the contact cannot receive messages."""


class InvalidReplyError(OutboundMessageError):
    """Raised when reply_to_message_id is not in this conversation."""


class CredentialsUnavailableError(OutboundMessageError):
    """Raised when stored credentials cannot be decrypted."""


class ProviderNotConfiguredForSendError(OutboundMessageError):
    """Raised when the provider app is not configured."""


class MessageSendFailedError(OutboundMessageError):
    """Raised when the provider rejected or could not receive the message."""

    def __init__(self, message: str, message_id: uuid.UUID) -> None:
        super().__init__(message)
        self.message_id = message_id


class IdempotencyConflictError(OutboundMessageError):
    """A request key was reused with a different payload."""


def _request_hash(conversation_id: uuid.UUID, data: MessageCreate) -> str:
    canonical = json.dumps(
        {"conversation_id": str(conversation_id), "message": data.model_dump(mode="json")},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MediaUnavailableError(OutboundMessageError):
    """Raised when a flow media asset cannot be read for sending."""


def _resolve_flow_media(tenant_id: uuid.UUID, media_key: str) -> tuple[bytes, str]:
    """Read a flow-uploaded asset's bytes and content type, restricted to the
    tenant's own asset prefix (keys embed the tenant id)."""
    from app.storage import get_storage
    from app.storage.base import StorageError

    if not media_key.startswith(f"flow-assets/{tenant_id.hex}/"):
        raise MediaUnavailableError("Media asset does not belong to this tenant.")
    storage = get_storage()
    try:
        if not storage.exists(media_key):
            raise MediaUnavailableError("Media asset was not found.")
        data = b"".join(storage.iter_chunks(media_key))
    except StorageError:
        raise MediaUnavailableError("Media asset could not be read.") from None
    if not data:
        raise MediaUnavailableError("Media asset is empty.")
    content_type = mimetypes.guess_type(media_key)[0] or "application/octet-stream"
    return data, content_type


def _finish(
    db: Session,
    tenant_id: uuid.UUID,
    message_id: uuid.UUID,
    *,
    external_id: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    conversation: Conversation | None = None,
) -> dict[str, Any] | None:
    message = message_service.get_message_model(db, tenant_id, message_id, for_update=True)
    now = _utcnow()

    if external_id is not None:
        message.external_message_id = external_id
        message_service.update_message_status(db, message, MessageStatus.SENT, now)
    else:
        message_service.update_message_status(
            db, message, MessageStatus.FAILED, now, error_code, error_message,
        )

    realtime_event = None
    if external_id is not None and conversation is not None:
        realtime_event = realtime_service.build_conversation_updated_event(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            **conversation_service.get_update_snapshot(db, conversation),
        )

    db.commit()
    return realtime_event


def send_message(
    db: Session,
    tenant_id: uuid.UUID,
    actor: User,
    conversation_id: uuid.UUID,
    data: MessageCreate,
    idempotency_key: uuid.UUID | None = None,
) -> MessageResponse:

    key = idempotency_key or uuid.uuid4()
    payload_hash = _request_hash(conversation_id, data)
    existing = db.query(message_service.Message).filter(
        message_service.Message.tenant_id == tenant_id,
        message_service.Message.idempotency_key == key,
    ).first()
    if existing is not None:
        if existing.idempotency_payload_hash != payload_hash:
            raise IdempotencyConflictError("Idempotency key was already used with a different message.")
        return message_service.to_message_response(existing)

    conversation = conversation_service.get_conversation_model(db, tenant_id, conversation_id)

    contact = (
        db.query(Contact)
        .filter(Contact.id == conversation.contact_id, Contact.tenant_id == tenant_id)
        .first()
    )
    channel = (
        db.query(ChannelConnection)
        .filter(
            ChannelConnection.id == conversation.channel_connection_id,
            ChannelConnection.tenant_id == tenant_id,
            ChannelConnection.is_deleted.is_(False),
        )
        .first()
    )

    if contact is None:
        raise RecipientUnavailableError("This conversation has no contact.")
    if channel is None:
        raise ChannelNotConnectedError("The channel is not connected.")

    # Dispatch is by channel type: the provider owns how its recipient is
    # addressed. A provider without an implementation fails cleanly here,
    # before any message row is created or credentials are read.
    provider = get_provider(channel.channel_type)

    if (
        channel.status != ChannelStatus.CONNECTED
        or not channel.is_active
        or not channel.external_account_id
        or (provider.requires_credentials and not channel.access_token_encrypted)
    ):
        raise ChannelNotConnectedError("The channel is not connected.")

    if contact.is_blocked:
        raise RecipientUnavailableError("This contact is blocked.")
    try:
        recipient = provider.recipient_for(channel, contact)
    except ProviderNotImplementedError:
        raise UnsupportedChannelError(
            "This channel does not support sending messages yet."
        ) from None
    except ValueError as exc:
        raise RecipientUnavailableError(str(exc)) from None

    reply_to_id, reply_to_external_id = None, None
    if isinstance(data, TextMessageCreate) and data.reply_to_message_id is not None:
        try:
            replied = message_service.get_message_model(db, tenant_id, data.reply_to_message_id)
        except message_service.MessageNotFoundError:
            replied = None
        if replied is None or replied.conversation_id != conversation.id:
            raise InvalidReplyError("reply_to_message_id is not in this conversation.")
        reply_to_id, reply_to_external_id = replied.id, replied.external_message_id

    # Template messages: the template must belong to this tenant + channel,
    # be approved, and the parameters must match its definition. Meta stays
    # the authority on the 24h window; templates are allowed outside it.
    if isinstance(data, TemplateMessageCreate):
        template = template_service.resolve_for_send(
            db, tenant_id, channel.id, data.template_name, data.language,
        )
        template_components, preview = template_service.build_send_components(
            template, data.components,
        )
        message_type = MessageType.TEMPLATE
        message_text = preview
        message_metadata = {
            "template": {
                "id": str(template.id),
                "name": template.name,
                "language": template.language,
                "components": template_components,
            }
        }
    elif isinstance(data, InteractiveMessageCreate):
        template_components = []
        message_type = MessageType.INTERACTIVE
        message_text = data.body
        message_metadata = {
            "interactive": {
                "interactive_type": getattr(data, "interactive_type", "button"),
                "button_text": getattr(data, "button_text", None),
                "header": data.header.model_dump(exclude_none=True) if data.header else None,
                "footer": data.footer,
                "buttons": [b.model_dump(exclude_none=True) for b in data.buttons],
                "list_items": [item.model_dump(exclude_none=True) for item in getattr(data, "list_items", [])],
            }
        }
    elif isinstance(data, MediaMessageCreate):
        template_components = []
        message_type = MessageType(data.media_type)
        message_text = data.caption
        message_metadata = {"media": {"type": data.media_type, "filename": data.filename}}
    else:
        template_components = []
        message_type = MessageType.TEXT
        message_text = data.text
        message_metadata = None

    token = None
    if provider.requires_credentials:
        try:
            token = get_credential_service().decrypt(channel.access_token_encrypted)
        except CredentialEncryptionError:
            logger.error("Could not decrypt credentials for channel %s.", channel.id)
            raise CredentialsUnavailableError(
                "Channel credentials are unavailable. Reconnect the channel."
            ) from None

    phone_number_id = channel.external_account_id

    message = message_service.create_outbound_message(
        db,
        conversation=conversation,
        contact=contact,
        channel=channel,
        text=message_text,
        sender_identifier=phone_number_id,
        recipient_identifier=recipient,
        sent_by_user_id=actor.id,
        reply_to_message_id=reply_to_id,
        message_type=message_type,
        metadata=message_metadata,
        idempotency_key=key,
        idempotency_payload_hash=payload_hash,
    )
    conversation_service.record_activity(db, conversation, _utcnow(), inbound=False)
    message_id = message.id

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(message_service.Message).filter(
            message_service.Message.tenant_id == tenant_id,
            message_service.Message.idempotency_key == key,
        ).first()
        if existing is None:
            raise
        if existing.idempotency_payload_hash != payload_hash:
            raise IdempotencyConflictError("Idempotency key was already used with a different message.") from None
        return message_service.to_message_response(existing)
    except SQLAlchemyError:
        db.rollback()
        raise

    # ---- No transaction is open during the provider call. ----
    try:
        credentials = ProviderCredentials(access_token=token or "")
        if isinstance(data, TemplateMessageCreate):
            external_id = provider.send_template_message(
                credentials,
                phone_number_id,
                recipient,
                data.template_name,
                data.language,
                template_components,
            )
        elif isinstance(data, InteractiveMessageCreate):
            header_dict = None
            if data.header is not None:
                if data.header.type == "text":
                    header_dict = {"type": "text", "text": data.header.text or ""}
                elif data.header.media_key:
                    media_bytes, content_type = _resolve_flow_media(tenant_id, data.header.media_key)
                    media_id = provider.upload_media(
                        credentials, phone_number_id, media_bytes, content_type, data.header.filename,
                    )
                    header_dict = {"type": data.header.type, "id": media_id, "filename": data.header.filename}
                elif data.header.media_url:
                    header_dict = {"type": data.header.type, "link": data.header.media_url, "filename": data.header.filename}
            external_id = provider.send_interactive_message(
                credentials,
                phone_number_id,
                recipient,
                body=data.body,
                header=header_dict,
                footer=data.footer,
                reply_buttons=[{"id": b.id, "title": b.title} for b in data.buttons if b.kind == "reply"],
                url_buttons=[{"title": b.title, "url": b.url} for b in data.buttons if b.kind == "url" and b.url],
                call_buttons=[{"title": b.title, "phone_number": b.phone_number} for b in data.buttons if b.kind == "call" and b.phone_number],
                list_items=[{"id": i.id, "title": i.title, "description": i.description} for i in getattr(data, "list_items", [])],
                button_text=getattr(data, "button_text", None),
            )
        elif isinstance(data, MediaMessageCreate):
            if data.media_key:
                media_bytes, content_type = _resolve_flow_media(tenant_id, data.media_key)
                media_id = provider.upload_media(
                    credentials, phone_number_id, media_bytes, content_type, data.filename,
                )
                external_id = provider.send_media_message(
                    credentials,
                    phone_number_id,
                    recipient,
                    data.media_type,
                    media_id=media_id,
                    caption=data.caption,
                    filename=data.filename,
                )
            elif data.media_url:
                external_id = provider.send_media_message(
                    credentials,
                    phone_number_id,
                    recipient,
                    data.media_type,
                    media_url=data.media_url,
                    caption=data.caption,
                    filename=data.filename,
                )
            else:
                raise MediaUnavailableError("Neither media_key nor media_url was provided.")
        else:
            external_id = provider.send_text(
                credentials,
                channel,
                recipient,
                data.text,
                reply_to_external_id,
            )
    except MediaUnavailableError as exc:
        _finish(db, tenant_id, message_id, error_message=str(exc))
        raise MessageSendFailedError(str(exc), message_id) from None
    except ProviderRequestError as exc:
        _finish(db, tenant_id, message_id, error_code=exc.code, error_message=str(exc))
        raise MessageSendFailedError(f"WhatsApp rejected the message: {exc}", message_id) from None
    except ProviderUnavailableError as exc:
        # The provider may have accepted the request before the timeout. Keep
        # this key permanently bound to the pending message; a retry returns
        # this row and never sends a second provider request.
        raise MessageSendFailedError(str(exc), message_id) from None
    except ProviderNotConfiguredError:
        _finish(db, tenant_id, message_id, error_message="WhatsApp integration is not configured.")
        raise ProviderNotConfiguredForSendError("WhatsApp integration is not configured.") from None
    finally:
        del token

    realtime_event = _finish(
        db,
        tenant_id,
        message_id,
        external_id=external_id,
        conversation=(
            conversation
            if isinstance(data, (TextMessageCreate, InteractiveMessageCreate, MediaMessageCreate))
            else None
        ),
    )
    if realtime_event is not None:
        realtime_service.publish_event(realtime_event)

    logger.info("Outbound message %s sent on channel %s.", message_id, channel.id)

    return message_service.get_message(db, tenant_id, message_id)
