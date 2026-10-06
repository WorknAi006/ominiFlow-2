import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, text, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, aliased

from app.models import (
    ACTIVE_CONVERSATION_STATUSES,
    ChannelConnection,
    Contact,
    Conversation,
    ConversationStatus,
    Message,
    TenantMembership,
    User,
)
from app.schemas.conversation import (
    ConversationChannelSummary,
    ConversationContactSummary,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    ConversationUserSummary,
    LastMessagePreview,
)
from app.services import realtime_service
from app.services.query_utils import like_pattern, page_offset

PREVIEW_LENGTH = 200


def _latest_message_order():
    """
    Recency of a message within a conversation: provider/send time when
    known, else insertion time. Matches how last_message_at advances (it
    never moves backwards), so a late-arriving older message never becomes
    the "last message" preview.
    """
    return (
        func.coalesce(Message.sent_at, Message.created_at).desc(),
        Message.created_at.desc(),
        Message.id.desc(),
    )


class ConversationServiceError(Exception):
    """Base conversation service error."""


class ConversationNotFoundError(ConversationServiceError):
    """Raised when the conversation does not exist in the current tenant."""


class ConversationConflictError(ConversationServiceError):
    """Raised when a status change would create a second active thread."""


class InvalidAssigneeError(ConversationServiceError):
    """Raised when the assignee is not an active member of the tenant."""


ACTIVE_CONFLICT = (
    "Another active conversation already exists for this contact and channel."
)


# =========================
# HELPERS
# =========================

def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConversationConflictError(ACTIVE_CONFLICT) from None
    except SQLAlchemyError:
        db.rollback()
        raise


def get_conversation_model(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    for_update: bool = False,
) -> Conversation:
    query = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant_id,
    )
    if for_update:
        query = query.with_for_update()

    conversation = query.first()
    if conversation is None:
        raise ConversationNotFoundError("Conversation not found.")
    return conversation


def _summary_statement(tenant_id: uuid.UUID):
    """
    One query for the list/detail view: conversation + contact + channel +
    assignee + last message preview (LATERAL, uses the
    (conversation_id, created_at) index). No JSON columns are loaded.
    """

    assignee = aliased(User)

    last_message = (
        select(
            Message.id,
            Message.direction,
            Message.message_type,
            Message.status,
            func.left(Message.text, PREVIEW_LENGTH).label("text"),
            Message.created_at,
        )
        .where(Message.conversation_id == Conversation.id)
        .order_by(*_latest_message_order())
        .limit(1)
        .lateral("last_message")
    )

    statement = (
        select(
            Conversation.id,
            Conversation.status,
            Conversation.subject,
            Conversation.unread_count,
            Conversation.last_message_at,
            Conversation.created_at,
            Conversation.updated_at,
            Contact.id.label("contact_id"),
            Contact.first_name.label("contact_first_name"),
            Contact.last_name.label("contact_last_name"),
            Contact.display_name.label("contact_display_name"),
            Contact.profile_name.label("contact_profile_name"),
            Contact.email.label("contact_email"),
            Contact.normalized_phone_number.label("contact_phone"),
            ChannelConnection.id.label("channel_id"),
            ChannelConnection.name.label("channel_name"),
            ChannelConnection.channel_type.label("channel_type"),
            assignee.id.label("assignee_id"),
            assignee.first_name.label("assignee_first_name"),
            assignee.last_name.label("assignee_last_name"),
            last_message.c.id.label("last_message_id"),
            last_message.c.direction.label("last_message_direction"),
            last_message.c.message_type.label("last_message_type"),
            last_message.c.status.label("last_message_status"),
            last_message.c.text.label("last_message_text"),
            last_message.c.created_at.label("last_message_created_at"),
        )
        .join(Contact, Contact.id == Conversation.contact_id)
        .join(ChannelConnection, ChannelConnection.id == Conversation.channel_connection_id)
        .outerjoin(assignee, assignee.id == Conversation.assigned_user_id)
        .outerjoin(last_message, true())
        .where(
            Conversation.tenant_id == tenant_id,
            Contact.tenant_id == tenant_id,
            ChannelConnection.tenant_id == tenant_id,
        )
    )

    return statement


