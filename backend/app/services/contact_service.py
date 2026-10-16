import uuid

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.phone import InvalidPhoneNumberError, normalize_phone, to_whatsapp_id
from app.models import (
    ChannelType,
    Contact,
    ContactFieldValue,
    ContactIdentity,
    ContactTag,
    CustomFieldDefinition,
    Tag,
)
from app.schemas.contact import (
    ContactCreate,
    ContactFieldValueOut,
    ContactIdentitySummary,
    ContactImportResult,
    ContactImportRow,
    ContactListResponse,
    ContactResponse,
    ContactTagSummary,
    ContactUpdate,
)
from app.services.query_utils import like_pattern, page_offset


class ContactServiceError(Exception):
    """Base contact service error."""


class ContactNotFoundError(ContactServiceError):
    """Raised when the contact does not exist in the current tenant."""


class ContactAlreadyExistsError(ContactServiceError):
    """Raised when the phone number is already used by another contact."""


class InvalidContactError(ContactServiceError):
    """Raised when contact data is invalid."""


DUPLICATE_PHONE = "A contact with this phone number already exists."


# =========================
# HELPERS
# =========================

def contact_name(contact: Contact) -> str | None:
    full_name = " ".join(
        part for part in (contact.first_name, contact.last_name) if part
    )
    return (
        contact.display_name
        or full_name
        or contact.profile_name
        or contact.normalized_phone_number
        or contact.email
    )


def to_contact_response(contact: Contact) -> ContactResponse:
    return ContactResponse(
        id=contact.id,
        name=contact_name(contact),
        phone_number=contact.phone_number,
        normalized_phone_number=contact.normalized_phone_number,
        email=contact.email,
        first_name=contact.first_name,
        last_name=contact.last_name,
        display_name=contact.display_name,
        profile_name=contact.profile_name,
        avatar_url=contact.avatar_url,
        is_blocked=contact.is_blocked,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


# =========================
# ENRICHMENT (identities / tags) — batched, no N+1
# =========================

def _identities_for(db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ContactIdentitySummary]]:
    if not contact_ids:
        return {}
    rows = (
        db.query(ContactIdentity)
        .filter(ContactIdentity.tenant_id == tenant_id, ContactIdentity.contact_id.in_(contact_ids))
        .order_by(ContactIdentity.channel_type.asc())
        .all()
    )
    out: dict[uuid.UUID, list[ContactIdentitySummary]] = {}
    for row in rows:
        out.setdefault(row.contact_id, []).append(
            ContactIdentitySummary(
                channel_type=row.channel_type, external_id=row.external_id, display_name=row.display_name,
            )
        )
    return out


def _tags_for(db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ContactTagSummary]]:
    if not contact_ids:
        return {}
    rows = (
        db.query(ContactTag.contact_id, Tag)
        .join(Tag, (Tag.id == ContactTag.tag_id) & (Tag.tenant_id == ContactTag.tenant_id))
        .filter(ContactTag.tenant_id == tenant_id, ContactTag.contact_id.in_(contact_ids))
        .order_by(Tag.name.asc())
        .all()
    )
    out: dict[uuid.UUID, list[ContactTagSummary]] = {}
    for contact_id, tag in rows:
        out.setdefault(contact_id, []).append(
            ContactTagSummary(id=tag.id, name=tag.name, color=tag.color)
        )
    return out


def _field_values_for(db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ContactFieldValueOut]]:
    if not contact_ids:
        return {}
    rows = (
        db.query(ContactFieldValue, CustomFieldDefinition)
        .join(
            CustomFieldDefinition,
            (CustomFieldDefinition.id == ContactFieldValue.field_id)
            & (CustomFieldDefinition.tenant_id == ContactFieldValue.tenant_id),
        )
        .filter(ContactFieldValue.tenant_id == tenant_id, ContactFieldValue.contact_id.in_(contact_ids))
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


def _enrich(contacts: list[Contact], identities, tags, field_values=None) -> list[ContactResponse]:
    field_values = field_values or {}
    result = []
    for contact in contacts:
        response = to_contact_response(contact)
        response.identities = identities.get(contact.id, [])
        response.tags = tags.get(contact.id, [])
        response.field_values = field_values.get(contact.id, [])
        result.append(response)
    return result


def _normalize(phone: str) -> str:
    try:
        return normalize_phone(phone)
    except InvalidPhoneNumberError as exc:
        raise InvalidContactError(str(exc)) from None


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )
        if constraint_name == "uq_contacts_tenant_normalized_phone":
            raise ContactAlreadyExistsError(DUPLICATE_PHONE) from None
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def get_contact_model(
    db: Session,
    tenant_id: uuid.UUID,
    contact_id: uuid.UUID,
    for_update: bool = False,
) -> Contact:
    query = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.tenant_id == tenant_id,
    )
    if for_update:
        query = query.with_for_update()

    contact = query.first()
    if contact is None:
        raise ContactNotFoundError("Contact not found.")
    return contact


