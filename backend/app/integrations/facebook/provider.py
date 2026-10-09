"""
Facebook Messenger provider (Meta Messenger Platform).

Mapping onto ChannelConnection:
- external_account_id  -> Facebook Page id (webhook routing key)
- external_business_id -> unused for Messenger (kept null)
- access_token         -> Page access token

All Facebook/Meta-specific logic lives here; the core inbound/outbound
services stay channel-neutral. Verified against the official Messenger
Platform documentation (webhook "messages" event, Send API, subscribed_apps,
X-Hub-Signature-256). See TASK report for live-verification status.
"""
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.integrations.base import (
    ChannelProvider,
    NormalizedInboundEvent,
    ProviderAccountInfo,
    ProviderCredentials,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderUnavailableError,
    ProviderVerificationError,
)
from app.integrations.meta.graph_client import (
    MetaGraphClient,
    MetaGraphError,
    MetaGraphUnavailableError,
    build_graph_client,
    is_meta_configured,
)
from app.models import ChannelConnection, ChannelType, MessageType

# Permissions a Page access token must carry to receive and send Messenger
# messages and to manage the app's webhook subscription on the Page.
REQUIRED_SCOPES = frozenset({
    "pages_messaging",
    "pages_manage_metadata",
})

PAGE_FIELDS = "id,name"

MAX_TEXT_LENGTH = 2000


