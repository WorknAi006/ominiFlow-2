"""
Parse WhatsApp Cloud API inbound message objects (as stored in
whatsapp_events.payload["message"]) into provider-neutral inbox content.

Only real payload fields are used; nothing is invented for unsupported
types. Media is referenced by its WhatsApp media id; downloading media
requires the channel token and is done later by a separate step.
"""
from dataclasses import dataclass, field
from typing import Any

from app.models import MessageType

MEDIA_TYPES = {
    "image": MessageType.IMAGE,
    "video": MessageType.VIDEO,
    "audio": MessageType.AUDIO,
    "document": MessageType.DOCUMENT,
}

MEDIA_FIELDS = ("id", "mime_type", "sha256", "filename", "voice")
LOCATION_FIELDS = ("latitude", "longitude", "name", "address", "url")


@dataclass(frozen=True)
class InboundContent:
    message_type: MessageType
    text: str | None = None
    media_type: str | None = None
    media_metadata: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = field(default=None)


def _pick(source: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in keys if source.get(key) is not None}


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def parse_inbound_message(message: dict[str, Any]) -> InboundContent:
    whatsapp_type = message.get("type")

    if whatsapp_type == "text":
        body = message.get("text")
        return InboundContent(
            message_type=MessageType.TEXT,
            text=_str_or_none(body.get("body")) if isinstance(body, dict) else None,
        )

    if whatsapp_type in MEDIA_TYPES:
        media = message.get(whatsapp_type)
        media = media if isinstance(media, dict) else {}
        return InboundContent(
            message_type=MEDIA_TYPES[whatsapp_type],
            text=_str_or_none(media.get("caption")),
            media_type=_str_or_none(media.get("mime_type")),
            media_metadata=_pick(media, MEDIA_FIELDS) or None,
        )

    if whatsapp_type == "location":
        return InboundContent(
            message_type=MessageType.LOCATION,
            metadata={"location": _pick(message.get("location"), LOCATION_FIELDS)},
        )

    # Unsupported (sticker, contacts, button, interactive replies, ...):
    # keep the provider type, invent no content.
    return InboundContent(
        message_type=MessageType.UNKNOWN,
        metadata={
            "unsupported": True,
            "whatsapp_type": _str_or_none(whatsapp_type) or "unknown",
        },
    )


def reply_context_id(message: dict[str, Any]) -> str | None:
    context = message.get("context")
    return _str_or_none(context.get("id")) if isinstance(context, dict) else None


def profile_name(contact: Any) -> str | None:
    if not isinstance(contact, dict):
        return None
    profile = contact.get("profile")
    name = profile.get("name") if isinstance(profile, dict) else None
    return name[:150] if isinstance(name, str) and name else None
