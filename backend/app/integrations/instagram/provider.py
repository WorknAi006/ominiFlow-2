"""
Instagram Messaging provider (Meta Instagram Platform, Facebook Login flow).

An Instagram Professional account is linked to a Facebook Page; messaging is
done on the Page's behalf with a Page access token through the shared
MetaGraphClient (graph.facebook.com), exactly like the Facebook provider.

Mapping onto ChannelConnection:
- external_account_id  -> Instagram Professional account id (IGID), the
                          webhook routing key (entry.id / recipient.id)
- external_business_id -> linked Facebook Page id (token owner)
- access_token         -> Page access token

All Instagram/Meta-specific logic lives here; the core inbound/outbound
services stay channel-neutral. Verified against the official Instagram
messaging documentation (webhook "instagram" object, Send API, Page
subscription, X-Hub-Signature-256). See TASK report for live-verification
status.
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

# Permissions a Page access token must carry to read the linked Instagram
# account and to receive/send its messages.
REQUIRED_SCOPES = frozenset({
    "instagram_basic",
    "instagram_manage_messages",
    "pages_manage_metadata",
})

INSTAGRAM_FIELDS = "id,username,name"
PAGE_LINK_FIELDS = "instagram_business_account{id,username,name}"

MAX_TEXT_LENGTH = 2000


class InstagramProvider(ChannelProvider):

    channel_type = ChannelType.INSTAGRAM
    display_name = "Instagram"

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
                "Instagram integration is not configured."
            )
        return self.client_factory()

    def _call(self, fn: Callable[[], Any], failure: str) -> Any:
        try:
            return fn()
        except MetaGraphUnavailableError:
            raise ProviderUnavailableError(
                "Could not reach Instagram. Please try again later."
            ) from None
        except MetaGraphError as exc:
            raise ProviderVerificationError(f"{failure} {exc}".strip()) from None

    def _graph(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except MetaGraphUnavailableError:
            raise ProviderUnavailableError(
                "Could not reach Instagram. Please try again later."
            ) from None
        except MetaGraphError as exc:
            raise ProviderRequestError(
                str(exc),
                code=str(exc.code) if exc.code is not None else None,
            ) from None

    @staticmethod
    def _occurred_at(timestamp: Any) -> datetime:
        # Instagram messaging timestamps are epoch milliseconds.
        if isinstance(timestamp, (int, float)) and timestamp > 0:
            try:
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                pass
        return datetime.now(timezone.utc)

    # ---------- Instagram-specific operations ----------

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

    def verify_account(
        self,
        credentials: ProviderCredentials,
        instagram_id: str,
        page_id: str,
    ) -> ProviderAccountInfo:
        """
        Verify the token, and that the given Page owns the given Instagram
        Professional account. Proving the token controls the Page that owns
        the IG account prevents claiming an Instagram id the caller does not
        actually control.
        """
        with self._client() as client:
            self.inspect_token(client, credentials)
            page = self._call(
                lambda: client.request(
                    "GET", page_id,
                    access_token=credentials.access_token,
                    params={"fields": PAGE_LINK_FIELDS},
                ),
                "Facebook Page could not be verified.",
            )

        linked = page.get("instagram_business_account")
        linked_id = linked.get("id") if isinstance(linked, dict) else None
        if not linked_id or str(linked_id) != instagram_id:
            raise ProviderVerificationError(
                "This Facebook Page is not linked to the given Instagram account."
            )

        username = linked.get("username") if isinstance(linked, dict) else None
        name = linked.get("name") if isinstance(linked, dict) else None
        return ProviderAccountInfo(
            external_account_id=instagram_id,
            external_business_id=page_id,
            display_name=username or name,
            metadata={"username": username, "name": name, "page_id": page_id},
        )

    def subscribe_webhooks(
        self,
        credentials: ProviderCredentials,
        page_id: str,
    ) -> None:
        """Subscribe our app to the Page's `messages` field (Instagram)."""
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
        """Read-only diagnostic: is our app subscribed on this Page?"""
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

    def account_info(
        self,
        credentials: ProviderCredentials,
        instagram_id: str,
        page_id: str | None = None,
    ) -> ProviderAccountInfo:
        with self._client() as client:
            info = self._call(
                lambda: client.request(
                    "GET", instagram_id,
                    access_token=credentials.access_token,
                    params={"fields": INSTAGRAM_FIELDS},
                ),
                "Instagram account could not be loaded.",
            )

        return ProviderAccountInfo(
            external_account_id=str(info.get("id") or instagram_id),
            external_business_id=page_id,
            display_name=info.get("username") or info.get("name"),
            metadata={"username": info.get("username"), "name": info.get("name")},
        )

    # ---------- generic outbound contract (ChannelProvider) ----------

    def recipient_for(self, connection: ChannelConnection, contact: Any) -> str:
        """
        The Instagram recipient is the Instagram-scoped id (IGSID), stored as
        a ContactIdentity (channel_type=instagram). Never a phone number or a
        Facebook PSID.
        """
        for identity in getattr(contact, "identities", None) or []:
            if getattr(identity, "channel_type", None) == ChannelType.INSTAGRAM.value:
                if identity.external_id:
                    return str(identity.external_id)
        raise ValueError("This contact has no Instagram identity.")

    def send_text(
        self,
        credentials: ProviderCredentials,
        connection: ChannelConnection,
        recipient: str,
        text: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        """
        Send a text message via the Instagram Send API. Returns the message
        id. The standard messaging window is enforced by Meta.
        """
        payload: dict[str, Any] = {
            "recipient": {"id": recipient},
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
            raise ProviderRequestError("Instagram did not return a message id.")
        return message_id

    # ---------- inbound normalization (generic contract) ----------

    def normalize_inbound_message(
        self,
        connection: ChannelConnection,
        raw: dict[str, Any],
    ) -> NormalizedInboundEvent | None:
        """
        Normalize a single Instagram `messaging` event into the common
        inbound event. Returns None for anything that is not a processable
        inbound message (echoes, read/delivery receipts, reactions, missing
        id/sender).
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
            # Text-first: non-text content (story mentions/replies, media,
            # shares) is recorded without invented content.
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
            channel_type=ChannelType.INSTAGRAM.value,
            external_message_id=str(external_message_id),
            external_sender_id=str(external_sender_id),
            # An IGSID is not a phone; resolve purely by identity.
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
        if not connection.external_account_id or not connection.external_business_id:
            raise ProviderVerificationError(
                "An Instagram account id and a linked Facebook Page id are required."
            )
        info = self.verify_account(
            credentials,
            connection.external_account_id,
            connection.external_business_id,
        )
        self.subscribe_webhooks(credentials, connection.external_business_id)
        return info

    def disconnect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> None:
        """Unsubscribe our app from the linked Page's webhooks."""
        if not connection.external_business_id:
            return
        with self._client() as client:
            self._call(
                lambda: client.request(
                    "DELETE", f"{connection.external_business_id}/subscribed_apps",
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
            "Instagram Page tokens cannot be refreshed here. "
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
            raise ProviderVerificationError("Channel has no Instagram account id.")
        return self.account_info(
            credentials,
            connection.external_account_id,
            connection.external_business_id,
        )
