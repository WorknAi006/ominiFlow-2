from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.flow import FlowStatus

VALID_CHANNELS = ("omnichannel", "whatsapp", "instagram", "messenger")


class FlowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    channels: list[str] = Field(default_factory=list, max_length=4)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("channels")
    @classmethod
    def valid_channels(cls, v: list[str]) -> list[str]:
        cleaned = [c.lower() for c in v if c.lower() in VALID_CHANNELS]
        return list(dict.fromkeys(cleaned))  # de-duplicate, keep order


class FlowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    status: FlowStatus | None = None
    channels: list[str] | None = Field(default=None, max_length=4)
    nodes: list[dict[str, Any]] | None = Field(default=None, max_length=500)
    edges: list[dict[str, Any]] | None = Field(default=None, max_length=1000)
    model_config = ConfigDict(extra="forbid")

    @field_validator("channels")
    @classmethod
    def valid_channels(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [c.lower() for c in v if c.lower() in VALID_CHANNELS]
        return list(dict.fromkeys(cleaned))


class FlowResponse(BaseModel):
    id: UUID
    name: str
    status: FlowStatus
    channels: list[str]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FlowSummary(BaseModel):
    """List-row shape (omits the heavy nodes/edges payload)."""

    id: UUID
    name: str
    status: FlowStatus
    channels: list[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FlowListResponse(BaseModel):
    items: list[FlowSummary]
    total: int


class FlowUploadResponse(BaseModel):
    key: str
    url: str
    filename: str
    content_type: str
    size: int