# =========================
# QUERIES
# =========================

def find_by_phone(
    db: Session,
    tenant_id: uuid.UUID,
    phone: str,
) -> Contact | None:
    return (
        db.query(Contact)
        .filter(
            Contact.tenant_id == tenant_id,
            Contact.normalized_phone_number == _normalize(phone),
        )
        .first()
    )


def get_contact(
    db: Session,
    tenant_id: uuid.UUID,
    contact_id: uuid.UUID,
) -> ContactResponse:
    contact = get_contact_model(db, tenant_id, contact_id)
    identities = _identities_for(db, tenant_id, [contact.id])
    tags = _tags_for(db, tenant_id, [contact.id])
    field_values = _field_values_for(db, tenant_id, [contact.id])
    return _enrich([contact], identities, tags, field_values)[0]


def _filtered_query(
    db: Session,
    tenant_id: uuid.UUID,
    search: str | None = None,
    phone: str | None = None,
    tag_id: uuid.UUID | None = None,
    channel_type: str | None = None,
    source: str | None = None,
):
    query = db.query(Contact).filter(Contact.tenant_id == tenant_id)

    # Source is derived: a contact with a channel identity arrived through the
    # Inbox; one without is manually added. (No external CRM sources exist.)
    if source in ("inbox", "manual"):
        has_identity = (
            db.query(ContactIdentity.id)
            .filter(ContactIdentity.tenant_id == tenant_id, ContactIdentity.contact_id == Contact.id)
            .exists()
        )
        query = query.filter(has_identity if source == "inbox" else ~has_identity)

    if phone:
        query = query.filter(Contact.normalized_phone_number == _normalize(phone))

    if search:
        pattern = like_pattern(search)
        query = query.filter(
            or_(*(
                column.ilike(pattern, escape="\\")
                for column in (
                    Contact.first_name,
                    Contact.last_name,
                    Contact.display_name,
                    Contact.profile_name,
                    Contact.email,
                    Contact.phone_number,
                    Contact.normalized_phone_number,
                )
            ))
        )

    if tag_id is not None:
        query = query.filter(
            db.query(ContactTag.id)
            .filter(
                ContactTag.tenant_id == tenant_id,
                ContactTag.contact_id == Contact.id,
                ContactTag.tag_id == tag_id,
            )
            .exists()
        )

    if channel_type:
        query = query.filter(
            db.query(ContactIdentity.id)
            .filter(
                ContactIdentity.tenant_id == tenant_id,
                ContactIdentity.contact_id == Contact.id,
                ContactIdentity.channel_type == channel_type,
            )
            .exists()
        )

    return query


def list_contacts(
    db: Session,
    tenant_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    phone: str | None = None,
    tag_id: uuid.UUID | None = None,
    channel_type: str | None = None,
    source: str | None = None,
) -> ContactListResponse:

    query = _filtered_query(db, tenant_id, search, phone, tag_id, channel_type, source)

    total = query.count()

    contacts = (
        query.order_by(Contact.created_at.desc(), Contact.id.asc())
        .offset(page_offset(page, page_size))
        .limit(page_size)
        .all()
    )

    ids = [contact.id for contact in contacts]
    identities = _identities_for(db, tenant_id, ids)
    tags = _tags_for(db, tenant_id, ids)
    field_values = _field_values_for(db, tenant_id, ids)

    return ContactListResponse(
        items=_enrich(contacts, identities, tags, field_values),
        total=total,
        page=page,
        page_size=page_size,
    )


