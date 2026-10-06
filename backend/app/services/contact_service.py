import uuid

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.phone import InvalidPhoneNumberError, normalize_phone
from app.models import Contact
from app.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
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


def _normalize(phone: str) -> str:
    try:
        return normalize_phone(phone)
    except InvalidPhoneNumberError as exc:
        raise InvalidContactError(str(exc)) from None


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ContactAlreadyExistsError(DUPLICATE_PHONE) from None
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
    return to_contact_response(get_contact_model(db, tenant_id, contact_id))


def list_contacts(
    db: Session,
    tenant_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    phone: str | None = None,
) -> ContactListResponse:

    query = db.query(Contact).filter(Contact.tenant_id == tenant_id)

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

    total = query.count()

    contacts = (
        query.order_by(Contact.created_at.desc(), Contact.id.asc())
        .offset(page_offset(page, page_size))
        .limit(page_size)
        .all()
    )

    return ContactListResponse(
        items=[to_contact_response(contact) for contact in contacts],
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

    db.flush()
    return contact
