from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    ChannelType,
    ConversationStatus,
    MessageDirection,
    MessageStatus,
    MessageType,
)


class ConversationContactSummary(BaseModel):
    id: UUID
    name: str | None
    phone_number: str | None


class ConversationChannelSummary(BaseModel):
    id: UUID
    name: str
    channel_type: ChannelType


class ConversationUserSummary(BaseModel):
    id: UUID
    first_name: str
    last_name: str | None


class LastMessagePreview(BaseModel):
    id: UUID
    direction: MessageDirection
    message_type: MessageType
    status: MessageStatus
    # Truncated preview, not the full message.
    text: str | None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: UUID
    status: ConversationStatus
    subject: str | None
    unread_count: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    contact: ConversationContactSummary
    channel: ConversationChannelSummary
    assigned_user: ConversationUserSummary | None
    last_message: LastMessagePreview | None


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class ConversationUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_fields(self) -> "ConversationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class ConversationAssign(BaseModel):
    # null unassigns. The key is required so an empty body is rejected.
    assigned_user_id: UUID | None

    model_config = ConfigDict(extra="forbid")


class ConversationStatusUpdate(BaseModel):
    status: ConversationStatus

    model_config = ConfigDict(extra="forbid")
