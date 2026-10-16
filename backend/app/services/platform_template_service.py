import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.base import (
    ProviderCredentials,
    ProviderError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.integrations.registry import get_provider
from app.integrations.whatsapp.provider import WhatsAppProvider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    MessageTemplate,
    PlatformTemplate,
    User,
)
from app.schemas.platform_template import (
    PlatformTemplateCreate,
    PlatformTemplateListResponse,
    PlatformTemplateResponse,
    PlatformTemplateSubmitRequest,
    PlatformTemplateSubmitResponse,
)
from app.services.credential_service import CredentialEncryptionError, get_credential_service
from app.services.template_service import to_template_response


class PlatformTemplateError(Exception):
    """Base error for global and tenant template library workflows."""


class PlatformTemplateNotFoundError(PlatformTemplateError):
    pass


class PlatformTemplateConflictError(PlatformTemplateError):
    pass


class PlatformTemplateAccessError(PlatformTemplateError):
    pass


class PlatformTemplateProviderError(PlatformTemplateError):
    pass


def list_library(db: Session, *, include_inactive: bool = False) -> PlatformTemplateListResponse:
    query = select(PlatformTemplate)
    if not include_inactive:
        query = query.where(PlatformTemplate.is_active.is_(True))
    query = query.order_by(PlatformTemplate.label.asc(), PlatformTemplate.language.asc())
    items = list(db.scalars(query).all())
    return PlatformTemplateListResponse(
        items=[PlatformTemplateResponse.model_validate(item) for item in items],
        total=len(items),
    )


def create_library_template(
    db: Session,
    user: User,
    data: PlatformTemplateCreate,
) -> PlatformTemplateResponse:
    row = PlatformTemplate(**data.model_dump(), created_by=user.id)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise PlatformTemplateConflictError(
            "A common template with this name and language already exists."
        ) from None
    db.refresh(row)
    return PlatformTemplateResponse.model_validate(row)


def set_library_template_active(
    db: Session,
    template_id: uuid.UUID,
    active: bool,
) -> PlatformTemplateResponse:
    row = db.get(PlatformTemplate, template_id)
    if row is None:
        raise PlatformTemplateNotFoundError("Common template not found.")
    row.is_active = active
    db.commit()
    db.refresh(row)
    return PlatformTemplateResponse.model_validate(row)


def submit_for_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    data: PlatformTemplateSubmitRequest,
) -> PlatformTemplateSubmitResponse:
    platform_template = db.scalar(
        select(PlatformTemplate).where(
            PlatformTemplate.id == template_id,
            PlatformTemplate.is_active.is_(True),
        )
    )
    if platform_template is None:
        raise PlatformTemplateNotFoundError("Common template not found.")

    channel = db.scalar(
        select(ChannelConnection).where(
            ChannelConnection.id == data.channel_connection_id,
            ChannelConnection.tenant_id == tenant_id,
            ChannelConnection.channel_type == ChannelType.WHATSAPP,
            ChannelConnection.is_deleted.is_(False),
        )
    )
    if channel is None:
        raise PlatformTemplateAccessError("Select a WhatsApp channel in this workspace.")
    if (
        channel.status != ChannelStatus.CONNECTED
        or not channel.external_business_id
        or not channel.access_token_encrypted
    ):
        raise PlatformTemplateAccessError("Connect this WhatsApp channel before submitting templates.")

    template_placeholders = list(dict.fromkeys(
        re.findall(r"\{\{\s*(\d+)\s*\}\}", platform_template.body_text)
    ))
    submitted_placeholders = list(dict.fromkeys(
        re.findall(r"\{\{\s*(\d+)\s*\}\}", data.body_text)
    ))
    if submitted_placeholders != template_placeholders:
        raise PlatformTemplateAccessError(
            "Keep the common template's numbered placeholders unchanged."
        )
    if len(data.examples) != len(template_placeholders) or any(
        not value.strip() for value in data.examples
    ):
        raise PlatformTemplateAccessError(
            "Provide one non-empty example value for every template placeholder."
        )

    existing = db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.channel_connection_id == channel.id,
            MessageTemplate.name == platform_template.name,
            MessageTemplate.language == platform_template.language,
            MessageTemplate.is_active.is_(True),
        )
    )
    if existing is not None and existing.status != "draft":
        raise PlatformTemplateConflictError(
            f"This template already exists on the selected WhatsApp account (status: {existing.status}). Sync templates to refresh its status."
        )

    try:
        token = get_credential_service().decrypt(channel.access_token_encrypted)
    except CredentialEncryptionError:
        raise PlatformTemplateAccessError(
            "WhatsApp credentials are unavailable. Reconnect this channel."
        ) from None

    components = [{
        "type": "BODY",
        "text": data.body_text,
        **(
            {"example": {"body_text": [data.examples]}}
            if template_placeholders else {}
        ),
    }]
    payload = {
        "name": platform_template.name,
        "language": platform_template.language,
        "category": platform_template.category.upper(),
        "components": components,
    }
    if existing is None:
        existing = MessageTemplate(
            tenant_id=tenant_id,
            channel_connection_id=channel.id,
            name=platform_template.name,
            language=platform_template.language,
            category=platform_template.category,
            status="submitting",
            components=components,
            template_metadata={"platform_template_id": str(platform_template.id)},
            is_active=True,
        )
        db.add(existing)
    else:
        existing.status = "submitting"
        existing.category = platform_template.category
        existing.components = components
        existing.template_metadata = {"platform_template_id": str(platform_template.id)}
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise PlatformTemplateConflictError(
            "This common template has already been submitted to the selected WhatsApp account."
        ) from None

    provider = get_provider(ChannelType.WHATSAPP)
    if not isinstance(provider, WhatsAppProvider):
        del token
        existing.status = "draft"
        db.commit()
        raise PlatformTemplateProviderError("WhatsApp template submission is unavailable.")
    try:
        response = provider.create_template(
            ProviderCredentials(access_token=token),
            channel.external_business_id,
            payload,
        )
    except ProviderUnavailableError:
        raise PlatformTemplateProviderError(
            "Could not confirm Meta's response. Sync templates before trying again."
        ) from None
    except ProviderRequestError as exc:
        existing.status = "draft"
        db.commit()
        raise PlatformTemplateProviderError(
            f"Meta could not accept the template: {exc}"
        ) from None
    except ProviderError as exc:
        existing.status = "draft"
        db.commit()
        raise PlatformTemplateProviderError(
            f"Meta could not accept the template: {exc}"
        ) from None
    finally:
        del token

    result_id = response.get("id")
    status = response.get("status")
    if not isinstance(result_id, str) or not result_id:
        raise PlatformTemplateProviderError(
            "Meta returned an unexpected response. Sync templates before trying again."
        )
    normalized_status = status.lower() if isinstance(status, str) else "pending"
    now = datetime.now(timezone.utc)
    existing.external_template_id = result_id[:64]
    existing.status = normalized_status
    existing.category = platform_template.category
    existing.components = components
    existing.template_metadata = {"platform_template_id": str(platform_template.id)}
    existing.last_synced_at = now
    db.commit()
    db.refresh(existing)
    return PlatformTemplateSubmitResponse(
        template=to_template_response(existing),
        message="Submitted to Meta for review. Approval is per WhatsApp Business Account; sync later to refresh its status.",
    )
