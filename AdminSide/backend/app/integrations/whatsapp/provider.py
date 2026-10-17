"""
WhatsApp Cloud API provider.

Mapping onto ChannelConnection:
- external_account_id  -> phone_number_id
- external_business_id -> WhatsApp Business Account (WABA) id
- access_token         -> system user / business integration token

Verification performed before a channel is marked connected:
1. debug_token: token is valid, issued for OUR Meta app, not expired, and
   has the WhatsApp scopes. If granular scopes list target ids, the WABA
   must be among them.
2. The WABA is readable with the token.
3. The phone number is listed under that WABA.
"""
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.core.phone import InvalidPhoneNumberError, normalize_phone, to_whatsapp_id
from app.integrations.whatsapp.messages import (
    parse_inbound_message,
    profile_name,
    reply_context_id,
)
from app.integrations.base import (
    NormalizedInboundEvent,
    ChannelProvider,
    ProviderAccountInfo,
    ProviderCredentials,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderPayloadTooLargeError,
    ProviderRequestError,
    ProviderUnavailableError,
    ProviderVerificationError,
)
from app.integrations.meta.graph_client import (
    MetaGraphClient,
    MetaGraphError,
    MetaGraphUnavailableError,
    MetaPayloadTooLargeError,
    build_graph_client,
    is_meta_configured,
)
from app.models import ChannelConnection, ChannelType

REQUIRED_SCOPES = frozenset({
    "whatsapp_business_management",
    "whatsapp_business_messaging",
})

PHONE_NUMBER_FIELDS = "id,display_phone_number,verified_name,quality_rating"

TEMPLATE_FIELDS = (
    "id,name,language,status,category,components,"
    "parameter_format,quality_score,rejected_reason"
)


