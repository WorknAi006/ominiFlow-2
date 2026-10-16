"""
WhatsApp message templates: sync from Meta, query, and send-time
validation of template parameters against the stored definition.
"""
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.base import (
    ProviderCredentials,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.integrations.registry import get_provider
from app.integrations.whatsapp.provider import WhatsAppProvider
from app.models import (
    USABLE_TEMPLATE_STATUSES,
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    MessageTemplate,
)
from app.schemas.template import (
    LocalTemplateSubmission,
    TemplateComponentInput,
    TemplateListResponse,
    TemplateResponse,
    TemplateSyncResponse,
)
from app.services.credential_service import CredentialEncryptionError, get_credential_service
from app.services.query_utils import like_pattern, page_offset

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[a-z0-9_]{1,512}$")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?$")
POSITIONAL_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")
NAMED_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")
MEDIA_HEADER_FORMATS = {"IMAGE": "image", "VIDEO": "video", "DOCUMENT": "document"}
HEADER_TEXT_LIMIT = 60


class TemplateServiceError(Exception):
    """Base template error. Messages are safe to return."""


class ChannelNotFoundError(TemplateServiceError):
    pass


class TemplateNotFoundError(TemplateServiceError):
    pass


class UnsupportedTemplateChannelError(TemplateServiceError):
    pass


class TemplateChannelNotConnectedError(TemplateServiceError):
    pass


class TemplateCredentialsError(TemplateServiceError):
    pass


class TemplateSyncFailedError(TemplateServiceError):
    pass


class TemplateNotConfiguredError(TemplateServiceError):
    pass


class TemplateNotUsableError(TemplateServiceError):
    pass


class TemplateAlreadyExistsError(TemplateServiceError):
    """A template with this name + language already exists on the channel."""


class TemplateSubmissionFailedError(TemplateServiceError):
    pass


class TemplateMediaUploadError(TemplateServiceError):
    pass


