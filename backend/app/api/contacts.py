import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.contact import (
    ContactCreate,
    ContactImportRequest,
    ContactImportResult,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from app.schemas.custom_field import ContactFieldsUpdate
from app.schemas.tag import (
    BulkDeleteRequest,
    BulkTagRequest,
    ContactTagsUpdate,
    DeleteAllRequest,
)
from app.services import contact_service, custom_field_service, tag_service
from app.services.contact_service import (
    ContactAlreadyExistsError,
    ContactNotFoundError,
    InvalidContactError,
)
from app.services.custom_field_service import CustomFieldNotFoundError, InvalidCustomFieldError
from app.services.tag_service import InvalidTagError, TagNotFoundError

router = APIRouter(prefix="/contacts", tags=["Contacts"])

ERRORS = {
    ContactNotFoundError: status.HTTP_404_NOT_FOUND,
    ContactAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidContactError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    TagNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidTagError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CustomFieldNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidCustomFieldError: status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    tag_id: uuid.UUID | None = Query(default=None),
    channel_type: str | None = Query(default=None, max_length=20),
    source: str | None = Query(default=None, max_length=20),
):
    with service_errors(ERRORS):
        return contact_service.list_contacts(
            db, tenant.id, page, page_size,
            search=(search or "").strip() or None,
            phone=(phone or "").strip() or None,
            tag_id=tag_id,
            channel_type=(channel_type or "").strip() or None,
            source=(source or "").strip() or None,
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


# ---- Collection-level routes (declared before /{contact_id} so literal
#      paths like /export are not captured by the UUID path param). ----

@router.get(
    "/export",
    dependencies=[Depends(require_permission("contact:read"))],
)
def export_contacts(
    tenant: CurrentTenant,
    db: DbSession,
    search: str | None = Query(default=None, max_length=100),
    tag_id: uuid.UUID | None = Query(default=None),
    channel_type: str | None = Query(default=None, max_length=20),
):
    with service_errors(ERRORS):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=contact_service.EXPORT_COLUMNS)
        writer.writeheader()
        for row in contact_service.iter_export_rows(
            db, tenant.id,
            search=(search or "").strip() or None,
            tag_id=tag_id,
            channel_type=(channel_type or "").strip() or None,
        ):
            writer.writerow(row)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="contacts.csv"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/bulk-delete",
    dependencies=[Depends(require_permission("contact:delete"))],
)
def bulk_delete(data: BulkDeleteRequest, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        deleted = contact_service.bulk_delete_contacts(db, tenant.id, data.contact_ids)
    return {"deleted": deleted}


@router.post(
    "/all/delete",
    dependencies=[Depends(require_permission("contact:delete"))],
)
def delete_all(data: DeleteAllRequest, tenant: CurrentTenant, db: DbSession):
    if data.confirm != contact_service.DELETE_ALL_CONFIRM:
        with service_errors(ERRORS):
            raise InvalidContactError('You must type "DELETE ALL" to confirm.')
    with service_errors(ERRORS):
        deleted = contact_service.delete_all_contacts(db, tenant.id)
    return {"deleted": deleted}


@router.post(
    "/import",
    response_model=ContactImportResult,
    dependencies=[Depends(require_permission("contact:create"))],
)
def import_contacts(data: ContactImportRequest, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return contact_service.import_contacts(db, tenant.id, data.rows)


@router.post(
    "/tags",
    dependencies=[Depends(require_permission("contact:update"))],
)
def bulk_tags(data: BulkTagRequest, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        affected = tag_service.bulk_apply_tags(
            db, tenant.id, data.contact_ids, data.add_tag_ids, data.remove_tag_ids,
        )
    return {"affected": affected}


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


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("contact:delete"))],
)
def delete_contact(contact_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        contact_service.delete_contact(db, tenant.id, contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{contact_id}/tags",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact:update"))],
)
def set_contact_tags(
    contact_id: uuid.UUID,
    data: ContactTagsUpdate,
    tenant: CurrentTenant,
    db: DbSession,
):
    with service_errors(ERRORS):
        return tag_service.set_contact_tags(db, tenant.id, contact_id, data.tag_ids)


@router.post(
    "/{contact_id}/fields",
    response_model=ContactResponse,
    dependencies=[Depends(require_permission("contact:update"))],
)
def set_contact_fields(
    contact_id: uuid.UUID,
    data: ContactFieldsUpdate,
    tenant: CurrentTenant,
    db: DbSession,
):
    with service_errors(ERRORS):
        return custom_field_service.set_contact_values(db, tenant.id, contact_id, data.values)
