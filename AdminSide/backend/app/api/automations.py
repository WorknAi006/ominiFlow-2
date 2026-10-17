import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import CurrentTenant, CurrentUser, DbSession, require_permission
from app.api.errors import service_errors
from app.models.automation import AutomationStatus
from app.schemas.automation import (
    AutomationCreate, AutomationDetailResponse, AutomationExecutionListResponse,
    AutomationExecutionLogResponse, AutomationFlowSave, AutomationListResponse,
    AutomationNodeCreate, AutomationNodeResponse, AutomationNodeUpdate,
    AutomationResponse, AutomationUpdate, AutomationValidationResponse,
    SimulationInput, SimulationResponse, AutomationExecutionMetrics, AutomationWorkerHealth,
)
from app.services import automation_service
from app.services.automation_service import (
    AutomationConflictError, AutomationFlowLockedError, AutomationInvalidFlowError,
    AutomationNotFoundError,
)

router = APIRouter(prefix="/automations", tags=["Automations"])
ERRORS = {
    AutomationNotFoundError: status.HTTP_404_NOT_FOUND,
    AutomationConflictError: status.HTTP_409_CONFLICT,
    AutomationFlowLockedError: status.HTTP_409_CONFLICT,
    AutomationInvalidFlowError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _detail(db, tenant_id, automation_id):
    data = automation_service.get_detail(db, tenant_id, automation_id)
    return {
        **AutomationResponse.model_validate(data["automation"]).model_dump(),
        "nodes": data["nodes"], "edges": data["edges"],
    }


def _executions(result):
    fields = ("id", "automation_id", "automation_version", "conversation_id", "contact_id", "trigger_message_id", "status", "current_node_id", "attempt_count", "max_attempts", "step_count", "next_retry_at", "last_error_type", "started_at", "completed_at", "error_summary", "created_at")
    return {
        **{key: value for key, value in result.items() if key != "items"},
        "items": [{**{key: getattr(row["execution"], key) for key in fields}, "automation_name": row["automation_name"]} for row in result["items"]],
    }


@router.get("", response_model=AutomationListResponse, dependencies=[Depends(require_permission("automation:read"))])
def list_automations(tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), automation_status: AutomationStatus | None = Query(None, alias="status"), search: str | None = Query(None, max_length=100)):
    return automation_service.list_automations(db, tenant.id, page, page_size, automation_status, (search or "").strip() or None)


@router.post("", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("automation:create"))])
def create_automation(data: AutomationCreate, user: CurrentUser, tenant: CurrentTenant, db: DbSession):
    return automation_service.create_automation(db, tenant.id, user, data)


@router.get("/executions", response_model=AutomationExecutionListResponse, dependencies=[Depends(require_permission("automation:read"))])
def list_all_executions(tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return _executions(automation_service.list_executions(db, tenant.id, None, page, page_size))


@router.get("/worker-health", response_model=AutomationWorkerHealth, dependencies=[Depends(require_permission("automation:read"))])
def automation_worker_health(db: DbSession):
    from app.services.automation_execution_service import worker_health
    return worker_health(db)


@router.get("/executions/{execution_id}/logs", response_model=list[AutomationExecutionLogResponse], dependencies=[Depends(require_permission("automation:read"))])
def execution_logs(execution_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.list_execution_logs(db, tenant.id, execution_id)


@router.get("/{automation_id}", response_model=AutomationDetailResponse, dependencies=[Depends(require_permission("automation:read"))])
def get_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return _detail(db, tenant.id, automation_id)


@router.patch("/{automation_id}", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:update"))])
def update_automation(automation_id: uuid.UUID, data: AutomationUpdate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.update_automation(db, tenant.id, automation_id, data)


@router.delete("/{automation_id}", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:delete"))])
def archive_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.archive_automation(db, tenant.id, automation_id)


@router.post("/{automation_id}/validate", response_model=AutomationValidationResponse, dependencies=[Depends(require_permission("automation:update"))])
def validate_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        issues = automation_service.validate_flow(db, tenant.id, automation_id)
        return {"valid": not issues, "issues": issues}


@router.post("/{automation_id}/activate", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:publish"))])
def activate_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.activate(db, tenant.id, automation_id)


@router.post("/{automation_id}/pause", response_model=AutomationResponse, dependencies=[Depends(require_permission("automation:publish"))])
def pause_automation(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.pause(db, tenant.id, automation_id)


@router.post("/{automation_id}/simulate", response_model=SimulationResponse, dependencies=[Depends(require_permission("automation:update"))])
def simulate_automation(automation_id: uuid.UUID, data: SimulationInput, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.simulate_flow(db, tenant.id, automation_id, data.message)


@router.get("/{automation_id}/nodes", response_model=list[AutomationNodeResponse], dependencies=[Depends(require_permission("automation:read"))])
def list_nodes(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.get_detail(db, tenant.id, automation_id)["nodes"]


@router.post("/{automation_id}/nodes", response_model=AutomationNodeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("automation:update"))])
def create_node(automation_id: uuid.UUID, data: AutomationNodeCreate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.create_node(db, tenant.id, automation_id, data)


@router.patch("/{automation_id}/nodes/{node_id}", response_model=AutomationNodeResponse, dependencies=[Depends(require_permission("automation:update"))])
def update_node(automation_id: uuid.UUID, node_id: uuid.UUID, data: AutomationNodeUpdate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.update_node(db, tenant.id, automation_id, node_id, data)


@router.delete("/{automation_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("automation:update"))])
def delete_node(automation_id: uuid.UUID, node_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        automation_service.delete_node(db, tenant.id, automation_id, node_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{automation_id}/flow", response_model=AutomationDetailResponse, dependencies=[Depends(require_permission("automation:update"))])
def save_flow(automation_id: uuid.UUID, data: AutomationFlowSave, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        automation_service.save_flow(db, tenant.id, automation_id, data)
        return _detail(db, tenant.id, automation_id)


@router.get("/{automation_id}/executions", response_model=AutomationExecutionListResponse, dependencies=[Depends(require_permission("automation:read"))])
def list_automation_executions(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with service_errors(ERRORS):
        return _executions(automation_service.list_executions(db, tenant.id, automation_id, page, page_size))


@router.get("/{automation_id}/metrics", response_model=AutomationExecutionMetrics, dependencies=[Depends(require_permission("automation:read"))])
def automation_metrics(automation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return automation_service.execution_metrics(db, tenant.id, automation_id)
