import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MatchType = Literal["exact", "contains", "starts_with", "ends_with"]


class KeywordBase(BaseModel):
    keyword_text: str = Field(..., min_length=1, max_length=255)
    match_type: MatchType = "exact"
    is_active: bool = True
    flow_id: uuid.UUID | None = None
    reply_text: str | None = Field(default=None, max_length=4096)
    model_config = ConfigDict(str_strip_whitespace=True)


class KeywordCreate(KeywordBase):
    pass


class KeywordUpdate(BaseModel):
    keyword_text: str | None = Field(None, min_length=1, max_length=255)
    match_type: MatchType | None = None
    is_active: bool | None = None
    flow_id: uuid.UUID | None = None
    reply_text: str | None = Field(default=None, max_length=4096)
    model_config = ConfigDict(str_strip_whitespace=True)


class KeywordResponse(KeywordBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    flow_name: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
