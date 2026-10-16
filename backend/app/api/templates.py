import uuid
import json
import re
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError

from app.api.dependencies import (
    CurrentTenant,
    CurrentUser,
    DbSession,
    require_permission,
    require_platform_super_admin,
)
from app.api.errors import service_errors
from app.schemas.template import (
    AiTemplateGenerateRequest,
    AiTemplateGenerateResponse,
    LocalTemplateCreate,
    LocalTemplateSubmission,
    TemplateListResponse,
    TemplateResponse,
    TemplateSyncResponse,
)
from app.schemas.platform_template import (
    PlatformTemplateAdminStatus,
    PlatformTemplateCreate,
    PlatformTemplateListResponse,
    PlatformTemplateResponse,
    PlatformTemplateSubmitRequest,
    PlatformTemplateSubmitResponse,
)
from app.services import ai_template_service, payment_service, template_service
from app.services import platform_template_service
from app.services.template_service import (
    ChannelNotFoundError,
    TemplateAlreadyExistsError,
    TemplateChannelNotConnectedError,
    TemplateCredentialsError,
    TemplateNotConfiguredError,
    TemplateNotFoundError,
    TemplateSubmissionFailedError,
    TemplateMediaUploadError,
    TemplateSyncFailedError,
    UnsupportedTemplateChannelError,
)
from app.services.platform_template_service import (
    PlatformTemplateAccessError,
    PlatformTemplateConflictError,
    PlatformTemplateNotFoundError,
    PlatformTemplateProviderError,
)

router = APIRouter(tags=["Templates"])

MEDIA_RULES = {
    "IMAGE": ({"image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}}, 5 * 1024 * 1024),
    "VIDEO": ({"video/mp4": {".mp4"}}, 16 * 1024 * 1024),
    "DOCUMENT": ({"application/pdf": {".pdf"}}, 100 * 1024 * 1024),
}
SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


async def read_template_media(file: UploadFile, media_type: str) -> tuple[bytes, str, str]:
    rules = MEDIA_RULES[media_type]
    filename = PurePath(file.filename or "upload").name
    content_type = (file.content_type or "").lower()
    extension = PurePath(filename).suffix.lower()
    valid_extensions = rules[0].get(content_type)
    if valid_extensions is None or extension not in valid_extensions:
        raise HTTPException(status_code=422, detail=f"Choose a valid {media_type.lower()} file.")
    data = await file.read(rules[1] + 1)
    if not data:
        raise HTTPException(status_code=422, detail="The selected media file is empty.")
    if len(data) > rules[1]:
        raise HTTPException(status_code=413, detail=f"The {media_type.lower()} file is too large.")
    valid_signature = (
        (media_type == "IMAGE" and (
            content_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff")
            or content_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n")
        ))
        or (media_type == "VIDEO" and len(data) >= 12 and data[4:8] == b"ftyp")
        or (media_type == "DOCUMENT" and data.startswith(b"%PDF-"))
    )
    if not valid_signature:
        raise HTTPException(status_code=422, detail=f"The selected file is not a valid {media_type.lower()}.")
    safe_name = SAFE_FILENAME_CHARS.sub("_", filename)[:255] or "upload"
    return data, content_type, safe_name


@router.post(
    "/templates/submit",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("template:sync"))],
)
async def submit_local_template(
    tenant: CurrentTenant,
    db: DbSession,
    name: str = Form(...),
    channel_connection_id: uuid.UUID = Form(...),
    language: str = Form(...),
    category: str = Form(...),
    header_format: str = Form("NONE"),
    header_text: str | None = Form(None),
    body_text: str = Form(...),
    footer_text: str | None = Form(None),
    buttons_json: str = Form("[]"),
    body_examples_json: str = Form("[]"),
    header_file: UploadFile | None = File(None),
):
    try:
        buttons = json.loads(buttons_json)
        body_examples = json.loads(body_examples_json)
        if not isinstance(buttons, list) or not isinstance(body_examples, list):
            raise ValueError
        definition = LocalTemplateSubmission(
            name=name,
            channel_connection_id=channel_connection_id,
            language=language,
            category=category,
            header_format=header_format,
            header_text=header_text,
            body_text=body_text,
            footer_text=footer_text,
            buttons=buttons,
            body_examples=body_examples,
        )
    except (ValueError, ValidationError) as exc:
        detail = exc.errors() if isinstance(exc, ValidationError) else "Template examples are invalid."
        raise HTTPException(status_code=422, detail=detail) from None

    sample = None
    if definition.header_format in MEDIA_RULES:
        if header_file is None:
            raise HTTPException(status_code=422, detail="Choose a sample file for the media header.")
        sample = await read_template_media(header_file, definition.header_format)
    elif header_file is not None:
        raise HTTPException(status_code=422, detail="A sample file is only used for media headers.")

    try:
        return template_service.submit_local_template(db, tenant.id, definition, sample)
    except tuple(ERRORS) as exc:
        raise HTTPException(status_code=ERRORS[type(exc)], detail=str(exc)) from None
    except TemplateSubmissionFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@router.post(
    "/templates/channels/{channel_id}/media-upload",
    dependencies=[Depends(require_permission("message:create"))],
)
async def upload_template_send_media(
    channel_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
    media_type: str = Form(...),
    file: UploadFile = File(...),
):
    if media_type.upper() not in MEDIA_RULES:
        raise HTTPException(status_code=422, detail="Media type must be image, video or document.")
    media = await read_template_media(file, media_type.upper())
    try:
        return template_service.upload_template_media(
            db, tenant.id, channel_id, media_type.lower(), *media,
        )
    except tuple(ERRORS) as exc:
        raise HTTPException(status_code=ERRORS[type(exc)], detail=str(exc)) from None
    except TemplateMediaUploadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None

