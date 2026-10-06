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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from app.models import ChannelConnection, ChannelType


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


class ChannelProvider(ABC):
    channel_type: ClassVar[ChannelType]
    display_name: ClassVar[str]

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
