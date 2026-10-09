import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.tag import TagCreate, TagListResponse, TagResponse, TagUpdate
from app.services import tag_service
from app.services.tag_service import (
    InvalidTagError,
    TagAlreadyExistsError,
    TagNotFoundError,
)

router = APIRouter(prefix="/tags", tags=["Tags"])

ERRORS = {
    TagNotFoundError: status.HTTP_404_NOT_FOUND,
    TagAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidTagError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


@router.get(
    "",
    response_model=TagListResponse,
    dependencies=[Depends(require_permission("contact:read"))],
)
def list_tags(tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return tag_service.list_tags(db, tenant.id)


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("contact:update"))],
)
def create_tag(data: TagCreate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return tag_service.create_tag(db, tenant.id, data)


@router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    dependencies=[Depends(require_permission("contact:update"))],
)
def update_tag(tag_id: uuid.UUID, data: TagUpdate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return tag_service.update_tag(db, tenant.id, tag_id, data)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("contact:update"))],
)
def delete_tag(tag_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        tag_service.delete_tag(db, tenant.id, tag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
