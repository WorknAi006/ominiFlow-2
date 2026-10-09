import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class KeywordBase(BaseModel):
    keyword_text: str = Field(..., max_length=255)
    match_type: str = Field("exact", description="One of: exact, contains, starts_with")
    is_active: bool = True
    flow_id: uuid.UUID | None = None
    reply_text: str | None = None

class KeywordCreate(KeywordBase):
    pass

class KeywordUpdate(BaseModel):
    keyword_text: str | None = Field(None, max_length=255)
    match_type: str | None = None
    is_active: bool | None = None
    flow_id: uuid.UUID | None = None
    reply_text: str | None = None

class KeywordResponse(KeywordBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by_user_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
