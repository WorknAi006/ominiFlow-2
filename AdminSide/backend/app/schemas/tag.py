from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Hex colour like #176b59 or #176b59ff.
COLOR_PATTERN = r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$"


class TagResponse(BaseModel):
    id: UUID
    name: str
    color: str
    contact_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#176b59", pattern=COLOR_PATTERN)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContactTagsUpdate(BaseModel):
    """Replace the full set of tags on a single contact."""

    tag_ids: list[UUID] = Field(default_factory=list, max_length=100)

    model_config = ConfigDict(extra="forbid")


class BulkTagRequest(BaseModel):
    """Add and/or remove tags across several contacts."""

    contact_ids: list[UUID] = Field(min_length=1, max_length=500)
    add_tag_ids: list[UUID] = Field(default_factory=list, max_length=100)
    remove_tag_ids: list[UUID] = Field(default_factory=list, max_length=100)

    model_config = ConfigDict(extra="forbid")


class BulkDeleteRequest(BaseModel):
    contact_ids: list[UUID] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")


class DeleteAllRequest(BaseModel):
    # High-risk: the client must echo this exact phrase.
    confirm: str = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")
