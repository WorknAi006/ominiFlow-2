"""
Phone number normalization to E.164 ("+" followed by 8-15 digits).

WhatsApp wa_ids are E.164 without the "+", so "15551234567",
"+1 (555) 123-4567" and "0015551234567" all normalize to "+15551234567".
Numbers must be in international format; national formats without a
country code cannot be normalized reliably and are rejected.
"""
import re

_SEPARATORS = re.compile(r"[\s().\-/]")
_DIGITS = re.compile(r"^[1-9][0-9]{7,14}$")


class InvalidPhoneNumberError(ValueError):
    """Raised when a phone number cannot be normalized."""


def normalize_phone(value: str) -> str:
    raw = _SEPARATORS.sub("", value or "")

    if raw.startswith("+"):
        digits = raw[1:]
    elif raw.startswith("00"):
        digits = raw[2:]
    else:
        digits = raw

    if not _DIGITS.match(digits):
        raise InvalidPhoneNumberError(
            "Phone number must be in international format, e.g. +15551234567."
        )

    return f"+{digits}"


def to_whatsapp_id(normalized_phone: str) -> str:
    """E.164 to the WhatsApp recipient format (digits only)."""
    return normalized_phone.lstrip("+")