def search_contacts(
    db: Session,
    tenant_id: uuid.UUID,
    search: str,
    limit: int = 20,
) -> list[ContactResponse]:
    return list_contacts(db, tenant_id, 1, limit, search=search).items


# =========================
# COMMANDS
# =========================

def create_contact(
    db: Session,
    tenant_id: uuid.UUID,
    data: ContactCreate,
) -> ContactResponse:

    normalized = _normalize(data.phone_number) if data.phone_number else None

    if normalized and find_by_phone(db, tenant_id, normalized):
        raise ContactAlreadyExistsError(DUPLICATE_PHONE)

    contact = Contact(
        tenant_id=tenant_id,
        phone_number=data.phone_number,
        normalized_phone_number=normalized,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        display_name=data.display_name,
        is_blocked=False,
    )

    db.add(contact)
    _commit(db)
    db.refresh(contact)

    # Fire "new contact created" automation rules (best-effort).
    from app.services import automation_service
    automation_service.on_contact_created(db, contact)

    return to_contact_response(contact)


def update_contact(
    db: Session,
    tenant_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactUpdate,
) -> ContactResponse:

    contact = get_contact_model(db, tenant_id, contact_id, for_update=True)

    changes = data.model_dump(
        include={
            "phone_number", "email", "first_name", "last_name",
            "display_name", "is_blocked",
        },
        exclude_unset=True,
    )

    if "phone_number" in changes:
        normalized = _normalize(changes["phone_number"])
        existing = find_by_phone(db, tenant_id, normalized)
        if existing is not None and existing.id != contact.id:
            raise ContactAlreadyExistsError(DUPLICATE_PHONE)
        contact.normalized_phone_number = normalized

    for field, value in changes.items():
        setattr(contact, field, value)

    if not contact.normalized_phone_number and not contact.email:
        raise InvalidContactError("A contact needs a phone number or email.")

    _commit(db)
    db.refresh(contact)

    return to_contact_response(contact)


def get_or_create_by_phone(
    db: Session,
    tenant_id: uuid.UUID,
    phone: str,
    *,
    external_identifier: str | None = None,
    profile_name: str | None = None,
) -> Contact:
    """
    Race-safe find-or-create inside the caller's transaction (no commit).
    The partial unique index on (tenant_id, normalized_phone_number) is
    the source of truth; concurrent callers converge on one row.
    """

    normalized = _normalize(phone)

    db.execute(
        insert(Contact)
        .values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            phone_number=phone,
            normalized_phone_number=normalized,
            external_identifier=external_identifier,
            profile_name=profile_name,
            is_blocked=False,
        )
        .on_conflict_do_nothing(
            index_elements=["tenant_id", "normalized_phone_number"],
            index_where=text("normalized_phone_number IS NOT NULL"),
        )
    )

    contact = (
        db.query(Contact)
        .filter(
            Contact.tenant_id == tenant_id,
            Contact.normalized_phone_number == normalized,
        )
        .populate_existing()
        .one()
    )

    # Keep provider-reported data fresh without touching team-set fields.
    if profile_name and contact.profile_name != profile_name:
        contact.profile_name = profile_name
    if external_identifier and not contact.external_identifier:
        contact.external_identifier = external_identifier

    # Record the channel-agnostic WhatsApp identity (wa_id) for this contact
    # alongside the existing phone-based dedup, so the same person can later
    # hold identities on other channels. The phone index stays the source of
    # truth for WhatsApp contact resolution.
    _ensure_identity(
        db,
        tenant_id,
        contact.id,
        ChannelType.WHATSAPP,
        external_identifier or to_whatsapp_id(normalized),
        display_name=profile_name,
    )

    db.flush()
    return contact


def resolve_inbound_contact(
    db: Session,
    tenant_id: uuid.UUID,
    channel_type: ChannelType | str,
    external_sender_id: str,
    *,
    phone_hint: str | None = None,
    display_name: str | None = None,
) -> Contact:
    """
    Resolve the contact for an inbound event by its channel identity. When
    the channel's sender id is a phone number (phone_hint, e.g. WhatsApp),
    the existing phone-based find-or-create is used so phone dedup and the
    WhatsApp identity recording behave exactly as before. Channels without
    a phone resolve purely through ContactIdentity.
    """
    if phone_hint is not None:
        return get_or_create_by_phone(
            db,
            tenant_id,
            phone_hint,
            external_identifier=external_sender_id,
            profile_name=display_name,
        )
    return get_or_create_by_identity(
        db, tenant_id, channel_type, external_sender_id, display_name=display_name,
    )