class TemplateParameterError(TemplateServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# =========================
# RESPONSES / QUERIES
# =========================

def is_usable(template: MessageTemplate) -> bool:
    return template.is_active and template.status in USABLE_TEMPLATE_STATUSES


def to_template_response(template: MessageTemplate) -> TemplateResponse:
    metadata = template.template_metadata or {}
    return TemplateResponse(
        id=template.id,
        channel_connection_id=template.channel_connection_id,
        external_template_id=template.external_template_id,
        name=template.name,
        language=template.language,
        category=template.category,
        status=template.status,
        is_active=template.is_active,
        is_usable=is_usable(template),
        components=template.components,
        parameter_format=metadata.get("parameter_format"),
        last_synced_at=template.last_synced_at,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _get_channel(db: Session, tenant_id: uuid.UUID, channel_id: uuid.UUID) -> ChannelConnection:
    channel = (
        db.query(ChannelConnection)
        .filter(
            ChannelConnection.id == channel_id,
            ChannelConnection.tenant_id == tenant_id,
            ChannelConnection.is_deleted.is_(False),
        )
        .first()
    )
    if channel is None:
        raise ChannelNotFoundError("Channel not found.")
    return channel


def list_templates(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    page: int,
    page_size: int,
    *,
    status: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
) -> TemplateListResponse:

    _get_channel(db, tenant_id, channel_id)

    query = db.query(MessageTemplate).filter(
        MessageTemplate.tenant_id == tenant_id,
        MessageTemplate.channel_connection_id == channel_id,
    )
    if not include_inactive:
        query = query.filter(MessageTemplate.is_active.is_(True))
    if status:
        query = query.filter(MessageTemplate.status == status.lower())
    if search:
        query = query.filter(MessageTemplate.name.ilike(like_pattern(search), escape="\\"))

    total = query.count()
    templates = (
        query.order_by(MessageTemplate.name.asc(), MessageTemplate.language.asc())
        .offset(page_offset(page, page_size))
        .limit(page_size)
        .all()
    )

    return TemplateListResponse(
        items=[to_template_response(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_all_templates(
    db: Session,
    tenant_id: uuid.UUID,
    page: int,
    page_size: int,
    *,
    channel_id: uuid.UUID | None = None,
    status: str | None = None,
    category: str | None = None,
    language: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
) -> TemplateListResponse:
    """
    Tenant-wide template listing for the Templates dashboard, with optional
    channel/status/category/language filters. Always scoped to tenant_id;
    a channel_id from another tenant simply yields no rows.
    """

    query = db.query(MessageTemplate).filter(MessageTemplate.tenant_id == tenant_id)

    if channel_id is not None:
        query = query.filter(MessageTemplate.channel_connection_id == channel_id)
    if not include_inactive:
        query = query.filter(MessageTemplate.is_active.is_(True))
    if status:
        query = query.filter(MessageTemplate.status == status.lower())
    if category:
        query = query.filter(MessageTemplate.category == category.lower())
    if language:
        query = query.filter(MessageTemplate.language == language)
    if search:
        query = query.filter(MessageTemplate.name.ilike(like_pattern(search), escape="\\"))

    total = query.count()
    templates = (
        query.order_by(
            MessageTemplate.name.asc(),
            MessageTemplate.language.asc(),
            MessageTemplate.id.asc(),
        )
        .offset(page_offset(page, page_size))
        .limit(page_size)
        .all()
    )

    return TemplateListResponse(
        items=[to_template_response(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_template(db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID) -> TemplateResponse:
    template = (
        db.query(MessageTemplate)
        .filter(MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id)
        .first()
    )
    if template is None:
        raise TemplateNotFoundError("Template not found.")
    return to_template_response(template)


def create_local_template(db: Session, tenant_id: uuid.UUID, data) -> TemplateResponse:
    """Store a local draft template. Not sendable until approved by Meta and
    synced (status stays ``draft``, is_usable False)."""
    channel = _get_channel(db, tenant_id, data.channel_connection_id)

    components: list[dict[str, Any]] = []
    header_format = data.header_format
    if header_format == "NONE" and data.header_text:
        header_format = "TEXT"
    if header_format in ("IMAGE", "VIDEO", "DOCUMENT"):
        components.append({"type": "HEADER", "format": header_format})
    elif header_format == "TEXT" and data.header_text:
        components.append({"type": "HEADER", "format": "TEXT", "text": data.header_text})
    components.append({"type": "BODY", "text": data.body_text})
    if data.footer_text:
        components.append({"type": "FOOTER", "text": data.footer_text})
    if data.buttons:
        components.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": b} for b in data.buttons if b]})

    template = MessageTemplate(
        tenant_id=tenant_id,
        channel_connection_id=channel.id,
        external_template_id=None,
        name=data.name,
        language=data.language,
        category=data.category,
        status="draft",
        components=components,
        is_active=True,
    )
    db.add(template)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise TemplateAlreadyExistsError("A template with this name and language already exists on this channel.")
    db.refresh(template)
    return to_template_response(template)


def submit_local_template(
    db: Session,
    tenant_id: uuid.UUID,
    data: LocalTemplateSubmission,
    sample_file: tuple[bytes, str, str] | None,
) -> TemplateResponse:
    channel = _get_channel(db, tenant_id, data.channel_connection_id)
    if channel.channel_type != ChannelType.WHATSAPP:
        raise UnsupportedTemplateChannelError("Templates are only available for WhatsApp channels.")
    if (
        channel.status != ChannelStatus.CONNECTED
        or not channel.external_account_id
        or not channel.external_business_id
        or not channel.access_token_encrypted
    ):
        raise TemplateChannelNotConnectedError("The WhatsApp channel is not connected.")

    media_format = data.header_format in MEDIA_HEADER_FORMATS
    if media_format != (sample_file is not None):
        raise TemplateSubmissionFailedError(
            "Choose a matching sample file for an image, video or document header."
        )

    existing = db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.channel_connection_id == channel.id,
            MessageTemplate.name == data.name,
            MessageTemplate.language == data.language,
        )
    )
    if existing is not None and existing.status != "draft":
        raise TemplateAlreadyExistsError(
            f"This template already exists on this WhatsApp account (status: {existing.status})."
        )

    try:
        token = get_credential_service().decrypt(channel.access_token_encrypted)
    except CredentialEncryptionError:
        raise TemplateCredentialsError(
            "WhatsApp credentials are unavailable. Reconnect this channel."
        ) from None

    provider = get_provider(ChannelType.WHATSAPP)
    if not isinstance(provider, WhatsAppProvider) or not provider.is_configured():
        del token
        raise TemplateNotConfiguredError("WhatsApp integration is not configured.")

    components: list[dict[str, Any]] = []
    if data.header_format == "TEXT":
        components.append({"type": "HEADER", "format": "TEXT", "text": data.header_text})
    elif media_format:
        components.append({"type": "HEADER", "format": data.header_format})
    body: dict[str, Any] = {"type": "BODY", "text": data.body_text}
    if data.body_examples:
        body["example"] = {"body_text": [data.body_examples]}
    components.append(body)
    if data.footer_text:
        components.append({"type": "FOOTER", "text": data.footer_text})
    if data.buttons:
        components.append({
            "type": "BUTTONS",
            "buttons": [{"type": "QUICK_REPLY", "text": label} for label in data.buttons],
        })

    existing_components = components
    if existing is None:
        existing = MessageTemplate(
            tenant_id=tenant_id,
            channel_connection_id=channel.id,
            name=data.name,
            language=data.language,
            category=data.category.lower(),
            status="submitting",
            components=existing_components,
            template_metadata={"parameter_format": "POSITIONAL"},
            is_active=True,
        )
        db.add(existing)
    else:
        existing.category = data.category.lower()
        existing.status = "submitting"
        existing.components = existing_components
        existing.template_metadata = {"parameter_format": "POSITIONAL"}
        existing.is_active = True
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        del token
        raise TemplateAlreadyExistsError(
            "A template with this name and language already exists on this channel."
        ) from None

    payload_components = [dict(component) for component in components]
    try:
        if sample_file is not None:
            sample_bytes, content_type, _filename = sample_file
            handle = provider.upload_template_sample(
                ProviderCredentials(access_token=token), sample_bytes, content_type,
            )
            header = next(item for item in payload_components if item["type"] == "HEADER")
            header["example"] = {"header_handle": [handle]}
        result = provider.create_template(
            ProviderCredentials(access_token=token),
            channel.external_business_id,
            {
                "name": data.name,
                "language": data.language,
                "category": data.category,
                "components": payload_components,
            },
        )
    except ProviderUnavailableError:
        raise TemplateSubmissionFailedError(
            "Could not confirm Meta's response. Sync templates before trying again."
        ) from None
    except (ProviderRequestError, ProviderError) as exc:
        existing.status = "draft"
        db.commit()
        raise TemplateSubmissionFailedError(f"Meta could not accept the template: {exc}") from None
    finally:
        del token

    external_id = result.get("id")
    if not isinstance(external_id, str) or not external_id:
        raise TemplateSubmissionFailedError(
            "Meta returned an unexpected response. Sync templates before trying again."
        )
    status_value = result.get("status")
    existing.external_template_id = external_id[:64]
    existing.status = status_value.lower() if isinstance(status_value, str) else "pending"
    existing.components = components
    existing.last_synced_at = _utcnow()
    db.commit()
    db.refresh(existing)
    return to_template_response(existing)


def upload_template_media(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    media_type: str,
    data: bytes,
    content_type: str,
    filename: str,
) -> dict[str, str]:
    channel = _get_channel(db, tenant_id, channel_id)
    if channel.channel_type != ChannelType.WHATSAPP:
        raise UnsupportedTemplateChannelError("Media headers are only available for WhatsApp channels.")
    if (
        channel.status != ChannelStatus.CONNECTED
        or not channel.external_account_id
        or not channel.access_token_encrypted
    ):
        raise TemplateChannelNotConnectedError("The WhatsApp channel is not connected.")
    try:
        token = get_credential_service().decrypt(channel.access_token_encrypted)
    except CredentialEncryptionError:
        raise TemplateCredentialsError(
            "WhatsApp credentials are unavailable. Reconnect this channel."
        ) from None

    provider = get_provider(ChannelType.WHATSAPP)
    if not isinstance(provider, WhatsAppProvider) or not provider.is_configured():
        del token
        raise TemplateNotConfiguredError("WhatsApp integration is not configured.")
    try:
        media_id = provider.upload_media(
            ProviderCredentials(access_token=token),
            channel.external_account_id,
            data,
            content_type,
            filename,
        )
    except ProviderUnavailableError:
        raise TemplateMediaUploadError("Could not reach WhatsApp. Please try again.") from None
    except ProviderRequestError as exc:
        raise TemplateMediaUploadError(f"WhatsApp rejected the media file: {exc}") from None
    except ProviderError as exc:
        raise TemplateMediaUploadError(f"WhatsApp could not accept the media file: {exc}") from None
    finally:
        del token
    return {"id": media_id, "type": media_type, "filename": filename}


# =========================
# SYNC
# =========================

@dataclass(frozen=True)
class _ParsedTemplate:
    external_id: str | None
    name: str
    language: str
    category: str | None
    status: str
    components: list[dict[str, Any]]
    metadata: dict[str, Any]


def _parse_template(item: dict[str, Any]) -> _ParsedTemplate | None:
    name, language, status = item.get("name"), item.get("language"), item.get("status")
    components = item.get("components")

    if not (isinstance(name, str) and NAME_RE.match(name)):
        return None
    if not (isinstance(language, str) and LANGUAGE_RE.match(language)):
        return None
    if not isinstance(status, str) or not status.strip():
        return None
    if not isinstance(components, list) or not all(isinstance(c, dict) for c in components):
        return None

    external_id = item.get("id")
    category = item.get("category")

    return _ParsedTemplate(
        external_id=str(external_id)[:64] if external_id is not None else None,
        name=name,
        language=language,
        category=category.lower()[:30] if isinstance(category, str) else None,
        status=status.strip().lower()[:30],
        components=components,
        metadata={
            key: item[key]
            for key in ("parameter_format", "quality_score", "rejected_reason")
            if item.get(key) is not None
        },
    )


UPSERT_ATTRIBUTES = (
    "external_template_id",
    "category",
    "status",
    "components",
    "template_metadata",
    "is_active",
    "last_synced_at",
)


def _column(attribute: str):
    """Table column behind a mapped attribute (handles renamed columns)."""
    return getattr(MessageTemplate, attribute).property.columns[0]


def sync_templates(db: Session, tenant_id: uuid.UUID, channel_id: uuid.UUID) -> TemplateSyncResponse:
    """
    Fetch templates from Meta (no transaction open during HTTP), then
    upsert them idempotently. Templates missing from Meta are deactivated.
    """

    channel = _get_channel(db, tenant_id, channel_id)

    if channel.channel_type != ChannelType.WHATSAPP:
        raise UnsupportedTemplateChannelError("Templates are only available for WhatsApp channels.")
    if (
        channel.status != ChannelStatus.CONNECTED
        or not channel.access_token_encrypted
        or not channel.external_business_id
    ):
        raise TemplateChannelNotConnectedError("The WhatsApp channel is not connected.")

    provider = get_provider(ChannelType.WHATSAPP)
    assert isinstance(provider, WhatsAppProvider)
    if not provider.is_configured():
        raise TemplateNotConfiguredError("WhatsApp integration is not configured.")

    try:
        token = get_credential_service().decrypt(channel.access_token_encrypted)
    except CredentialEncryptionError:
        raise TemplateCredentialsError("Channel credentials are unavailable. Reconnect the channel.") from None

    waba_id = channel.external_business_id
    db.rollback()

    try:
        items = provider.list_templates(ProviderCredentials(access_token=token), waba_id)
    except (ProviderRequestError, ProviderUnavailableError) as exc:
        raise TemplateSyncFailedError(f"Template sync failed: {exc}") from None
    except ProviderNotConfiguredError:
        raise TemplateNotConfiguredError("WhatsApp integration is not configured.") from None
    finally:
        del token

    parsed: dict[tuple[str, str], _ParsedTemplate] = {}
    skipped = 0
    for item in items:
        template = _parse_template(item)
        if template is None:
            skipped += 1
            continue
        parsed[(template.name, template.language)] = template

    now = _utcnow()

    existing = set(
        db.execute(
            select(MessageTemplate.name, MessageTemplate.language).where(
                MessageTemplate.tenant_id == tenant_id,
                MessageTemplate.channel_connection_id == channel_id,
            )
        ).all()
    )

    try:
        for template in parsed.values():
            statement = insert(MessageTemplate).values(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                channel_connection_id=channel_id,
                name=template.name,
                language=template.language,
                external_template_id=template.external_id,
                category=template.category,
                status=template.status,
                components=template.components,
                template_metadata=template.metadata or None,
                is_active=True,
                last_synced_at=now,
            )
            db.execute(
                statement.on_conflict_do_update(
                    constraint="uq_message_templates_tenant_channel_name_language",
                    set_={
                        **{
                            _column(name): statement.excluded[_column(name).key]
                            for name in UPSERT_ATTRIBUTES
                        },
                        _column("updated_at"): func.now(),
                    },
                )
            )

        deactivate = update(MessageTemplate).where(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.channel_connection_id == channel_id,
            MessageTemplate.is_active.is_(True),
        )
        if parsed:
            deactivate = deactivate.where(
                tuple_(MessageTemplate.name, MessageTemplate.language).not_in(list(parsed))
            )
        deactivated = db.execute(
            deactivate.values(is_active=False, updated_at=func.now())
            .execution_options(synchronize_session=False)
        ).rowcount

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    created = sum(1 for key in parsed if key not in existing)

    logger.info(
        "Templates synced for channel %s: %d received, %d created, %d deactivated.",
        channel_id, len(items), created, deactivated,
    )

    return TemplateSyncResponse(
        received=len(items),
        created=created,
        updated=len(parsed) - created,
        deactivated=deactivated,
        skipped=skipped,
    )


# =========================
# SEND-TIME VALIDATION
# =========================

def resolve_for_send(
    db: Session,
    tenant_id: uuid.UUID,
    channel_id: uuid.UUID,
    name: str,
    language: str,
) -> MessageTemplate:
    template = (
        db.query(MessageTemplate)
        .filter(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.channel_connection_id == channel_id,
            MessageTemplate.name == name,
            MessageTemplate.language == language,
        )
        .first()
    )
    if template is None or not template.is_active:
        raise TemplateNotFoundError("Template not found for this channel. Sync templates first.")
    if not is_usable(template):
        raise TemplateNotUsableError(f"Template is not approved (status: {template.status}).")
    return template


def _check_text(value: str, label: str, limit: int) -> str:
    if not value.strip():
        raise TemplateParameterError(f"{label} cannot be blank.")
    if len(value) > limit:
        raise TemplateParameterError(f"{label} exceeds {limit} characters.")
    if any(ch in value for ch in "\n\r\t") or "     " in value:
        raise TemplateParameterError(
            f"{label} cannot contain new lines, tabs or more than 4 consecutive spaces."
        )
    return value


def _placeholders(text: str, named: bool) -> list[str]:
    if named:
        return list(dict.fromkeys(NAMED_RE.findall(text)))
    numbers = sorted({int(n) for n in POSITIONAL_RE.findall(text)})
    return [str(n) for n in numbers]


def _template_parts(template: MessageTemplate) -> tuple[dict | None, dict | None, list[dict]]:
    header = body = None
    buttons: list[dict] = []
    for component in template.components:
        kind = str(component.get("type", "")).upper()
        if kind == "HEADER":
            header = component
        elif kind == "BODY":
            body = component
        elif kind == "BUTTONS" and isinstance(component.get("buttons"), list):
            buttons = [b for b in component["buttons"] if isinstance(b, dict)]
    return header, body, buttons


def build_send_components(
    template: MessageTemplate,
    requested: list[TemplateComponentInput],
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Validate requested parameters against the template definition and
    build the Meta "components" payload. Returns (components, preview).
    """

    named = str((template.template_metadata or {}).get("parameter_format", "")).upper() == "NAMED"
    header, body, buttons = _template_parts(template)

    by_key: dict[tuple, TemplateComponentInput] = {}
    for component in requested:
        key = (component.type, component.index)
        if key in by_key:
            raise TemplateParameterError(f"Duplicate {component.type} component.")
        by_key[key] = component

    result: list[dict[str, Any]] = []

    # ---- header ----
    header_input = by_key.pop(("header", None), None)
    header_format = str(header.get("format", "TEXT")).upper() if header else None

    if header is None:
        if header_input:
            raise TemplateParameterError("This template has no header.")
    elif header_format == "TEXT":
        expected = _placeholders(str(header.get("text", "")), named)
        params = header_input.parameters if header_input else []
        if len(params) != len(expected) or any(p.type != "text" for p in params):
            raise TemplateParameterError(f"Header requires {len(expected)} text parameter(s).")
        if params:
            rendered_header_params: list[dict[str, str]] = []
            for position, param in enumerate(params):
                rendered: dict[str, str] = {
                    "type": "text",
                    "text": _check_text(param.text, "Header parameter", HEADER_TEXT_LIMIT),
                }
                if named:
                    if param.parameter_name != expected[position]:
                        raise TemplateParameterError(
                            f"Header parameter must be '{expected[position]}'."
                        )
                    rendered["parameter_name"] = param.parameter_name
                elif param.parameter_name is not None:
                    raise TemplateParameterError("This template uses positional parameters.")
                rendered_header_params.append(rendered)
            result.append({"type": "header", "parameters": rendered_header_params})
    elif header_format in MEDIA_HEADER_FORMATS:
        media_type = MEDIA_HEADER_FORMATS[header_format]
        params = header_input.parameters if header_input else []
        if len(params) != 1 or params[0].type != media_type:
            raise TemplateParameterError(f"Header requires one {media_type} parameter.")
        media: dict[str, Any] = {}
        if params[0].id:
            media["id"] = params[0].id
        else:
            media["link"] = params[0].link
        if media_type == "document" and params[0].filename:
            media["filename"] = params[0].filename
        result.append({"type": "header", "parameters": [{"type": media_type, media_type: media}]})
    else:
        raise TemplateParameterError("This template's header type is not supported yet.")

    # ---- body ----
    body_input = by_key.pop(("body", None), None)
    body_text = str(body.get("text", "")) if body else ""
    expected = _placeholders(body_text, named)
    params = body_input.parameters if body_input else []

    if len(params) != len(expected) or any(p.type != "text" for p in params):
        raise TemplateParameterError(f"Body requires {len(expected)} text parameter(s).")

    values: dict[str, str] = {}
    body_params: list[dict[str, Any]] = []
    for position, param in enumerate(params):
        value = _check_text(param.text, "Body parameter", 1024)
        if named:
            if param.parameter_name not in expected:
                raise TemplateParameterError(f"Unknown body parameter '{param.parameter_name}'.")
            if param.parameter_name in values:
                raise TemplateParameterError(f"Duplicate body parameter '{param.parameter_name}'.")
            values[param.parameter_name] = value
            body_params.append({"type": "text", "parameter_name": param.parameter_name, "text": value})
        else:
            if param.parameter_name is not None:
                raise TemplateParameterError("This template uses positional parameters.")
            values[expected[position]] = value
            body_params.append({"type": "text", "text": value})
    if body_params:
        result.append({"type": "body", "parameters": body_params})

    # ---- buttons ----
    for index, button in enumerate(buttons):
        kind = str(button.get("type", "")).upper()
        if kind == "URL" and POSITIONAL_RE.search(str(button.get("url", ""))):
            given = by_key.pop(("button", index), None)
            if not given or given.sub_type != "url" or len(given.parameters) != 1 or given.parameters[0].type != "text":
                raise TemplateParameterError(f"Button {index} requires one url text parameter.")
            result.append({
                "type": "button", "sub_type": "url", "index": str(index),
                "parameters": [{"type": "text", "text": _check_text(given.parameters[0].text, "Button parameter", 2000)}],
            })
        elif kind == "QUICK_REPLY":
            given = by_key.pop(("button", index), None)
            if given:
                if given.sub_type != "quick_reply" or len(given.parameters) != 1 or given.parameters[0].type != "payload":
                    raise TemplateParameterError(f"Button {index} accepts one payload parameter.")
                result.append({
                    "type": "button", "sub_type": "quick_reply", "index": str(index),
                    "parameters": [{"type": "payload", "payload": given.parameters[0].payload}],
                })

    if by_key:
        raise TemplateParameterError("Components do not match this template.")

    pattern = NAMED_RE if named else POSITIONAL_RE
    preview = pattern.sub(lambda m: values.get(m.group(1), m.group(0)), body_text) or None
    return result, preview
