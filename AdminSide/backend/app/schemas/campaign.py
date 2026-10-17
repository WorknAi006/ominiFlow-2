import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus

class CampaignBase(BaseModel):
    name: str = Field(..., max_length=255)
    channel_connection_id: uuid.UUID
    message_template_id: Optional[uuid.UUID] = None
    text_content: Optional[str] = None
    template_params: Optional[List[Dict[str, Any]]] = None
    audience_config: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    channel_connection_id: Optional[uuid.UUID] = None
    message_template_id: Optional[uuid.UUID] = None
    text_content: Optional[str] = None
    template_params: Optional[List[Dict[str, Any]]] = None
    audience_config: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[CampaignStatus] = None

class CampaignRead(CampaignBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: CampaignStatus
    total_recipients: int
    delivered_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CampaignListResponse(BaseModel):
    items: List[CampaignRead]
    total: int

class AudiencePreviewRequest(BaseModel):
    audience_config: Dict[str, Any]

class AudiencePreviewResponse(BaseModel):
    total_contacts: int
