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


MessageCreate = Annotated[
    TextMessageCreate | TemplateMessageCreate,
    Field(discriminator="type"),
]
