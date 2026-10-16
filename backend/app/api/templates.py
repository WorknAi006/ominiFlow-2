import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import CurrentTenant, DbSession, require_permission
from app.api.errors import service_errors
from app.schemas.template import (
    AiTemplateGenerateRequest,
    AiTemplateGenerateResponse,
    LocalTemplateCreate,
    TemplateListResponse,
    TemplateResponse,
    TemplateSyncResponse,
)
from app.services import ai_template_service, payment_service, template_service
from app.services.template_service import (
    ChannelNotFoundError,
    TemplateAlreadyExistsError,
    TemplateChannelNotConnectedError,
    TemplateCredentialsError,
    TemplateNotConfiguredError,
    TemplateNotFoundError,
    TemplateSyncFailedError,
    UnsupportedTemplateChannelError,
)

router = APIRouter(tags=["Templates"])

ERRORS = {
    ChannelNotFoundError: status.HTTP_404_NOT_FOUND,
    TemplateNotFoundError: status.HTTP_404_NOT_FOUND,
    TemplateAlreadyExistsError: status.HTTP_409_CONFLICT,
    UnsupportedTemplateChannelError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    TemplateChannelNotConnectedError: status.HTTP_409_CONFLICT,
    TemplateSyncFailedError: status.HTTP_502_BAD_GATEWAY,
    TemplateCredentialsError: status.HTTP_503_SERVICE_UNAVAILABLE,
    TemplateNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("template:sync"))],
)
def create_local_template(data: LocalTemplateCreate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return template_service.create_local_template(db, tenant.id, data)


@router.post(
    "/templates/ai-generate",
    response_model=AiTemplateGenerateResponse,
    dependencies=[Depends(require_permission("template:sync"))],
)
def ai_generate_templates(data: AiTemplateGenerateRequest, tenant: CurrentTenant, db: DbSession):
    """Generate template drafts with AI and charge credits for the usage."""
    if payment_service.get_or_create_balance(db, tenant.id) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No AI credits remaining. Please buy credits.")

    try:
        result = ai_template_service.generate_templates(
            db, tenant.id, data.prompt, count=data.count, category=data.category, language=data.language,
        )
    except ai_template_service.AiProviderError as exc:
        # The AI provider was reached but failed (e.g. no OpenAI quota, bad key).
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI provider error: {exc}") from None

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is not configured. Set OPENAI_API_KEY in the backend environment.",
        )

    charge = payment_service.credits_for_tokens(result["tokens_in"] + result["tokens_out"])
    balance = payment_service.deduct_credits(
        db, tenant.id, charge, description="AI template generation",
        model=result.get("model"), tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
    )
    return AiTemplateGenerateResponse(items=result["drafts"], credits_used=charge, balance=balance)


@router.get(
    "/channels/{channel_id}/templates",
    response_model=TemplateListResponse,
    dependencies=[Depends(require_permission("template:read"))],
)
def list_templates(
    channel_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    template_status: str | None = Query(default=None, alias="status", pattern=r"^[A-Za-z_]{1,30}$"),
    search: str | None = Query(default=None, max_length=100),
    include_inactive: bool = Query(default=False),
):
    with service_errors(ERRORS):
        return template_service.list_templates(
            db, tenant.id, channel_id, page, page_size,
            status=template_status,
            search=(search or "").strip() or None,
            include_inactive=include_inactive,
        )


@router.post(
    "/channels/{channel_id}/templates/sync",
    response_model=TemplateSyncResponse,
    dependencies=[Depends(require_permission("template:sync"))],
)
def sync_templates(channel_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return template_service.sync_templates(db, tenant.id, channel_id)


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    dependencies=[Depends(require_permission("template:read"))],
)
def list_all_templates(
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    channel_id: uuid.UUID | None = Query(default=None),
    template_status: str | None = Query(default=None, alias="status", pattern=r"^[A-Za-z_]{1,30}$"),
    category: str | None = Query(default=None, pattern=r"^[A-Za-z_]{1,30}$"),
    language: str | None = Query(default=None, pattern=r"^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?$"),
    search: str | None = Query(default=None, max_length=100),
    include_inactive: bool = Query(default=False),
):
    with service_errors(ERRORS):
        return template_service.list_all_templates(
            db, tenant.id, page, page_size,
            channel_id=channel_id,
            status=template_status,
            category=category,
            language=language,
            search=(search or "").strip() or None,
            include_inactive=include_inactive,
        )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(require_permission("template:read"))],
)
def get_template(template_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return template_service.get_template(db, tenant.id, template_id)