def _ensure_identity(
    db: Session,
    tenant_id: uuid.UUID,
    contact_id: uuid.UUID,
    channel_type: ChannelType | str,
    external_id: str,
    *,
    display_name: str | None = None,
) -> None:
    """
    Idempotently attach a channel identity to an existing contact. Safe to
    call repeatedly: the partial unique index converges concurrent callers.
    """
    db.execute(
        insert(ContactIdentity)
        .values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contact_id=contact_id,
            channel_type=str(channel_type),
            external_id=external_id,
            display_name=display_name,
        )
        .on_conflict_do_nothing(
            index_elements=["tenant_id", "channel_type", "external_id"],
        )
    )


def find_by_identity(
    db: Session,
    tenant_id: uuid.UUID,
    channel_type: ChannelType | str,
    external_id: str,
) -> Contact | None:
    identity = (
        db.query(ContactIdentity)
        .filter(
            ContactIdentity.tenant_id == tenant_id,
            ContactIdentity.channel_type == str(channel_type),
            ContactIdentity.external_id == external_id,
        )
        .first()
    )
    if identity is None:
        return None
    return db.get(Contact, identity.contact_id)


def get_or_create_by_identity(
    db: Session,
    tenant_id: uuid.UUID,
    channel_type: ChannelType | str,
    external_id: str,
    display_name: str | None = None,
) -> Contact:
    """
    Resolve a contact by its channel identity, creating both the contact and
    the identity when none exists. Tenant-safe: the same external_id in a
    different tenant resolves to a different contact. Race-safe via the
    (tenant_id, channel_type, external_id) unique index inside the caller's
    transaction (no commit).
    """

    existing = find_by_identity(db, tenant_id, channel_type, external_id)
    if existing is not None:
        return existing

    contact = Contact(
        tenant_id=tenant_id,
        display_name=display_name,
        is_blocked=False,
    )
    db.add(contact)
    db.flush()

    inserted = db.execute(
        insert(ContactIdentity)
        .values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contact_id=contact.id,
            channel_type=str(channel_type),
            external_id=external_id,
            display_name=display_name,
        )
        .on_conflict_do_nothing(
            index_elements=["tenant_id", "channel_type", "external_id"],
        )
        .returning(ContactIdentity.id)
    ).scalar_one_or_none()

    if inserted is None:
        # A concurrent caller created the identity first; drop the contact we
        # speculatively created and return the winning contact.
        db.delete(contact)
        db.flush()
        winner = find_by_identity(db, tenant_id, channel_type, external_id)
        assert winner is not None  # the conflicting identity must exist
        return winner

    return contact


# =========================
# DELETE (tenant-scoped; dependents cascade at the DB level)
# =========================

DELETE_ALL_CONFIRM = "DELETE ALL"


