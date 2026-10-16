from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentTenant, get_db, require_permission
from app.models import Flow, TenantRoutingConfig
from app.schemas.routing import RoutingConfigResponse, RoutingConfigUpdate

router = APIRouter(prefix="/routing-config", tags=["Routing"])


@router.get("", response_model=RoutingConfigResponse)
def get_routing_config(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    _=Depends(require_permission("tenant:update")),
):
    """Current global fallback routing for the tenant."""
    config = db.query(TenantRoutingConfig).filter(TenantRoutingConfig.tenant_id == tenant.id).first()
    if config is None:
        return RoutingConfigResponse(fallback_action="none", fallback_flow_id=None)
    return config


@router.put("", response_model=RoutingConfigResponse)
def update_routing_config(
    data: RoutingConfigUpdate,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    _=Depends(require_permission("tenant:update")),
):
    """Set the global fallback routing. When action is ``flow`` the flow must
    belong to this tenant."""
    flow_id = data.fallback_flow_id
    if data.fallback_action == "flow":
        if flow_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A flow must be selected when the fallback action is 'flow'.",
            )
        flow = db.query(Flow).filter(Flow.id == flow_id, Flow.tenant_id == tenant.id).first()
        if flow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found.")
    else:
        flow_id = None

    config = db.query(TenantRoutingConfig).filter(TenantRoutingConfig.tenant_id == tenant.id).first()
    if config is None:
        config = TenantRoutingConfig(tenant_id=tenant.id)
        db.add(config)
    config.fallback_action = data.fallback_action
    config.fallback_flow_id = flow_id
    db.commit()
    db.refresh(config)
    return config
