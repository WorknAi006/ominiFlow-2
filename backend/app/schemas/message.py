from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import MessageDirection, MessageStatus, MessageType
from app.schemas.template import (
    LANGUAGE_PATTERN,
    TEMPLATE_NAME_PATTERN,
    TemplateComponentInput,
)

# WhatsApp Cloud API limit for text message bodies.
MAX_TEXT_LENGTH = 4096


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    contact_id: UUID
    channel_connection_id: UUID
    direction: MessageDirection
    message_type: MessageType
    status: MessageStatus
    external_message_id: str | None
    text: str | None
    # Authenticated Omniflow endpoint once media is downloaded; never a
    # provider URL.
    media_url: str | None
    media_type: str | None
    media_metadata: dict[str, Any] | None
    metadata: dict[str, Any] | None
    reply_to_message_id: UUID | None
    sent_by_user_id: UUID | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int


class TextMessageCreate(BaseModel):
    type: Literal["text"]
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    reply_to_message_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text cannot be blank.")
        return value


class TemplateMessageCreate(BaseModel):
    """
    Send an approved WhatsApp template (usable outside the 24h customer
    service window; Meta decides eligibility).
    """

    type: Literal["template"]
    template_name: str = Field(pattern=TEMPLATE_NAME_PATTERN)
    language: str = Field(pattern=LANGUAGE_PATTERN)
    components: list[TemplateComponentInput] = Field(default_factory=list, max_length=10)

    model_config = ConfigDict(extra="forbid")


# ---- Interactive (buttons with header/footer) and media messages ----------
# Used by the flow engine. WhatsApp Cloud API limits are enforced here and in
# the provider; existing text/template sending is unaffected.
MAX_BODY_LENGTH = 1024
MAX_FOOTER_LENGTH = 60
MAX_HEADER_TEXT_LENGTH = 60
MAX_BUTTON_TITLE_LENGTH = 20


class InteractiveHeader(BaseModel):
    """Optional header for an interactive message: text or a media object."""

    type: Literal["text", "image", "video", "document"]
    text: str | None = Field(default=None, max_length=MAX_HEADER_TEXT_LENGTH)
    # Storage key of a flow-uploaded asset (image/video/document headers).
    media_key: str | None = None
    media_url: str | None = None
    filename: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class InteractiveButton(BaseModel):
    """A single button. `reply` = tappable quick reply (drives a branch);
    `url` = open a link; `call` = phone number."""

    id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=MAX_BUTTON_TITLE_LENGTH)
    kind: Literal["reply", "url", "call"] = "reply"
    url: str | None = Field(default=None, max_length=2000)
    phone_number: str | None = Field(default=None, max_length=32)

    model_config = ConfigDict(extra="forbid")


class InteractiveListItem(BaseModel):
    """A row in a WhatsApp interactive list message."""

    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=24)
    description: str | None = Field(default=None, max_length=72)

    model_config = ConfigDict(extra="forbid")


class InteractiveMessageCreate(BaseModel):
    type: Literal["interactive"]
    body: str = Field(min_length=1, max_length=MAX_BODY_LENGTH)
    header: InteractiveHeader | None = None
    footer: str | None = Field(default=None, max_length=MAX_FOOTER_LENGTH)
    buttons: list[InteractiveButton] = Field(default_factory=list, max_length=10)
    interactive_type: Literal["button", "list"] = "button"
    button_text: str | None = Field(default=None, max_length=20)
    list_items: list[InteractiveListItem] = Field(default_factory=list, max_length=10)

    model_config = ConfigDict(extra="forbid")


class MediaMessageCreate(BaseModel):
    type: Literal["media"]
    media_type: Literal["image", "video", "audio", "document"]
    # Storage key of a flow-uploaded asset OR public URL.
    media_key: str | None = None
    media_url: str | None = None
    caption: str | None = Field(default=None, max_length=MAX_BODY_LENGTH)
    filename: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


MessageCreate = Annotated[
    TextMessageCreate | TemplateMessageCreate | InteractiveMessageCreate | MediaMessageCreate,
    Field(discriminator="type"),
]