class FacebookProvider(ChannelProvider):

    channel_type = ChannelType.FACEBOOK
    display_name = "Facebook"

    def __init__(
        self,
        client_factory: Callable[[], MetaGraphClient] = build_graph_client,
    ) -> None:
        self.client_factory = client_factory

    # ---------- helpers ----------

    def is_configured(self) -> bool:
        return is_meta_configured()

    def _client(self) -> MetaGraphClient:
        if not self.is_configured():
            raise ProviderNotConfiguredError(
                "Facebook integration is not configured."
            )
        return self.client_factory()

    def _call(self, fn: Callable[[], Any], failure: str) -> Any:
        """Verification/connect calls: Graph errors -> verification errors."""
        try:
            return fn()
        except MetaGraphUnavailableError:
            raise ProviderUnavailableError(
                "Could not reach Facebook. Please try again later."
            ) from None
        except MetaGraphError as exc:
            raise ProviderVerificationError(f"{failure} {exc}".strip()) from None

    def _graph(self, fn: Callable[[], Any]) -> Any:
        """Outbound calls: Graph errors -> request/unavailable (like WhatsApp)."""
        try:
            return fn()
        except MetaGraphUnavailableError:
            raise ProviderUnavailableError(
                "Could not reach Facebook. Please try again later."
            ) from None
        except MetaGraphError as exc:
            raise ProviderRequestError(
                str(exc),
                code=str(exc.code) if exc.code is not None else None,
            ) from None

    @staticmethod
    def _occurred_at(timestamp: Any) -> datetime:
        # Messenger timestamps are epoch milliseconds.
        if isinstance(timestamp, (int, float)) and timestamp > 0:
            try:
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                pass
        return datetime.now(timezone.utc)

    # ---------- Facebook-specific operations ----------

    def inspect_token(
        self,
        client: MetaGraphClient,
        credentials: ProviderCredentials,
    ) -> None:
        data = self._call(
            lambda: client.debug_token(credentials.access_token),
            "Access token could not be verified.",
        )

        if data.get("is_valid") is not True:
            raise ProviderVerificationError("Access token is invalid or expired.")

        if str(data.get("app_id")) != client.app_id:
            raise ProviderVerificationError(
                "Access token was not issued for this application."
            )

        scopes = set(data.get("scopes") or [])
        missing = REQUIRED_SCOPES - scopes
        if missing:
            raise ProviderVerificationError(
                "Access token is missing required permissions: "
                + ", ".join(sorted(missing)) + "."
            )

        expires_at = data.get("expires_at")
        if isinstance(expires_at, int) and 0 < expires_at <= int(
            datetime.now(timezone.utc).timestamp()
        ):
            raise ProviderVerificationError("Access token is invalid or expired.")

    def verify_page(
        self,
        credentials: ProviderCredentials,
        page_id: str,
    ) -> ProviderAccountInfo:
        """Verify the token and that it can read the target Page."""
        with self._client() as client:
            self.inspect_token(client, credentials)
            page = self._call(
                lambda: client.request(
                    "GET", page_id,
                    access_token=credentials.access_token,
                    params={"fields": PAGE_FIELDS},
                ),
                "Facebook Page could not be verified.",
            )

        if str(page.get("id")) != page_id:
            raise ProviderVerificationError(
                "Facebook Page could not be verified."
            )

        return ProviderAccountInfo(
            external_account_id=page_id,
            external_business_id=None,
            display_name=page.get("name"),
            metadata={"page_name": page.get("name")},
        )

    def subscribe_webhooks(
        self,
        credentials: ProviderCredentials,
        page_id: str,
    ) -> None:
        """Subscribe our app to the Page's `messages` webhook field."""
        with self._client() as client:
            body = self._call(
                lambda: client.request(
                    "POST", f"{page_id}/subscribed_apps",
                    access_token=credentials.access_token,
                    params={"subscribed_fields": "messages"},
                ),
                "Webhook subscription failed.",
            )

        if body.get("success") is not True:
            raise ProviderVerificationError("Webhook subscription failed.")

    def is_webhook_subscribed(
        self,
        credentials: ProviderCredentials,
        page_id: str,
    ) -> bool:
        """Read-only diagnostic: is our app subscribed to this Page?"""
        with self._client() as client:
            body = self._call(
                lambda: client.request(
                    "GET", f"{page_id}/subscribed_apps",
                    access_token=credentials.access_token,
                ),
                "Webhook subscription could not be read.",
            )
            app_id = client.app_id

        for entry in body.get("data") or []:
            if not isinstance(entry, dict):
                continue
            candidate = entry.get("id")
            fields = entry.get("subscribed_fields") or []
            field_names = {
                f.get("name") if isinstance(f, dict) else f for f in fields
            }
            if candidate is not None and str(candidate) == app_id:
                return "messages" in field_names or not field_names
        return False

    # ---------- generic outbound contract (ChannelProvider) ----------

    def recipient_for(self, connection: ChannelConnection, contact: Any) -> str:
        """
        The Facebook recipient is the Page-scoped id (PSID), stored as a
        ContactIdentity (channel_type=facebook). Never a phone number.
        """
        for identity in getattr(contact, "identities", None) or []:
            if getattr(identity, "channel_type", None) == ChannelType.FACEBOOK.value:
                if identity.external_id:
                    return str(identity.external_id)
        raise ValueError("This contact has no Facebook Messenger identity.")

    def send_text(
        self,
        credentials: ProviderCredentials,
        connection: ChannelConnection,
        recipient: str,
        text: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        """
        Send a text message via the Messenger Send API. Returns the Facebook
        message id. The 24h standard messaging window is enforced by Meta.
        """
        payload: dict[str, Any] = {
            "recipient": {"id": recipient},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        }

        with self._client() as client:
            body = self._graph(
                lambda: client.request(
                    "POST", "me/messages",
                    access_token=credentials.access_token,
                    json=payload,
                )
            )

        message_id = body.get("message_id")
        if not isinstance(message_id, str) or not message_id:
            raise ProviderRequestError("Facebook did not return a message id.")
        return message_id

    # ---------- inbound normalization (generic contract) ----------

    def normalize_inbound_message(
        self,
        connection: ChannelConnection,
        raw: dict[str, Any],
    ) -> NormalizedInboundEvent | None:
        """
        Normalize a single Messenger `messaging` event into the common
        inbound event. Returns None for anything that is not a processable
        inbound message (delivery/read receipts, echoes, missing id/sender).
        """
        if not isinstance(raw, dict):
            return None

        message = raw.get("message")
        if not isinstance(message, dict) or message.get("is_echo"):
            return None

        sender = raw.get("sender") if isinstance(raw.get("sender"), dict) else {}
        external_sender_id = sender.get("id")
        external_message_id = message.get("mid")
        if not external_sender_id or not external_message_id:
            return None

        text = message.get("text")
        if isinstance(text, str) and text.strip():
            message_type = MessageType.TEXT
            body = text.strip()[:MAX_TEXT_LENGTH]
            metadata = None
        else:
            # Text-first: non-text content is recorded without invented
            # content so the conversation still reflects the inbound event.
            message_type = MessageType.UNKNOWN
            body = None
            attachments = message.get("attachments")
            kinds = [
                a.get("type") for a in attachments
                if isinstance(a, dict) and a.get("type")
            ] if isinstance(attachments, list) else []
            metadata = {"provider_type": kinds[0] if kinds else "unsupported"}

        reply_to = message.get("reply_to")
        reply_to_external_id = (
            reply_to.get("mid") if isinstance(reply_to, dict) else None
        )

        return NormalizedInboundEvent(
            tenant_id=connection.tenant_id,
            channel_connection_id=connection.id,
            channel_type=ChannelType.FACEBOOK.value,
            external_message_id=str(external_message_id),
            external_sender_id=str(external_sender_id),
            # A Facebook PSID is not a phone; resolve purely by identity.
            phone_hint=None,
            sender_display_name=None,
            message_type=message_type,
            text=body,
            occurred_at=self._occurred_at(raw.get("timestamp")),
            reply_to_external_id=reply_to_external_id,
            metadata=metadata,
        )

    # ---------- ChannelProvider interface ----------

    def connect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        if not connection.external_account_id:
            raise ProviderVerificationError("A Facebook Page id is required.")

        info = self.verify_page(credentials, connection.external_account_id)
        self.subscribe_webhooks(credentials, connection.external_account_id)
        return info

    def disconnect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> None:
        """Unsubscribe our app from the Page's webhooks."""
        if not connection.external_account_id:
            return
        with self._client() as client:
            self._call(
                lambda: client.request(
                    "DELETE", f"{connection.external_account_id}/subscribed_apps",
                    access_token=credentials.access_token,
                ),
                "Webhook unsubscription failed.",
            )

    def refresh_token(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderCredentials:
        raise ProviderError(
            "Facebook Page tokens cannot be refreshed here. "
            "Reconnect the channel with a new token."
        )

    def validate_credentials(self, credentials: ProviderCredentials) -> bool:
        try:
            with self._client() as client:
                self.inspect_token(client, credentials)
        except ProviderVerificationError:
            return False
        return True

    def get_account_info(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        if not connection.external_account_id:
            raise ProviderVerificationError("Channel has no Facebook Page id.")
        return self.verify_page(credentials, connection.external_account_id)