def _row_to_response(row: Any) -> ConversationResponse:
    full_name = " ".join(
        part for part in (row.contact_first_name, row.contact_last_name) if part
    )

    return ConversationResponse(
        id=row.id,
        status=row.status,
        subject=row.subject,
        unread_count=row.unread_count,
        last_message_at=row.last_message_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        contact=ConversationContactSummary(
            id=row.contact_id,
            name=(
                row.contact_display_name or full_name or row.contact_profile_name
                or row.contact_phone or row.contact_email
            ),
            phone_number=row.contact_phone,
        ),
        channel=ConversationChannelSummary(
            id=row.channel_id,
            name=row.channel_name,
            channel_type=row.channel_type,
        ),
        assigned_user=(
            ConversationUserSummary(
                id=row.assignee_id,
                first_name=row.assignee_first_name,
                last_name=row.assignee_last_name,
            )
            if row.assignee_id else None
        ),
        last_message=(
            LastMessagePreview(
                id=row.last_message_id,
                direction=row.last_message_direction,
                message_type=row.last_message_type,
                status=row.last_message_status,
                text=row.last_message_text,
                created_at=row.last_message_created_at,
            )
            if row.last_message_id else None
        ),
    )


# =========================
# QUERIES
# =========================

def get_conversation(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> ConversationResponse:

    row = db.execute(
        _summary_statement(tenant_id).where(Conversation.id == conversation_id)
    ).first()

    if row is None:
        raise ConversationNotFoundError("Conversation not found.")

    return _row_to_response(row)


def list_conversations(
    db: Session,
    tenant_id: uuid.UUID,
    page: int,
    page_size: int,
    *,
    status: ConversationStatus | None = None,
    channel_id: uuid.UUID | None = None,
    assigned_user_id: uuid.UUID | None = None,
    unassigned: bool = False,
    unread: bool | None = None,
    search: str | None = None,
) -> ConversationListResponse:

    filters = [Conversation.tenant_id == tenant_id]

    if status is not None:
        filters.append(Conversation.status == status)
    if channel_id is not None:
        filters.append(Conversation.channel_connection_id == channel_id)
    if assigned_user_id is not None:
        filters.append(Conversation.assigned_user_id == assigned_user_id)
    if unassigned:
        filters.append(Conversation.assigned_user_id.is_(None))
    if unread is True:
        filters.append(Conversation.unread_count > 0)
    elif unread is False:
        filters.append(Conversation.unread_count == 0)
    if search:
        pattern = like_pattern(search)
        filters.append(
            or_(*(
                column.ilike(pattern, escape="\\")
                for column in (
                    Conversation.subject,
                    Contact.first_name,
                    Contact.last_name,
                    Contact.display_name,
                    Contact.profile_name,
                    Contact.email,
                    Contact.normalized_phone_number,
                )
            ))
        )

    total = db.execute(
        select(func.count())
        .select_from(Conversation)
        .join(Contact, Contact.id == Conversation.contact_id)
        .where(*filters)
    ).scalar_one()

    rows = db.execute(
        _summary_statement(tenant_id)
        .where(*filters)
        .order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.created_at.desc(),
            Conversation.id.asc(),
        )
        .offset(page_offset(page, page_size))
        .limit(page_size)
    ).all()

    return ConversationListResponse(
        items=[_row_to_response(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


# =========================
# COMMANDS (API)
# =========================

def create_conversation(
    db: Session,
    tenant_id: uuid.UUID,
    contact_id: uuid.UUID,
    channel_id: uuid.UUID,
    subject: str | None = None,
) -> ConversationResponse:
    conversation = get_or_create_conversation(db, tenant_id, contact_id, channel_id)
    if subject is not None:
        conversation.subject = subject
    _commit(db)
    return get_conversation(db, tenant_id, conversation.id)


def update_conversation(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
) -> ConversationResponse:

    conversation = get_conversation_model(db, tenant_id, conversation_id, for_update=True)

    for field, value in data.model_dump(include={"subject"}, exclude_unset=True).items():
        setattr(conversation, field, value)

    _commit(db)
    return get_conversation(db, tenant_id, conversation_id)


def assign_conversation(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    assignee_id: uuid.UUID | None,
) -> ConversationResponse:

    conversation = get_conversation_model(db, tenant_id, conversation_id, for_update=True)

    if assignee_id is not None:
        is_member = (
            db.query(TenantMembership.id)
            .join(User, User.id == TenantMembership.user_id)
            .filter(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == assignee_id,
                TenantMembership.status == "active",
                User.is_active.is_(True),
            )
            .first()
        )
        if not is_member:
            raise InvalidAssigneeError(
                "Assignee must be an active member of this workspace."
            )

    conversation.assigned_user_id = assignee_id

    _commit(db)
    return get_conversation(db, tenant_id, conversation_id)


def change_status(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    status: ConversationStatus,
) -> ConversationResponse:
    """
    Reopening is rejected (409) if the contact already has another active
    conversation on the same channel (enforced by a partial unique index).
    """

    conversation = get_conversation_model(db, tenant_id, conversation_id, for_update=True)
    conversation.status = status

    _commit(db)
    return get_conversation(db, tenant_id, conversation_id)


def mark_as_read(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> ConversationResponse:

    conversation = get_conversation_model(db, tenant_id, conversation_id, for_update=True)
    changed = conversation.unread_count > 0
    conversation.unread_count = 0

    realtime_event = None
    if changed:
        db.flush()
        realtime_event = realtime_service.build_conversation_updated_event(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            **get_update_snapshot(db, conversation),
        )

    _commit(db)
    if realtime_event is not None:
        realtime_service.publish_event(realtime_event)
    return get_conversation(db, tenant_id, conversation_id)


# =========================
# INTERNAL (event processing / messaging; caller commits)
# =========================

def get_or_create_conversation(
    db: Session,
    tenant_id: uuid.UUID,
    contact_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> Conversation:
    """
    Return the active (open/pending) conversation for contact + channel,
    creating an open one if none exists. Race-safe via the partial unique
    index: concurrent callers converge on the same row.
    """

    db.execute(
        insert(Conversation)
        .values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contact_id=contact_id,
            channel_connection_id=channel_id,
            status=ConversationStatus.OPEN,
            unread_count=0,
        )
        .on_conflict_do_nothing(
            index_elements=["tenant_id", "contact_id", "channel_connection_id"],
            index_where=text("status IN ('open', 'pending')"),
        )
    )

    return (
        db.query(Conversation)
        .filter(
            Conversation.tenant_id == tenant_id,
            Conversation.contact_id == contact_id,
            Conversation.channel_connection_id == channel_id,
            Conversation.status.in_(ACTIVE_CONVERSATION_STATUSES),
        )
        .populate_existing()
        .one()
    )


def record_activity(
    db: Session,
    conversation: Conversation,
    occurred_at: datetime,
    inbound: bool,
) -> None:
    """
    Atomically bump last_message_at (never backwards) and, for inbound
    messages, unread_count.
    """

    values: dict[str, Any] = {
        "last_message_at": func.greatest(
            func.coalesce(Conversation.last_message_at, occurred_at),
            occurred_at,
        ),
        "updated_at": func.now(),
    }
    if inbound:
        values["unread_count"] = Conversation.unread_count + 1

    db.execute(
        update(Conversation)
        .where(
            Conversation.id == conversation.id,
            Conversation.tenant_id == conversation.tenant_id,
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    db.expire(conversation)


def increment_unread(db: Session, conversation: Conversation, by: int = 1) -> None:
    db.execute(
        update(Conversation)
        .where(Conversation.id == conversation.id)
        .values(unread_count=Conversation.unread_count + by)
        .execution_options(synchronize_session=False)
    )
    db.expire(conversation)


def get_update_snapshot(db: Session, conversation: Conversation) -> dict[str, Any]:
    """
    Current list-relevant state of a conversation (inside the caller's
    transaction): status, unread count, last activity and the latest
    message by the same ordering as the conversation list.
    """

    db.refresh(conversation, attribute_names=["status", "unread_count", "last_message_at"])

    latest = db.execute(
        select(Message.id, Message.direction, Message.message_type, Message.text)
        .where(
            Message.conversation_id == conversation.id,
            Message.tenant_id == conversation.tenant_id,
        )
        .order_by(*_latest_message_order())
        .limit(1)
    ).first()

    return {
        "status": conversation.status,
        "unread_count": conversation.unread_count,
        "last_message_at": conversation.last_message_at,
        "last_message_id": latest.id if latest else None,
        "last_message_direction": latest.direction if latest else None,
        "last_message_type": latest.message_type if latest else None,
        "last_message_text": latest.text if latest else None,
    }
