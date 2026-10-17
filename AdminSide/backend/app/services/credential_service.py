"""
Encryption for external channel credentials (OAuth / API tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256, authenticated) via MultiFernet
so keys can be rotated: the first configured key encrypts new values,
every configured key can decrypt existing ones.

Plaintext credentials must only ever exist in memory inside provider
integrations. They are never returned by API schemas or logged.
"""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import settings


class CredentialEncryptionError(Exception):
    """Base credential encryption error."""


class CredentialEncryptionNotConfiguredError(CredentialEncryptionError):
    """Raised when no valid encryption key is configured."""


class CredentialDecryptionError(CredentialEncryptionError):
    """Raised when a stored credential cannot be decrypted."""


class ChannelCredentialService:

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise CredentialEncryptionNotConfiguredError(
                "Channel credential encryption is not configured."
            )

        try:
            self._fernet = MultiFernet([Fernet(key) for key in keys])
        except (ValueError, TypeError):
            # Never include key material in the error.
            raise CredentialEncryptionNotConfiguredError(
                "Channel credential encryption key is invalid."
            ) from None

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken:
            raise CredentialDecryptionError(
                "Stored credential could not be decrypted."
            ) from None

    def rotate(self, ciphertext: str) -> str:
        """Re-encrypt a value with the current primary key."""
        try:
            return self._fernet.rotate(ciphertext.encode("ascii")).decode("ascii")
        except InvalidToken:
            raise CredentialDecryptionError(
                "Stored credential could not be decrypted."
            ) from None


@lru_cache
def _build_service(raw_keys: str) -> ChannelCredentialService:
    keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
    return ChannelCredentialService(keys)


def get_credential_service() -> ChannelCredentialService:
    return _build_service(settings.channel_credential_keys)
