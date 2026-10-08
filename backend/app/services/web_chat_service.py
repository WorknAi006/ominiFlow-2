"""
Web Chat channel: a first-party Omniflow channel.

Dashboard side (authenticated): create a Web Chat channel and mint its
public widget key. Public side (widget, no auth): the tenant and channel
are always derived from the public key in the URL — never trusted from the
browser. Inbound messages flow through the same channel-neutral
inbound_event_service as every other channel; outbound agent/automation
replies are delivered by the widget polling for new messages.
"""
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.base import ProviderCredentials
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Contact,
    ContactIdentity,
    Conversation,
    Message,
    MessageDirection,
)
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.web_chat import (
    WebChatConfigResponse,
    WebChatInboundRequest,
    WebChatInboundResponse,
    WebChatMessageOut,
    WebChatMessagesResponse,
)
from app.services import channel_service, inbound_event_service, realtime_service

MESSAGE_PAGE_SIZE = 100


class WebChatError(Exception):
    """Base Web Chat error."""


class WebChatChannelNotFoundError(WebChatError):
    """Raised when a channel or public key does not resolve."""


class NotWebChatChannelError(WebChatError):
    """Raised when a channel exists but is not a Web Chat channel."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _public_key() -> str:
    return f"wc_{secrets.token_urlsafe(24)}"


# =========================
# DASHBOARD (authenticated)
# =========================

def connect_web_chat_channel(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ChannelConnectionResponse:
    """
    Activate a Web Chat channel, minting a public widget key if absent.
    Idempotent: reconnecting keeps the existing key.
    """
    channel = (
        db.query(ChannelConnection)
        .filter(
            ChannelConnection.id == channel_id,
            ChannelConnection.tenant_id == tenant_id,
            ChannelConnection.is_deleted.is_(False),
        )
        .with_for_update()
        .first()
    )
    if channel is None:
        raise WebChatChannelNotFoundError("Channel not found.")
    if channel.channel_type != ChannelType.WEB_CHAT:
        raise NotWebChatChannelError("This channel is not a Web Chat channel.")

    if not channel.external_account_id:
        channel.external_account_id = _public_key()

    channel.status = ChannelStatus.CONNECTED
    channel.is_active = True
    channel.last_connected_at = _utcnow()
    channel.last_error = None

    db.commit()
    db.refresh(channel)
    return channel_service._to_response(channel)


# =========================
# PUBLIC (widget)
# =========================

def _resolve_channel(db: Session, public_key: str) -> ChannelConnection:
    channel = channel_service.find_connected_channel(
        db, ChannelType.WEB_CHAT, public_key,
    )
    if channel is None:
        raise WebChatChannelNotFoundError("Unknown or inactive Web Chat channel.")
    return channel


def get_config(db: Session, public_key: str) -> WebChatConfigResponse:
    channel = _resolve_channel(db, public_key)
    return WebChatConfigResponse(channel_name=channel.name)


def process_inbound(
    db: Session,
    public_key: str,
    data: WebChatInboundRequest,
) -> WebChatInboundResponse:
    """
    Accept a visitor message, run it through the common inbound pipeline,
    and echo back the stored message. Idempotent per (visitor, client
    message id).
    """
    channel = _resolve_channel(db, public_key)

    if data.client_message_id:
        external_message_id = f"wc:{data.visitor_id}:{data.client_message_id}"
    else:
        external_message_id = f"wc_in_{uuid.uuid4().hex}"

    provider = get_provider(ChannelType.WEB_CHAT)
    normalized = provider.normalize_inbound_message(
        channel,
        {
            "visitor_id": data.visitor_id,
            "text": data.text,
            "display_name": data.display_name,
            "external_message_id": external_message_id,
            "external_event_id": data.client_message_id,
            "occurred_at": _utcnow(),
        },
    )
    if normalized is None:
        raise WebChatError("Message could not be processed.")

    realtime_events = inbound_event_service.process_inbound_event(db, normalized)
    db.commit()

    # Only after commit; best effort (never raises) — same rule as webhooks.
    for event in realtime_events:
        realtime_service.publish_event(event)

    stored = (
        db.query(Message)
        .filter(
            Message.tenant_id == channel.tenant_id,
            Message.channel_connection_id == channel.id,
            Message.external_message_id == external_message_id,
        )
        .first()
    )
    if stored is None:
        raise WebChatError("Message could not be stored.")

    return WebChatInboundResponse(
        conversation_id=str(stored.conversation_id),
        message=_to_out(stored),
    )


def list_visitor_messages(
    db: Session,
    public_key: str,
    visitor_id: str,
    after: datetime | None = None,
) -> WebChatMessagesResponse:
    """Messages in the visitor's conversation, oldest first, after a
    timestamp cursor. Empty until the visitor has a conversation."""
    channel = _resolve_channel(db, public_key)

    identity = (
        db.query(ContactIdentity)
        .filter(
            ContactIdentity.tenant_id == channel.tenant_id,
            ContactIdentity.channel_type == ChannelType.WEB_CHAT.value,
            ContactIdentity.external_id == visitor_id,
        )
        .first()
    )
    if identity is None:
        return WebChatMessagesResponse(messages=[])

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == channel.tenant_id,
            Conversation.contact_id == identity.contact_id,
            Conversation.channel_connection_id == channel.id,
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )
    if conversation is None:
        return WebChatMessagesResponse(messages=[])

    query = db.query(Message).filter(
        Message.tenant_id == channel.tenant_id,
        Message.conversation_id == conversation.id,
    )
    if after is not None:
        query = query.filter(Message.created_at > after)

    messages = (
        query.order_by(Message.created_at.asc(), Message.id.asc())
        .limit(MESSAGE_PAGE_SIZE)
        .all()
    )
    return WebChatMessagesResponse(messages=[_to_out(m) for m in messages])


def _to_out(message: Message) -> WebChatMessageOut:
    # Visitors see their own messages as inbound->"visitor" and agent
    # replies as outbound->"agent".
    direction = "agent" if message.direction == MessageDirection.OUTBOUND else "visitor"
    return WebChatMessageOut(
        id=str(message.id),
        direction=direction,
        text=message.text,
        created_at=message.created_at,
    )
