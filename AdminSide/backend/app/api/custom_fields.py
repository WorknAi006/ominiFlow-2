import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.custom_field import (
    CustomFieldCreate,
    CustomFieldListResponse,
    CustomFieldResponse,
    CustomFieldUpdate,
)
from app.services import custom_field_service
from app.services.custom_field_service import (
    CustomFieldAlreadyExistsError,
    CustomFieldNotFoundError,
    InvalidCustomFieldError,
)

router = APIRouter(prefix="/custom-fields", tags=["Custom Fields"])

ERRORS = {
    CustomFieldNotFoundError: status.HTTP_404_NOT_FOUND,
    CustomFieldAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidCustomFieldError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


@router.get(
    "",
    response_model=CustomFieldListResponse,
    dependencies=[Depends(require_permission("contact:read"))],
)
def list_fields(tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return custom_field_service.list_fields(db, tenant.id)


@router.post(
    "",
    response_model=CustomFieldResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("contact:update"))],
)
def create_field(data: CustomFieldCreate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return custom_field_service.create_field(db, tenant.id, data)


@router.patch(
    "/{field_id}",
    response_model=CustomFieldResponse,
    dependencies=[Depends(require_permission("contact:update"))],
)
def update_field(field_id: uuid.UUID, data: CustomFieldUpdate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return custom_field_service.update_field(db, tenant.id, field_id, data)


@router.delete(
    "/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("contact:update"))],
)
def delete_field(field_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        custom_field_service.delete_field(db, tenant.id, field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
