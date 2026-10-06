import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from app.services import contact_service
from app.services.contact_service import (
    ContactAlreadyExistsError,
    ContactNotFoundError,
    InvalidContactError,
)

router = APIRouter(prefix="/contacts", tags=["Contacts"])

ERRORS = {
    ContactNotFoundError: status.HTTP_404_NOT_FOUND,
    ContactAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidContactError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


@router.get(
    "",
    response_model=ContactListResponse,
    dependencies=[Depends(require_permission("contact:read"))],
)
def list_contacts(
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    phone: str | None = Query(default=None, max_length=32),
):
    with service_errors(ERRORS):
        return contact_service.list_contacts(
            db, tenant.id, page, page_size,
            search=(search or "").strip() or None,
            phone=(phone or "").strip() or None,
        )


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("contact:create"))],
)
def create_contact(data: ContactCreate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return contact_service.create_contact(db, tenant.id, data)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact:read"))],
)
def get_contact(contact_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return contact_service.get_contact(db, tenant.id, contact_id)


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact:update"))],
)
def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    tenant: CurrentTenant,
    db: DbSession,
):
    with service_errors(ERRORS):
        return contact_service.update_contact(db, tenant.id, contact_id, data)
