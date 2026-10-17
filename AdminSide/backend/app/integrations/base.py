"""
Common interface for external channel providers.

Each provider (WhatsApp, Instagram, Facebook) implements ChannelProvider
in its own package under app/integrations/<provider>/. Providers receive
decrypted credentials in memory only; they must never log them or
persist them except through the credential service.

Webhook routing (future): each provider exposes its own webhook endpoint,
verifies the provider signature, then resolves the tenant/channel with
channel_service.find_connected_channel(channel_type, external_account_id).
Webhooks never accept a tenant_id from the caller.
"""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from app.models import ChannelConnection, ChannelType, MessageType


class ProviderError(Exception):
    """Base provider error. Messages must never include credentials."""


class ProviderNotImplementedError(ProviderError):
    """Raised by providers whose integration is not built yet."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when platform credentials (app id/secret) are missing."""


class ProviderVerificationError(ProviderError):
    """Raised when credentials or account ownership fail verification."""


class ProviderUnavailableError(ProviderError):
    """Raised when the provider cannot be reached."""


class ProviderRequestError(ProviderError):
    """Raised when the provider rejects a request (e.g. a message send)."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ProviderPayloadTooLargeError(ProviderRequestError):
    """Raised when provider content (e.g. media) exceeds a size limit."""


@dataclass(frozen=True)
class ProviderCredentials:
    access_token: str = field(repr=False)
    refresh_token: str | None = field(default=None, repr=False)
    expires_at: datetime | None = None


@dataclass(frozen=True)
class ProviderAccountInfo:
    external_account_id: str
    external_business_id: str | None = None
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedInboundEvent:
    """
    Channel-neutral inbound message, produced by a provider's normalizer
    from its raw webhook payload and consumed by the common inbound event
    service. Provider-specific fields live in `metadata`; nothing
    provider-specific leaks into the generic processing path.

    `external_sender_id` is resolved through ContactIdentity
    (channel_type + external_sender_id). `phone_hint` is set only by
    channels whose sender id is a phone number (WhatsApp wa_id), so the
    existing phone-based contact dedup keeps working; other channels leave
    it None and resolve purely by identity.
    """

    tenant_id: uuid.UUID
    channel_connection_id: uuid.UUID
    channel_type: str
    external_message_id: str
    external_sender_id: str
    message_type: MessageType
    occurred_at: datetime
    external_event_id: str | None = None
    sender_display_name: str | None = None
    phone_hint: str | None = None
    text: str | None = None
    media_type: str | None = None
    media_metadata: dict[str, Any] | None = None
    external_thread_id: str | None = None
    reply_to_external_id: str | None = None
    metadata: dict[str, Any] | None = None


class ChannelProvider(ABC):
    channel_type: ClassVar[ChannelType]
    display_name: ClassVar[str]
    # Whether outbound sending needs stored provider credentials. External
    # APIs (WhatsApp/Meta) need a token; an internal channel (Web Chat)
    # delivers through Omniflow itself and needs none.
    requires_credentials: ClassVar[bool] = True

    @abstractmethod
    def connect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        """Complete authorization and return the verified account."""

    @abstractmethod
    def disconnect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> None:
        """Revoke access / unsubscribe webhooks at the provider."""

    @abstractmethod
    def refresh_token(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderCredentials:
        """Return refreshed credentials."""

    @abstractmethod
    def validate_credentials(
        self,
        credentials: ProviderCredentials,
    ) -> bool:
        """Check the credentials against the provider."""

    @abstractmethod
    def get_account_info(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        """Fetch account details from the provider."""

    # ---------- outbound messaging (generic contract) ----------

    @abstractmethod
    def recipient_for(self, connection: ChannelConnection, contact: Any) -> str:
        """
        Resolve the channel-specific recipient address for a contact (e.g.
        the WhatsApp recipient id). Keeps provider-specific addressing out
        of the generic outbound service.
        """

    @abstractmethod
    def send_text(
        self,
        credentials: ProviderCredentials,
        connection: ChannelConnection,
        recipient: str,
        text: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        """Send a free-form text message; return the provider message id."""

    # ---------- inbound normalization (generic contract) ----------

    @abstractmethod
    def normalize_inbound_message(
        self,
        connection: ChannelConnection,
        raw: dict[str, Any],
    ) -> "NormalizedInboundEvent | None":
        """
        Turn a raw stored inbound event into a NormalizedInboundEvent, or
        None when it is not a processable inbound message (malformed /
        missing id or sender / unsupported). All provider-specific payload
        parsing lives here, never in the common inbound service.
        """


class UnimplementedChannelProvider(ChannelProvider):
    """
    Placeholder for providers not built yet. Every operation fails
    explicitly so no code path can report a fake successful connection.
    """

    def _not_implemented(self) -> ProviderNotImplementedError:
        return ProviderNotImplementedError(
            f"{self.display_name} integration is not implemented yet."
        )

    def connect(self, connection, credentials):
        raise self._not_implemented()

    def disconnect(self, connection, credentials):
        raise self._not_implemented()

    def refresh_token(self, connection, credentials):
        raise self._not_implemented()

    def validate_credentials(self, credentials):
        raise self._not_implemented()

    def get_account_info(self, connection, credentials):
        raise self._not_implemented()

    def recipient_for(self, connection, contact):
        raise self._not_implemented()

    def send_text(self, credentials, connection, recipient, text, reply_to_external_id=None):
        raise self._not_implemented()

    def normalize_inbound_message(self, connection, raw):
        raise self._not_implemented()
