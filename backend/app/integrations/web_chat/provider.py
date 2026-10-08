"""
Web Chat provider: an internal, first-party channel owned by Omniflow.

Unlike WhatsApp there is no external API. A visitor is identified by a
client-generated id (stored as a ContactIdentity with
channel_type=web_chat); inbound messages arrive on a public endpoint and
outbound agent/automation replies are delivered by the visitor's widget
polling for new messages. No provider credentials are involved, so
`requires_credentials` is False and `send_text` needs no token.
"""
import uuid
from typing import Any

from app.integrations.base import (
    ChannelProvider,
    NormalizedInboundEvent,
    ProviderAccountInfo,
    ProviderCredentials,
    ProviderError,
)
from app.models import ChannelConnection, ChannelType, MessageType

MAX_TEXT_LENGTH = 4096


class WebChatProvider(ChannelProvider):

    channel_type = ChannelType.WEB_CHAT
    display_name = "Web Chat"
    requires_credentials = False

    # ---------- channel lifecycle ----------

    def connect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        # Internal channel: "connecting" just confirms the public widget key
        # already assigned by the web chat service. No external call.
        if not connection.external_account_id:
            raise ProviderError("Web Chat channel has no public widget key.")
        return ProviderAccountInfo(
            external_account_id=connection.external_account_id,
            display_name=connection.name,
        )

    def disconnect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> None:
        return None

    def refresh_token(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderCredentials:
        raise ProviderError("Web Chat channels do not use credentials.")

    def validate_credentials(self, credentials: ProviderCredentials) -> bool:
        return True

    def get_account_info(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        return ProviderAccountInfo(
            external_account_id=connection.external_account_id or "",
            display_name=connection.name,
        )

    # ---------- outbound ----------

    def recipient_for(self, connection: ChannelConnection, contact: Any) -> str:
        # Delivery is by the visitor's widget polling this conversation, so
        # there is no external address; the contact id is a stable label.
        return str(getattr(contact, "id", ""))

    def send_text(
        self,
        credentials: ProviderCredentials,
        connection: ChannelConnection,
        recipient: str,
        text: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        # No external API: persisting the outbound message (done by the
        # caller) is the delivery. Return a unique id for external_message_id.
        return f"wc_out_{uuid.uuid4().hex}"

    # ---------- inbound ----------

    def normalize_inbound_message(
        self,
        connection: ChannelConnection,
        raw: dict[str, Any],
    ) -> NormalizedInboundEvent | None:
        """
        Build a NormalizedInboundEvent from a validated widget payload:
        {"visitor_id", "text", "external_message_id", "external_event_id",
         "occurred_at", "display_name"}. Returns None for empty text or a
        missing visitor id (ignored upstream).
        """
        visitor_id = raw.get("visitor_id")
        text = raw.get("text")
        if not visitor_id or not isinstance(text, str) or not text.strip():
            return None

        external_message_id = raw.get("external_message_id") or f"wc_in_{uuid.uuid4().hex}"

        return NormalizedInboundEvent(
            tenant_id=connection.tenant_id,
            channel_connection_id=connection.id,
            channel_type=ChannelType.WEB_CHAT.value,
            external_message_id=str(external_message_id),
            external_sender_id=str(visitor_id),
            # Web Chat visitors have no phone; resolve purely by identity.
            phone_hint=None,
            sender_display_name=raw.get("display_name"),
            message_type=MessageType.TEXT,
            text=text.strip()[:MAX_TEXT_LENGTH],
            occurred_at=raw.get("occurred_at"),
            external_event_id=raw.get("external_event_id"),
        )
