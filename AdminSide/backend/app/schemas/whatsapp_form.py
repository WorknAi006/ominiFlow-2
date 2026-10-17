from datetime import datetime
from pydantic import BaseModel, Field

class WhatsAppFormBase(BaseModel):
    name: str = Field(..., max_length=255)
    category: str | None = None

class WhatsAppFormCreate(WhatsAppFormBase):
    config: dict | None = None

class WhatsAppFormUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    category: str | None = None
    status: str | None = None
    config: dict | None = None

class WhatsAppFormResponse(WhatsAppFormBase):
    id: str
    status: str
    config: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WhatsAppFormListResponse(BaseModel):
    items: list[WhatsAppFormResponse]
    total: int
    page: int
    size: int