class WhatsAppProvider(ChannelProvider):

    channel_type = ChannelType.WHATSAPP
    display_name = "WhatsApp"

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
                "WhatsApp integration is not configured."
            )
        return self.client_factory()

    def _call(self, fn: Callable[[], Any], failure: str) -> Any:
        try:
            return fn()
        except MetaGraphUnavailableError:
            raise ProviderUnavailableError(
                "Could not reach WhatsApp. Please try again later."
            ) from None
        except MetaGraphError as exc:
            raise ProviderVerificationError(f"{failure} {exc}".strip()) from None

    @staticmethod
    def _expiry(value: Any) -> datetime | None:
        # Meta uses 0 for tokens that never expire.
        if not isinstance(value, int) or value <= 0:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc)

    # ---------- WhatsApp-specific operations ----------

    def exchange_code(self, code: str) -> ProviderCredentials:
        """Embedded Signup: exchange the authorization code for a token."""
        with self._client() as client:
            body = self._call(
                lambda: client.exchange_code(code),
                "Authorization code could not be exchanged.",
            )

        token = body.get("access_token")
        if not isinstance(token, str) or not token:
            raise ProviderVerificationError(
                "Authorization code could not be exchanged."
            )

        return ProviderCredentials(access_token=token)

    def inspect_token(
        self,
        client: MetaGraphClient,
        credentials: ProviderCredentials,
        waba_id: str | None = None,
    ) -> ProviderCredentials:
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

        if waba_id is not None:
            for granular in data.get("granular_scopes") or []:
                if not isinstance(granular, dict):
                    continue
                targets = granular.get("target_ids")
                if granular.get("scope") in REQUIRED_SCOPES and targets:
                    if waba_id not in {str(target) for target in targets}:
                        raise ProviderVerificationError(
                            "Access token does not grant access to this "
                            "WhatsApp Business Account."
                        )

        expires_at = self._expiry(data.get("expires_at"))
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            raise ProviderVerificationError("Access token is invalid or expired.")

        return ProviderCredentials(
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
        )

    def verify_account(
        self,
        credentials: ProviderCredentials,
        phone_number_id: str,
        waba_id: str,
    ) -> tuple[ProviderAccountInfo, ProviderCredentials]:
        """
        Verify token validity, WABA access and phone number ownership.
        Returns the account info and credentials annotated with expiry.
        """

        with self._client() as client:
            verified = self.inspect_token(client, credentials, waba_id)
            token = verified.access_token

            waba = self._call(
                lambda: client.request(
                    "GET", waba_id,
                    access_token=token, params={"fields": "id,name"},
                ),
                "WhatsApp Business Account could not be verified.",
            )
            if str(waba.get("id")) != waba_id:
                raise ProviderVerificationError(
                    "WhatsApp Business Account could not be verified."
                )

            numbers = self._call(
                lambda: client.request(
                    "GET", f"{waba_id}/phone_numbers",
                    access_token=token,
                    params={"fields": PHONE_NUMBER_FIELDS, "limit": 100},
                ),
                "Phone numbers could not be loaded.",
            )

        phone = next(
            (
                item for item in numbers.get("data") or []
                if isinstance(item, dict) and str(item.get("id")) == phone_number_id
            ),
            None,
        )
        if phone is None:
            raise ProviderVerificationError(
                "Phone number does not belong to this WhatsApp Business Account."
            )

        info = ProviderAccountInfo(
            external_account_id=phone_number_id,
            external_business_id=waba_id,
            display_name=phone.get("verified_name"),
            metadata={
                "display_phone_number": phone.get("display_phone_number"),
                "verified_name": phone.get("verified_name"),
                "quality_rating": phone.get("quality_rating"),
                "waba_name": waba.get("name"),
            },
        )

        return info, verified

    def subscribe_webhooks(
        self,
        credentials: ProviderCredentials,
        waba_id: str,
    ) -> None:
        """Subscribe our app to the WABA so its webhooks reach us."""
        with self._client() as client:
            body = self._call(
                lambda: client.request(
                    "POST", f"{waba_id}/subscribed_apps",
                    access_token=credentials.access_token,
                ),
                "Webhook subscription failed.",
            )

        if body.get("success") is not True:
            raise ProviderVerificationError("Webhook subscription failed.")

    def is_webhook_subscribed(
        self,
        credentials: ProviderCredentials,
        waba_id: str,
    ) -> bool:
        """
        Report whether our app is in the WABA's subscribed_apps list, i.e.
        whether this account's webhooks reach us. Read-only diagnostic.
        """
        with self._client() as client:
            body = self._call(
                lambda: client.request(
                    "GET", f"{waba_id}/subscribed_apps",
                    access_token=credentials.access_token,
                ),
                "Webhook subscription could not be read.",
            )
            app_id = client.app_id

        for entry in body.get("data") or []:
            if not isinstance(entry, dict):
                continue
            data = entry.get("whatsapp_business_api_data")
            candidate = data.get("id") if isinstance(data, dict) else entry.get("id")
            if candidate is not None and str(candidate) == app_id:
                return True
        return False

    def send_text_message(
        self,
        credentials: ProviderCredentials,
        phone_number_id: str,
        to: str,
        text: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        """
        Send a free-form text message. Returns the WhatsApp message id.
        Raises ProviderRequestError when Meta rejects the message (e.g.
        outside the 24h customer service window) and
        ProviderUnavailableError when Meta cannot be reached.
        """

        return self._send_message(
            credentials,
            phone_number_id,
            {"type": "text", "text": {"preview_url": False, "body": text}},
            to,
            reply_to_external_id,
        )

    # ---------- generic outbound contract (ChannelProvider) ----------

    def recipient_for(self, connection: ChannelConnection, contact: Any) -> str:
        """
        WhatsApp recipient id (digits only) derived from the contact's
        WhatsApp identifier or phone number. Raises ValueError when no
        valid number is available; the block check stays in the service.
        """
        candidate = (
            getattr(contact, "external_identifier", None)
            or getattr(contact, "normalized_phone_number", None)
        )
        if not candidate:
            raise ValueError("This contact has no WhatsApp number.")
        try:
            return to_whatsapp_id(normalize_phone(candidate))
        except InvalidPhoneNumberError:
            raise ValueError("This contact has no valid WhatsApp number.") from None

    def send_text(
        self,
        credentials: ProviderCredentials,
        connection: ChannelConnection,
        recipient: str,
        text: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        """Generic text send; delegates to the WhatsApp Cloud API call."""
        if not connection.external_account_id:
            raise ProviderVerificationError("Channel has no phone_number_id.")
        return self.send_text_message(
            credentials,
            connection.external_account_id,
            recipient,
            text,
            reply_to_external_id,
        )

    def normalize_inbound_message(
        self,
        connection: ChannelConnection,
        raw: dict[str, Any],
    ) -> NormalizedInboundEvent | None:
        """
        Normalize a stored WhatsApp event into the common inbound event.
        `raw` carries the event payload and the routing-derived ids/time:
        {"payload", "external_message_id", "external_sender_id",
         "external_event_id", "occurred_at"}. Returns None for malformed
        events or ones missing a message id or sender (ignored upstream).
        """
        payload = raw.get("payload") if isinstance(raw, dict) else None
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict):
            return None

        external_message_id = raw.get("external_message_id") or message.get("id")
        external_sender_id = raw.get("external_sender_id") or message.get("from")
        if not external_message_id or not external_sender_id:
            return None

        content = parse_inbound_message(message)

        return NormalizedInboundEvent(
            tenant_id=connection.tenant_id,
            channel_connection_id=connection.id,
            channel_type=ChannelType.WHATSAPP.value,
            external_message_id=str(external_message_id),
            external_sender_id=str(external_sender_id),
            # A WhatsApp wa_id is the customer's phone number, so it also
            # drives the existing phone-based contact dedup.
            phone_hint=str(external_sender_id),
            sender_display_name=profile_name(payload.get("contact")),
            message_type=content.message_type,
            text=content.text,
            media_type=content.media_type,
            media_metadata=content.media_metadata,
            reply_to_external_id=reply_context_id(message),
            occurred_at=raw.get("occurred_at"),
            external_event_id=raw.get("external_event_id"),
            metadata=content.metadata,
        )

    def send_template_message(
        self,
        credentials: ProviderCredentials,
        phone_number_id: str,
        to: str,
        template_name: str,
        language: str,
        components: list[dict[str, Any]],
    ) -> str:
        """
        Send an approved template (allowed outside the 24h window; Meta is
        the authority on eligibility). Returns the WhatsApp message id.
        """

        template: dict[str, Any] = {"name": template_name, "language": {"code": language}}
        if components:
            template["components"] = components

        return self._send_message(
            credentials, phone_number_id, {"type": "template", "template": template}, to,
        )

    def _send_message(
        self,
        credentials: ProviderCredentials,
        phone_number_id: str,
        content: dict[str, Any],
        to: str,
        reply_to_external_id: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            **content,
        }
        if reply_to_external_id:
            payload["context"] = {"message_id": reply_to_external_id}

        with self._client() as client:
            body = self._graph(
                lambda: client.request(
                    "POST", f"{phone_number_id}/messages",
                    access_token=credentials.access_token,
                    json=payload,
                )
            )

        messages = body.get("messages")
        message_id = (
            messages[0].get("id")
            if isinstance(messages, list) and messages and isinstance(messages[0], dict)
            else None
        )
        if not isinstance(message_id, str) or not message_id:
            raise ProviderRequestError("WhatsApp did not return a message id.")

        return message_id

    @staticmethod
    def _graph(fn: Callable[[], Any]) -> Any:
        """Map Graph errors to request (permanent) / unavailable (transient)."""
        try:
            return fn()
        except MetaPayloadTooLargeError as exc:
            raise ProviderPayloadTooLargeError(str(exc)) from None
        except MetaGraphUnavailableError:
            raise ProviderUnavailableError(
                "Could not reach WhatsApp. Please try again later."
            ) from None
        except MetaGraphError as exc:
            raise ProviderRequestError(
                str(exc),
                code=str(exc.code) if exc.code is not None else None,
            ) from None

    # ---------- media ----------

    def get_media_info(
        self,
        credentials: ProviderCredentials,
        media_id: str,
        phone_number_id: str,
    ) -> dict[str, Any]:
        """
        Resolve a media id to its short-lived download URL and metadata.
        phone_number_id makes Meta verify the media belongs to this number.
        """
        with self._client() as client:
            return self._graph(
                lambda: client.request(
                    "GET", media_id,
                    access_token=credentials.access_token,
                    params={"phone_number_id": phone_number_id},
                )
            )

    def download_media(
        self,
        credentials: ProviderCredentials,
        url: str,
        max_bytes: int,
        timeout: float,
    ) -> tuple[bytes, str | None]:
        with self._client() as client:
            return self._graph(
                lambda: client.download(
                    url,
                    access_token=credentials.access_token,
                    max_bytes=max_bytes,
                    timeout=timeout,
                )
            )

    # ---------- templates ----------

    def list_templates(
        self,
        credentials: ProviderCredentials,
        waba_id: str,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Fetch all message templates of a WABA, following paging cursors
        (never arbitrary "next" URLs).
        """

        templates: list[dict[str, Any]] = []
        after: str | None = None

        with self._client() as client:
            for _ in range(max_pages):
                params: dict[str, Any] = {"fields": TEMPLATE_FIELDS, "limit": 100}
                if after:
                    params["after"] = after

                body = self._graph(
                    lambda: client.request(
                        "GET", f"{waba_id}/message_templates",
                        access_token=credentials.access_token,
                        params=params,
                    )
                )

                data = body.get("data")
                if not isinstance(data, list):
                    raise ProviderRequestError("Unexpected template response from WhatsApp.")
                templates.extend(item for item in data if isinstance(item, dict))

                paging = body.get("paging") if isinstance(body.get("paging"), dict) else {}
                cursors = paging.get("cursors") if isinstance(paging.get("cursors"), dict) else {}
                after = cursors.get("after") if paging.get("next") else None
                if not isinstance(after, str) or not after:
                    break

        return templates

    # ---------- ChannelProvider interface ----------

    def connect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> ProviderAccountInfo:
        if not connection.external_account_id or not connection.external_business_id:
            raise ProviderVerificationError(
                "phone_number_id and WhatsApp Business Account id are required."
            )

        info, verified = self.verify_account(
            credentials,
            connection.external_account_id,
            connection.external_business_id,
        )
        self.subscribe_webhooks(verified, connection.external_business_id)
        return info

    def disconnect(
        self,
        connection: ChannelConnection,
        credentials: ProviderCredentials,
    ) -> None:
        """
        Unsubscribe our app from the WABA. Note: the subscription covers
        every phone number in the WABA, so callers must only use this when
        no other connected channel shares the WABA.
        """
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
            "WhatsApp Cloud API tokens cannot be refreshed. "
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
            raise ProviderVerificationError("Channel has no phone_number_id.")

        with self._client() as client:
            phone = self._call(
                lambda: client.request(
                    "GET", connection.external_account_id,
                    access_token=credentials.access_token,
                    params={"fields": PHONE_NUMBER_FIELDS},
                ),
                "Phone number could not be loaded.",
            )

        return ProviderAccountInfo(
            external_account_id=str(phone.get("id")),
            external_business_id=connection.external_business_id,
            display_name=phone.get("verified_name"),
            metadata={
                "display_phone_number": phone.get("display_phone_number"),
                "verified_name": phone.get("verified_name"),
                "quality_rating": phone.get("quality_rating"),
            },
        )
