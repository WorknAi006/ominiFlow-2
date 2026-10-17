"""
Meta webhook security helpers (shared by WhatsApp, Instagram, Facebook).
"""
import hashlib
import hmac
import re

SIGNATURE_PREFIX = "sha256="

# Meta sends a numeric challenge; anything else is rejected rather than
# reflected back.
_CHALLENGE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


def verify_signature(
    app_secret: str,
    raw_body: bytes,
    signature_header: str | None,
) -> bool:
    """
    Validate X-Hub-Signature-256: "sha256=" + hex HMAC-SHA256 of the raw
    request body keyed with the app secret. Constant-time comparison.
    """

    if not app_secret or not signature_header:
        return False

    if not signature_header.startswith(SIGNATURE_PREFIX):
        return False

    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[len(SIGNATURE_PREFIX):].strip().lower()

    return hmac.compare_digest(expected, received)


def verify_subscription(
    expected_verify_token: str,
    mode: str | None,
    verify_token: str | None,
    challenge: str | None,
) -> bool:
    """
    Validate the GET subscription handshake (hub.mode / hub.verify_token
    / hub.challenge). Fails closed when no verify token is configured.
    """

    if not expected_verify_token or mode != "subscribe":
        return False

    if not verify_token or not challenge:
        return False

    if not _CHALLENGE_PATTERN.match(challenge):
        return False

    return hmac.compare_digest(
        expected_verify_token.encode("utf-8"),
        verify_token.encode("utf-8"),
    )
