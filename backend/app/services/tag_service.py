import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import ContactTag, Tag
from app.schemas.tag import TagCreate, TagListResponse, TagResponse, TagUpdate


class TagServiceError(Exception):
    """Base tag service error."""


class TagNotFoundError(TagServiceError):
    """Raised when a tag does not exist in the current tenant."""


class TagAlreadyExistsError(TagServiceError):
    """Raised when a tag name already exists in the tenant."""


class InvalidTagError(TagServiceError):
    """Raised when a referenced tag is not valid for the tenant."""


DUPLICATE_NAME = "A tag with this name already exists."


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise TagAlreadyExistsError(DUPLICATE_NAME) from None
    except SQLAlchemyError:
        db.rollback()
        raise


def _counts(db: Session, tenant_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not tag_ids:
        return {}
    rows = (
        db.query(ContactTag.tag_id, func.count(ContactTag.contact_id))
        .filter(ContactTag.tenant_id == tenant_id, ContactTag.tag_id.in_(tag_ids))
        .group_by(ContactTag.tag_id)
        .all()
    )
    return {tag_id: count for tag_id, count in rows}


def _to_response(tag: Tag, count: int = 0) -> TagResponse:
    return TagResponse(
        id=tag.id, name=tag.name, color=tag.color, contact_count=count,
        created_at=tag.created_at, updated_at=tag.updated_at,
    )


def get_tag_model(db: Session, tenant_id: uuid.UUID, tag_id: uuid.UUID, for_update: bool = False) -> Tag:
    query = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id)
    if for_update:
        query = query.with_for_update()
    tag = query.first()
    if tag is None:
        raise TagNotFoundError("Tag not found.")
    return tag


def list_tags(db: Session, tenant_id: uuid.UUID) -> TagListResponse:
    tags = (
        db.query(Tag)
        .filter(Tag.tenant_id == tenant_id)
        .order_by(Tag.name.asc(), Tag.id.asc())
        .all()
    )
    counts = _counts(db, tenant_id, [tag.id for tag in tags])
    items = [_to_response(tag, counts.get(tag.id, 0)) for tag in tags]
    return TagListResponse(items=items, total=len(items))


def create_tag(db: Session, tenant_id: uuid.UUID, data: TagCreate) -> TagResponse:
    tag = Tag(tenant_id=tenant_id, name=data.name, color=data.color)
    db.add(tag)
    _commit(db)
    db.refresh(tag)
    return _to_response(tag, 0)


def update_tag(db: Session, tenant_id: uuid.UUID, tag_id: uuid.UUID, data: TagUpdate) -> TagResponse:
    tag = get_tag_model(db, tenant_id, tag_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise InvalidTagError("At least one field must be provided.")
    for field, value in changes.items():
        if value is not None:
            setattr(tag, field, value)
    _commit(db)
    db.refresh(tag)
    return _to_response(tag, _counts(db, tenant_id, [tag.id]).get(tag.id, 0))


def delete_tag(db: Session, tenant_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    tag = get_tag_model(db, tenant_id, tag_id, for_update=True)
    # Only the tag and its associations are removed (CASCADE); contacts stay.
    db.delete(tag)
    _commit(db)


def validate_tag_ids(db: Session, tenant_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Return the subset of tag_ids that belong to this tenant, raising if any is foreign."""
    unique_ids = list(dict.fromkeys(tag_ids))
    if not unique_ids:
        return []
    found = {
        row[0] for row in
        db.query(Tag.id).filter(Tag.tenant_id == tenant_id, Tag.id.in_(unique_ids)).all()
    }
    missing = [tid for tid in unique_ids if tid not in found]
    if missing:
        raise InvalidTagError("One or more tags do not belong to this workspace.")
    return unique_ids


def _add_links(db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]) -> None:
    for contact_id in contact_ids:
        for tag_id in tag_ids:
            db.execute(
                insert(ContactTag)
                .values(id=uuid.uuid4(), tenant_id=tenant_id, contact_id=contact_id, tag_id=tag_id)
                .on_conflict_do_nothing(index_elements=["contact_id", "tag_id"])
            )


def _remove_links(db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]) -> None:
    if not tag_ids:
        return
    db.query(ContactTag).filter(
        ContactTag.tenant_id == tenant_id,
        ContactTag.contact_id.in_(contact_ids),
        ContactTag.tag_id.in_(tag_ids),
    ).delete(synchronize_session=False)


def set_contact_tags(db: Session, tenant_id: uuid.UUID, contact_id: uuid.UUID, tag_ids: list[uuid.UUID]):
    """Replace the full tag set on one contact (tenant-scoped)."""
    from app.services import contact_service
    contact_service.get_contact_model(db, tenant_id, contact_id)  # 404 if not this tenant
    valid = validate_tag_ids(db, tenant_id, tag_ids)
    existing = {
        r[0] for r in db.query(ContactTag.tag_id).filter(
            ContactTag.tenant_id == tenant_id, ContactTag.contact_id == contact_id,
        ).all()
    }
    db.query(ContactTag).filter(
        ContactTag.tenant_id == tenant_id, ContactTag.contact_id == contact_id,
    ).delete(synchronize_session=False)
    _add_links(db, tenant_id, [contact_id], valid)
    _commit(db)
    _fire_tag_added(db, tenant_id, contact_id, [t for t in valid if t not in existing])
    return contact_service.get_contact(db, tenant_id, contact_id)


def bulk_apply_tags(
    db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID],
    add_tag_ids: list[uuid.UUID], remove_tag_ids: list[uuid.UUID],
) -> int:
    """Add and/or remove tags across several of this tenant's contacts."""
    from app.services import contact_service
    owned = contact_service.filter_owned_contact_ids(db, tenant_id, contact_ids)
    if not owned:
        return 0
    add = validate_tag_ids(db, tenant_id, add_tag_ids)
    remove = validate_tag_ids(db, tenant_id, remove_tag_ids)
    _remove_links(db, tenant_id, owned, remove)
    _add_links(db, tenant_id, owned, add)
    _commit(db)
    if add:
        for contact_id in owned:
            _fire_tag_added(db, tenant_id, contact_id, add)
    return len(owned)


def _fire_tag_added(db: Session, tenant_id: uuid.UUID, contact_id: uuid.UUID, added_tag_ids: list[uuid.UUID]) -> None:
    """Best-effort: run 'tag added to contact' automation rules."""
    if not added_tag_ids:
        return
    from app.services import automation_service
    automation_service.on_tags_added(db, tenant_id, contact_id, added_tag_ids)