PLATFORM_TEMPLATE_ERRORS = {
    PlatformTemplateNotFoundError: status.HTTP_404_NOT_FOUND,
    PlatformTemplateConflictError: status.HTTP_409_CONFLICT,
    PlatformTemplateAccessError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PlatformTemplateProviderError: status.HTTP_502_BAD_GATEWAY,
}


@router.get(
    "/platform-template-library/admin-status",
    response_model=PlatformTemplateAdminStatus,
)
def platform_template_admin_status(user: CurrentUser):
    return {"is_platform_super_admin": user.is_platform_super_admin}


@router.get(
    "/platform-template-library",
    response_model=PlatformTemplateListResponse,
    dependencies=[Depends(require_permission("template:read"))],
)
def list_platform_template_library(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
):
    return platform_template_service.list_library(
        db, include_inactive=user.is_platform_super_admin,
    )


@router.post(
    "/platform-template-library",
    response_model=PlatformTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_platform_super_admin)],
)
def create_platform_template(
    data: PlatformTemplateCreate,
    user: CurrentUser,
    db: DbSession,
):
    try:
        return platform_template_service.create_library_template(db, user, data)
    except PlatformTemplateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post(
    "/platform-template-library/{template_id}/deactivate",
    response_model=PlatformTemplateResponse,
    dependencies=[Depends(require_platform_super_admin)],
)
def deactivate_platform_template(
    template_id: uuid.UUID,
    db: DbSession,
):
    try:
        return platform_template_service.set_library_template_active(db, template_id, False)
    except PlatformTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post(
    "/platform-template-library/{template_id}/activate",
    response_model=PlatformTemplateResponse,
    dependencies=[Depends(require_platform_super_admin)],
)
def activate_platform_template(
    template_id: uuid.UUID,
    db: DbSession,
):
    try:
        return platform_template_service.set_library_template_active(db, template_id, True)
    except PlatformTemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post(
    "/platform-template-library/{template_id}/submit",
    response_model=PlatformTemplateSubmitResponse,
    dependencies=[Depends(require_permission("template:sync"))],
)
def submit_platform_template(
    template_id: uuid.UUID,
    data: PlatformTemplateSubmitRequest,
    tenant: CurrentTenant,
    db: DbSession,
):
    try:
        return platform_template_service.submit_for_tenant(
            db, tenant.id, template_id, data,
        )
    except tuple(PLATFORM_TEMPLATE_ERRORS) as exc:
        raise HTTPException(
            status_code=PLATFORM_TEMPLATE_ERRORS[type(exc)],
            detail=str(exc),
        ) from None


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
