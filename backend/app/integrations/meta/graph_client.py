"""
Minimal synchronous client for the Meta Graph API, shared by the
WhatsApp, Instagram and Facebook providers.

Security:
- User access tokens are sent in the Authorization header, never in the
  URL path, and every user-token call carries an appsecret_proof.
- httpx request logging is raised to WARNING because it logs full URLs,
  and a few Graph endpoints (debug_token, oauth/access_token) require
  secrets as query parameters.
- Error messages are sanitized: any secret used in the request is
  redacted, and transport exceptions are not chained (their text can
  include request URLs).
"""
import hashlib
import hmac
import logging
from collections.abc import Iterable
from typing import Any

import httpx

from app.core.config import settings

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

MAX_ERROR_MESSAGE_LENGTH = 300


class MetaGraphError(Exception):
    """Graph API returned an error. Message is sanitized."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class MetaGraphUnavailableError(MetaGraphError):
    """Network failure, timeout or 5xx from the Graph API."""


class MetaPayloadTooLargeError(MetaGraphError):
    """A media download exceeded the allowed size."""


# Hosts Meta serves WhatsApp media from. The access token is only ever
# sent to these hosts, so a URL from any other host is refused.
MEDIA_HOST_SUFFIXES = ("fbsbx.com", "fbcdn.net", "facebook.com", "whatsapp.net")


def is_trusted_media_url(url: str) -> bool:
    try:
        parsed = httpx.URL(url)
    except (httpx.InvalidURL, TypeError):
        return False

    host = (parsed.host or "").lower()
    return (
        parsed.scheme == "https"
        and not parsed.userinfo
        and parsed.port in (None, 443)
        and any(host == suffix or host.endswith(f".{suffix}") for suffix in MEDIA_HOST_SUFFIXES)
    )


def sanitize(message: str, secrets: Iterable[str | None]) -> str:
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")

    return message[:MAX_ERROR_MESSAGE_LENGTH]


def appsecret_proof(app_secret: str, access_token: str) -> str:
    return hmac.new(
        app_secret.encode("utf-8"),
        access_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class MetaGraphClient:

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        base_url: str,
        api_version: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.app_id = app_id
        self._app_secret = app_secret
        self._base = f"{base_url.rstrip('/')}/{api_version}"
        self._http = httpx.Client(
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> "MetaGraphClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    @property
    def _app_access_token(self) -> str:
        return f"{self.app_id}|{self._app_secret}"

    def request(
        self,
        method: str,
        path: str,
        *,
        access_token: str | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        with_proof: bool = True,
        secrets: Iterable[str | None] = (),
    ) -> dict[str, Any]:
        query = dict(params or {})
        headers = {"Accept": "application/json"}

        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            if with_proof:
                query["appsecret_proof"] = appsecret_proof(
                    self._app_secret, access_token,
                )

        all_secrets = [access_token, self._app_secret, *secrets]

        try:
            response = self._http.request(
                method,
                f"{self._base}/{path.lstrip('/')}",
                params=query,
                data=data,
                json=json,
                files=files,
                headers=headers,
            )
        except httpx.HTTPError:
            raise MetaGraphUnavailableError(
                "Could not reach the Meta Graph API."
            ) from None

        try:
            body = response.json()
        except ValueError:
            body = None

        if response.status_code >= 500:
            raise MetaGraphUnavailableError(
                "The Meta Graph API is temporarily unavailable.",
                status_code=response.status_code,
            )

        error = body.get("error") if isinstance(body, dict) else None

        if response.status_code >= 400 or error:
            error = error if isinstance(error, dict) else {}
            raise MetaGraphError(
                sanitize(
                    str(error.get("message") or "Meta Graph API request failed."),
                    all_secrets,
                ),
                status_code=response.status_code,
                code=error.get("code"),
            )

        if not isinstance(body, dict):
            raise MetaGraphError(
                "Unexpected response from the Meta Graph API.",
                status_code=response.status_code,
            )

        return body

    def debug_token(self, input_token: str) -> dict[str, Any]:
        body = self.request(
            "GET",
            "debug_token",
            access_token=self._app_access_token,
            params={"input_token": input_token},
            with_proof=False,
            secrets=(input_token,),
        )
        data = body.get("data")
        return data if isinstance(data, dict) else {}

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange an Embedded Signup authorization code for a token."""
        return self.request(
            "GET",
            "oauth/access_token",
            params={
                "client_id": self.app_id,
                "client_secret": self._app_secret,
                "code": code,
            },
            secrets=(code,),
        )

    def oauth_exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """
        Exchange a Facebook Login authorization code (from the OAuth dialog)
        for a user access token. redirect_uri must match the one used to
        start the dialog. The app secret is sent as a query parameter, never
        from the browser.
        """
        return self.request(
            "GET",
            "oauth/access_token",
            params={
                "client_id": self.app_id,
                "client_secret": self._app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            with_proof=False,
            secrets=(code,),
        )

    def long_lived_user_token(self, user_token: str) -> dict[str, Any]:
        """Exchange a short-lived user token for a long-lived one."""
        return self.request(
            "GET",
            "oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self._app_secret,
                "fb_exchange_token": user_token,
            },
            with_proof=False,
            secrets=(user_token,),
        )

    def list_managed_pages(self, user_token: str, fields: str) -> dict[str, Any]:
        """List the Pages a user manages (GET /me/accounts), with the given
        fields (e.g. id,name,access_token,instagram_business_account{...})."""
        return self.request(
            "GET",
            "me/accounts",
            access_token=user_token,
            params={"fields": fields, "limit": 100},
        )

    def download(
        self,
        url: str,
        *,
        access_token: str,
        max_bytes: int,
        timeout: float,
    ) -> tuple[bytes, str | None]:
        """
        Download media from a URL returned by the Graph media endpoint.

        The URL must be https on a Meta media host; the token is sent only
        in the Authorization header; redirects are not followed; the body
        is streamed and aborted beyond max_bytes. Errors never include the
        URL (it carries signed parameters).
        """

        if not is_trusted_media_url(url):
            raise MetaGraphError("Untrusted media download URL.")

        try:
            with self._http.stream(
                "GET",
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=timeout,
            ) as response:
                if response.status_code >= 500:
                    raise MetaGraphUnavailableError(
                        "Media download is temporarily unavailable.",
                        status_code=response.status_code,
                    )
                if response.status_code != 200:
                    raise MetaGraphError(
                        f"Media download failed (HTTP {response.status_code}).",
                        status_code=response.status_code,
                    )

                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    raise MetaPayloadTooLargeError("Media exceeds the size limit.")

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise MetaPayloadTooLargeError("Media exceeds the size limit.")

                return bytes(body), response.headers.get("content-type")

        except httpx.HTTPError:
            raise MetaGraphUnavailableError(
                "Media download timed out or could not be completed."
            ) from None


def is_meta_configured() -> bool:
    return bool(settings.meta_app_id and settings.meta_app_secret)


def build_graph_client(
    transport: httpx.BaseTransport | None = None,
) -> MetaGraphClient:
    return MetaGraphClient(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        base_url=settings.meta_graph_api_base_url,
        api_version=settings.meta_graph_api_version,
        timeout=settings.meta_http_timeout_seconds,
        transport=transport,
    )