def filter_owned_contact_ids(
    db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Return only the ids that belong to this tenant (drops foreign/unknown)."""
    unique = list(dict.fromkeys(contact_ids))
    if not unique:
        return []
    rows = (
        db.query(Contact.id)
        .filter(Contact.tenant_id == tenant_id, Contact.id.in_(unique))
        .all()
    )
    return [row[0] for row in rows]


def delete_contact(db: Session, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    """
    Delete one contact in the current tenant. The DB cascades its identities,
    tags, conversations, messages and automation executions (all contact_id
    FKs are ON DELETE CASCADE). Other tenants are never touched.
    """
    contact = get_contact_model(db, tenant_id, contact_id, for_update=True)
    db.delete(contact)
    _commit(db)


def bulk_delete_contacts(
    db: Session, tenant_id: uuid.UUID, contact_ids: list[uuid.UUID],
) -> int:
    """Delete several contacts in this tenant; returns the number removed."""
    owned = filter_owned_contact_ids(db, tenant_id, contact_ids)
    if not owned:
        return 0
    deleted = (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant_id, Contact.id.in_(owned))
        .delete(synchronize_session=False)
    )
    _commit(db)
    return int(deleted)


def delete_all_contacts(db: Session, tenant_id: uuid.UUID) -> int:
    """Delete every contact in this tenant (high-risk; caller confirms)."""
    deleted = (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant_id)
        .delete(synchronize_session=False)
    )
    _commit(db)
    return int(deleted)


# =========================
# EXPORT (streamed, tenant-scoped, honours search/filters)
# =========================

EXPORT_COLUMNS = [
    "name", "first_name", "last_name", "phone_number", "email",
    "channels", "tags", "is_blocked", "created_at",
]


def iter_export_rows(
    db: Session,
    tenant_id: uuid.UUID,
    search: str | None = None,
    tag_id: uuid.UUID | None = None,
    channel_type: str | None = None,
    chunk_size: int = 500,
):
    """
    Yield one dict per contact for CSV export, paginating server-side so a
    large tenant never loads entirely into memory. Only this tenant's
    contacts are ever returned.
    """
    base = _filtered_query(db, tenant_id, search, None, tag_id, channel_type).order_by(
        Contact.created_at.desc(), Contact.id.asc(),
    )
    offset = 0
    while True:
        chunk = base.offset(offset).limit(chunk_size).all()
        if not chunk:
            break
        ids = [c.id for c in chunk]
        identities = _identities_for(db, tenant_id, ids)
        tags = _tags_for(db, tenant_id, ids)
        for contact in chunk:
            channels = sorted({i.channel_type for i in identities.get(contact.id, [])})
            tag_names = [t.name for t in tags.get(contact.id, [])]
            yield {
                "name": contact_name(contact) or "",
                "first_name": contact.first_name or "",
                "last_name": contact.last_name or "",
                "phone_number": contact.phone_number or contact.normalized_phone_number or "",
                "email": contact.email or "",
                "channels": ", ".join(channels),
                "tags": ", ".join(tag_names),
                "is_blocked": "yes" if contact.is_blocked else "no",
                "created_at": contact.created_at.isoformat() if contact.created_at else "",
            }
        if len(chunk) < chunk_size:
            break
        offset += chunk_size


# =========================
# IMPORT (CSV rows; tenant-scoped, deduped by phone)
# =========================

def import_contacts(db: Session, tenant_id: uuid.UUID, rows: list[ContactImportRow]) -> ContactImportResult:
    """
    Create contacts from parsed CSV rows. Rows without a phone or email are
    skipped; invalid phones are reported as errors; duplicates (by normalized
    phone, in the DB or within the batch) are skipped. Never touches another
    tenant's data.
    """
    existing_phones = {
        row[0] for row in
        db.query(Contact.normalized_phone_number)
        .filter(Contact.tenant_id == tenant_id, Contact.normalized_phone_number.isnot(None))
        .all()
    }
    seen = set(existing_phones)
    imported, skipped, errors = 0, 0, []

    for index, row in enumerate(rows, start=1):
        phone = (row.phone_number or "").strip() or None
        email = (row.email or "").strip().lower() or None
        if not phone and not email:
            skipped += 1
            continue

        normalized = None
        if phone:
            try:
                normalized = normalize_phone(phone)
            except InvalidPhoneNumberError:
                errors.append(f"Row {index}: invalid phone number.")
                continue
            if normalized in seen:
                skipped += 1
                continue

        contact = Contact(
            tenant_id=tenant_id,
            phone_number=phone,
            normalized_phone_number=normalized,
            email=email,
            first_name=row.first_name or None,
            last_name=row.last_name or None,
            display_name=row.display_name or None,
            is_blocked=False,
        )
        db.add(contact)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            # Re-seed the dedupe set once and skip this row.
            skipped += 1
            seen = {
                r[0] for r in
                db.query(Contact.normalized_phone_number)
                .filter(Contact.tenant_id == tenant_id, Contact.normalized_phone_number.isnot(None))
                .all()
            }
            continue

        if normalized:
            seen.add(normalized)
        imported += 1

    _commit(db)
    return ContactImportResult(imported=imported, skipped=skipped, errors=errors[:50])
