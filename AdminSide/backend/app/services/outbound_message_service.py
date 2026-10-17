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
        else:
            external_id = provider.send_text(
                credentials,
                channel,
                recipient,
                data.text,
                reply_to_external_id,
            )
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
        conversation=conversation if isinstance(data, TextMessageCreate) else None,
    )
    if realtime_event is not None:
        realtime_service.publish_event(realtime_event)

    logger.info("Outbound message %s sent on channel %s.", message_id, channel.id)

    return message_service.get_message(db, tenant_id, message_id)
