import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignRead,
    CampaignListResponse,
    AudiencePreviewRequest,
    AudiencePreviewResponse
)
from app.services.campaign import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.post("/preview-audience", response_model=AudiencePreviewResponse, dependencies=[Depends(require_permission("message:read"))])
def preview_audience(
    data: AudiencePreviewRequest,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = CampaignService(db)
    count = service.get_audience_count(tenant.id, data.audience_config)
    return {"total_contacts": count}


@router.post("", response_model=CampaignRead, dependencies=[Depends(require_permission("message:create"))])
def create_campaign(
    data: CampaignCreate,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = CampaignService(db)
    try:
        return service.create_campaign(tenant.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=CampaignListResponse, dependencies=[Depends(require_permission("message:read"))])
def get_campaigns(
    tenant: CurrentTenant,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str | None = None,
) -> Any:
    service = CampaignService(db)
    campaigns, total = service.get_campaigns(tenant.id, skip, limit, search)
    return {"items": campaigns, "total": total}


@router.get("/{campaign_id}", response_model=CampaignRead, dependencies=[Depends(require_permission("message:read"))])
def get_campaign(
    campaign_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = CampaignService(db)
    campaign = service.get_campaign(tenant.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/{campaign_id}/start", response_model=CampaignRead, dependencies=[Depends(require_permission("message:create"))])
def start_campaign(
    campaign_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = CampaignService(db)
    try:
        return service.start_campaign(tenant.id, campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{campaign_id}", response_model=CampaignRead, dependencies=[Depends(require_permission("message:create"))])
def update_campaign(
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    tenant: CurrentTenant,
    db: DbSession,
) -> Any:
    service = CampaignService(db)
    try:
        campaign = service.update_campaign(tenant.id, campaign_id, data)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
