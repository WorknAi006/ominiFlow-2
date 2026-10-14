import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import CurrentTenant, CurrentUser, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.automation import (
    AutomationCreate, AutomationListResponse, AutomationMetrics, AutomationOptions,
    AutomationResponse, AutomationRunListResponse, AutomationUpdate,
)
from app.services import automation_service
from app.services.automation_service import AutomationNotFoundError

router = APIRouter(prefix="/automations", tags=["Automations"])
ERRORS = {AutomationNotFoundError: status.HTTP_404_NOT_FOUND}


@router.get("", response_model=AutomationListResponse, dependencies=[Depends(require_permission("automation:read"))])
def list_automations(tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), search: str | None = Query(None, max_length=100)):
    return automation_service.list_automations(db, tenant.id, page, page_size, (search or "").strip() or None)


@router.post("", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("automation:create"))])
def create_automation(data: AutomationCreate, user: CurrentUser, tenant: CurrentTenant, db: DbSession):
    return automation_service.create_automation(db, tenant.id, user, data)


@router.get("/options", response_model=AutomationOptions, dependencies=[Depends(require_permission("automation:read"))])
def automation_options():
    return automation_service.options()


@router.get("/metrics", response_model=AutomationMetrics, dependencies=[Depends(require_permission("automation:read"))])
def automation_metrics(tenant: CurrentTenant, db: DbSession):
    return automation_service.metrics(db, tenant.id)


@router.get("/runs", response_model=AutomationRunListResponse, dependencies=[Depends(require_permission("automation:read"))])
def list_all_runs(tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return automation_service.list_runs(db, tenant.id, None, page, page_size)


@router.get("/{automation_id}", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:read"))])
def get_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.get_automation(db, tenant.id, automation_id)


@router.patch("/{automation_id}", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:update"))])
def update_automation(automation_id: uuid.UUID, data: AutomationUpdate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.update_automation(db, tenant.id, automation_id, data)


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("automation:delete"))])
def delete_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        automation_service.delete_automation(db, tenant.id, automation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{automation_id}/activate", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:publish"))])
def activate_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.set_active(db, tenant.id, automation_id, True)


@router.post("/{automation_id}/pause", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:publish"))])
def pause_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.set_active(db, tenant.id, automation_id, False)


@router.get("/{automation_id}/runs", response_model=AutomationRunListResponse, dependencies=[Depends(require_permission("automation:read"))])
def list_automation_runs(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with service_errors(ERRORS):
        automation_service.get_automation(db, tenant.id, automation_id)
        return automation_service.list_runs(db, tenant.id, automation_id, page, page_size)
