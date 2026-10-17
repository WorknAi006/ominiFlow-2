from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.schemas.whatsapp_form import WhatsAppFormCreate, WhatsAppFormListResponse, WhatsAppFormResponse, WhatsAppFormUpdate
from app.services import whatsapp_form_service

router = APIRouter(prefix="/whatsapp-forms", tags=["WhatsApp Forms"])

@router.get("", response_model=WhatsAppFormListResponse)
def list_forms(tenant: CurrentTenant, db: DbSession, page: int = Query(1, ge=1), size: int = Query(20, ge=1)):
    return whatsapp_form_service.list_forms(db, tenant.id, page, size)

@router.get("/{form_id}", response_model=WhatsAppFormResponse)
def get_form(form_id: str, tenant: CurrentTenant, db: DbSession):
    form = whatsapp_form_service.get_form(db, tenant.id, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form

@router.post("", response_model=WhatsAppFormResponse, status_code=status.HTTP_201_CREATED)
def create_form(data: WhatsAppFormCreate, tenant: CurrentTenant, db: DbSession):
    return whatsapp_form_service.create_form(db, tenant.id, data)

@router.patch("/{form_id}", response_model=WhatsAppFormResponse)
def update_form(form_id: str, data: WhatsAppFormUpdate, tenant: CurrentTenant, db: DbSession):
    form = whatsapp_form_service.update_form(db, tenant.id, form_id, data)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form

@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(form_id: str, tenant: CurrentTenant, db: DbSession):
    if not whatsapp_form_service.delete_form(db, tenant.id, form_id):
        raise HTTPException(status_code=404, detail="Form not found")
