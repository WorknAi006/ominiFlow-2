from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WebChatInboundRequest(BaseModel):
    """Public widget payload. tenant/channel are derived from the public
    key in the URL, never from the body."""

    visitor_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4096)
    client_message_id: str | None = Field(default=None, min_length=1, max_length=200)
    display_name: str | None = Field(default=None, min_length=1, max_length=150)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WebChatMessageOut(BaseModel):
    id: str
    direction: str
    text: str | None
    created_at: datetime


class WebChatInboundResponse(BaseModel):
    conversation_id: str
    message: WebChatMessageOut


class WebChatMessagesResponse(BaseModel):
    messages: list[WebChatMessageOut]


class WebChatConfigResponse(BaseModel):
    channel_name: str
