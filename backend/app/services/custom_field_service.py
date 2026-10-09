import re
import uuid
from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import ContactFieldValue, CustomFieldDefinition, CustomFieldType
from app.schemas.custom_field import (
    CustomFieldCreate,
    CustomFieldListResponse,
    CustomFieldResponse,
    CustomFieldUpdate,
)
from app.schemas.contact import ContactFieldValueOut

_SELECTABLE = {CustomFieldType.SELECT.value, CustomFieldType.MULTISELECT.value}


class CustomFieldServiceError(Exception):
    """Base custom field service error."""


class CustomFieldNotFoundError(CustomFieldServiceError):
    """Raised when a field definition is not in the current tenant."""


class CustomFieldAlreadyExistsError(CustomFieldServiceError):
    """Raised when a field key already exists in the tenant."""


class InvalidCustomFieldError(CustomFieldServiceError):
    """Raised when a field definition or value is invalid."""


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CustomFieldAlreadyExistsError("A custom field with this name already exists.") from None
    except SQLAlchemyError:
        db.rollback()
        raise


def _slug(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return (slug or "field")[:60]


def _unique_key(db: Session, tenant_id: uuid.UUID, label: str) -> str:
    base = _slug(label)
    existing = {
        row[0] for row in
        db.query(CustomFieldDefinition.key).filter(CustomFieldDefinition.tenant_id == tenant_id).all()
    }
    if base not in existing:
        return base
    for i in range(2, 1000):
        candidate = f"{base}_{i}"[:60]
        if candidate not in existing:
            return candidate
    return f"{base}_{uuid.uuid4().hex[:6]}"[:60]


def _to_response(field: CustomFieldDefinition) -> CustomFieldResponse:
    return CustomFieldResponse(
        id=field.id, label=field.label, key=field.key, field_type=field.field_type,
        options=field.options, created_at=field.created_at, updated_at=field.updated_at,
    )


def get_field_model(db: Session, tenant_id: uuid.UUID, field_id: uuid.UUID, for_update: bool = False) -> CustomFieldDefinition:
    query = db.query(CustomFieldDefinition).filter(
        CustomFieldDefinition.id == field_id, CustomFieldDefinition.tenant_id == tenant_id,
    )
    if for_update:
        query = query.with_for_update()
    field = query.first()
    if field is None:
        raise CustomFieldNotFoundError("Custom field not found.")
    return field


def list_fields(db: Session, tenant_id: uuid.UUID) -> CustomFieldListResponse:
    fields = (
        db.query(CustomFieldDefinition)
        .filter(CustomFieldDefinition.tenant_id == tenant_id)
        .order_by(CustomFieldDefinition.label.asc(), CustomFieldDefinition.id.asc())
        .all()
    )
    return CustomFieldListResponse(items=[_to_response(f) for f in fields], total=len(fields))


def _clean_options(field_type: str, options: list[str] | None) -> list[str] | None:
    if field_type in _SELECTABLE:
        cleaned = [o.strip() for o in (options or []) if o and o.strip()]
        if not cleaned:
            raise InvalidCustomFieldError("Select fields need at least one option.")
        # de-duplicate, preserve order
        return list(dict.fromkeys(cleaned))
    return None


def create_field(db: Session, tenant_id: uuid.UUID, data: CustomFieldCreate) -> CustomFieldResponse:
    options = _clean_options(data.field_type, data.options)
    field = CustomFieldDefinition(
        tenant_id=tenant_id, label=data.label, key=_unique_key(db, tenant_id, data.label),
        field_type=data.field_type, options=options,
    )
    db.add(field)
    _commit(db)
    db.refresh(field)
    return _to_response(field)


def update_field(db: Session, tenant_id: uuid.UUID, field_id: uuid.UUID, data: CustomFieldUpdate) -> CustomFieldResponse:
    field = get_field_model(db, tenant_id, field_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise InvalidCustomFieldError("At least one field must be provided.")
    if "label" in changes and changes["label"]:
        field.label = changes["label"]
    if "options" in changes:
        field.options = _clean_options(field.field_type, changes["options"])
    _commit(db)
    db.refresh(field)
    return _to_response(field)


def delete_field(db: Session, tenant_id: uuid.UUID, field_id: uuid.UUID) -> None:
    field = get_field_model(db, tenant_id, field_id, for_update=True)
    db.delete(field)  # its values cascade
    _commit(db)


# =========================
# VALUES
# =========================

def _coerce(field: CustomFieldDefinition, value: Any) -> Any:
    """Validate/normalize a value for a field type. None means clear."""
    if value is None:
        return None
    ftype = field.field_type
    if ftype == CustomFieldType.TEXT.value:
        if not isinstance(value, str):
            raise InvalidCustomFieldError(f"{field.label} must be text.")
        return value[:2000]
    if ftype == CustomFieldType.NUMBER.value:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidCustomFieldError(f"{field.label} must be a number.")
        return value
    if ftype == CustomFieldType.BOOLEAN.value:
        if not isinstance(value, bool):
            raise InvalidCustomFieldError(f"{field.label} must be true or false.")
        return value
    if ftype == CustomFieldType.DATE.value:
        if not isinstance(value, str):
            raise InvalidCustomFieldError(f"{field.label} must be a date (YYYY-MM-DD).")
        try:
            date.fromisoformat(value[:10])
        except ValueError:
            raise InvalidCustomFieldError(f"{field.label} must be a date (YYYY-MM-DD).") from None
        return value[:10]
    if ftype == CustomFieldType.SELECT.value:
        if not isinstance(value, str) or value not in (field.options or []):
            raise InvalidCustomFieldError(f"{field.label} must be one of its options.")
        return value
    if ftype == CustomFieldType.MULTISELECT.value:
        if not isinstance(value, list) or any(v not in (field.options or []) for v in value):
            raise InvalidCustomFieldError(f"{field.label} must be a subset of its options.")
        return list(dict.fromkeys(value))
    raise InvalidCustomFieldError("Unsupported field type.")


def set_contact_values(db: Session, tenant_id: uuid.UUID, contact_id: uuid.UUID, values: dict[uuid.UUID, Any]):
    """Set/clear custom-field values on one contact (tenant-scoped)."""
    from app.services import contact_service
    contact_service.get_contact_model(db, tenant_id, contact_id)  # 404 if not this tenant

    for field_id, raw in values.items():
        field = get_field_model(db, tenant_id, field_id)  # 404 if field is foreign
        coerced = _coerce(field, raw)
        existing = (
            db.query(ContactFieldValue)
            .filter(
                ContactFieldValue.tenant_id == tenant_id,
                ContactFieldValue.contact_id == contact_id,
                ContactFieldValue.field_id == field_id,
            )
            .with_for_update()
            .first()
        )
        if coerced is None:
            if existing is not None:
                db.delete(existing)
        elif existing is not None:
            existing.value = coerced
        else:
            db.add(ContactFieldValue(tenant_id=tenant_id, contact_id=contact_id, field_id=field_id, value=coerced))

    _commit(db)
    return contact_service.get_contact(db, tenant_id, contact_id)


def values_for(db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ContactFieldValueOut]]:
    """Batch-load custom-field values for a page of contacts (no N+1)."""
    if not contact_ids:
        return {}
    rows = (
        db.query(ContactFieldValue, CustomFieldDefinition)
        .join(
            CustomFieldDefinition,
            (CustomFieldDefinition.id == ContactFieldValue.field_id)
            & (CustomFieldDefinition.tenant_id == ContactFieldValue.tenant_id),
        )
        .filter(
            ContactFieldValue.tenant_id == tenant_id,
            ContactFieldValue.contact_id.in_(contact_ids),
        )
        .order_by(CustomFieldDefinition.label.asc())
        .all()
    )
    out: dict[uuid.UUID, list[ContactFieldValueOut]] = {}
    for value_row, field in rows:
        out.setdefault(value_row.contact_id, []).append(
            ContactFieldValueOut(
                field_id=field.id, key=field.key, label=field.label,
                field_type=field.field_type, value=value_row.value,
            )
        )
    return out
