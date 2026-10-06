import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import (
    CurrentTenant,
    DbSession,
    require_permission,
)
from app.schemas.tenant import TenantDetailResponse, TenantUpdateRequest
from app.services.tenant_service import update_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get(
    "/current",
    response_model=TenantDetailResponse,
    dependencies=[Depends(require_permission("tenant:read"))],
)
def get_tenant(
    tenant: CurrentTenant,
):
    return tenant


@router.patch(
    "/current",
    response_model=TenantDetailResponse,
    dependencies=[Depends(require_permission("tenant:update"))],
)
def patch_tenant(
    data: TenantUpdateRequest,
    tenant: CurrentTenant,
    db: DbSession,
):
    try:
        return update_tenant(db, tenant, data)

    except SQLAlchemyError:
        logger.exception("Database error while updating tenant.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )
