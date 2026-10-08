import uuid

from fastapi import APIRouter, Depends, Header, Query, status

from app.api.dependencies import (
    CurrentTenant,
    CurrentUser,
    DbSession,
    require_permission,
)
from app.api.errors import service_errors
from app.models import ConversationStatus
from app.schemas.conversation import (
    ConversationAssign,
    ConversationListResponse,
    ConversationResponse,
    ConversationStatusUpdate,
    ConversationUpdate,
)
from app.schemas.message import MessageCreate, MessageListResponse, MessageResponse
from app.services import conversation_service, message_service, outbound_message_service
from app.services.conversation_service import (
    ConversationConflictError,
    ConversationNotFoundError,
    InvalidAssigneeError,
)
from app.services.template_service import (
    TemplateNotFoundError,
    TemplateNotUsableError,
    TemplateParameterError,
)
from app.services.outbound_message_service import (
    ChannelNotConnectedError,
    CredentialsUnavailableError,
    IdempotencyConflictError,
    InvalidReplyError,
    MessageSendFailedError,
    ProviderNotConfiguredForSendError,
    RecipientUnavailableError,
    UnsupportedChannelError,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

ERRORS = {
    ConversationNotFoundError: status.HTTP_404_NOT_FOUND,
    ConversationConflictError: status.HTTP_409_CONFLICT,
    InvalidAssigneeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

SEND_ERRORS = {
    **ERRORS,
    UnsupportedChannelError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidReplyError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ChannelNotConnectedError: status.HTTP_409_CONFLICT,
    RecipientUnavailableError: status.HTTP_409_CONFLICT,
    MessageSendFailedError: status.HTTP_502_BAD_GATEWAY,
    CredentialsUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ProviderNotConfiguredForSendError: status.HTTP_503_SERVICE_UNAVAILABLE,
    TemplateNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    TemplateNotUsableError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    TemplateParameterError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    IdempotencyConflictError: status.HTTP_409_CONFLICT,
}


@router.get(
    "",
    response_model=ConversationListResponse,
    dependencies=[Depends(require_permission("conversation:read"))],
)
def list_conversations(
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    conversation_status: ConversationStatus | None = Query(default=None, alias="status"),
    channel_id: uuid.UUID | None = Query(default=None),
    contact_id: uuid.UUID | None = Query(default=None),
    assigned_user_id: uuid.UUID | None = Query(default=None),
    unassigned: bool = Query(default=False),
    unread: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
):
    with service_errors(ERRORS):
        return conversation_service.list_conversations(
            db, tenant.id, page, page_size,
            status=conversation_status,
            channel_id=channel_id,
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
            unassigned=unassigned,
            unread=unread,
            search=(search or "").strip() or None,
        )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    dependencies=[Depends(require_permission("conversation:read"))],
)
def get_conversation(conversation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return conversation_service.get_conversation(db, tenant.id, conversation_id)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    dependencies=[Depends(require_permission("conversation:update"))],
)
def update_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    tenant: CurrentTenant,
    db: DbSession,
):
    with service_errors(ERRORS):
        return conversation_service.update_conversation(db, tenant.id, conversation_id, data)


@router.post(
    "/{conversation_id}/read",
    response_model=ConversationResponse,
    dependencies=[Depends(require_permission("conversation:update"))],
)
def mark_read(conversation_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return conversation_service.mark_as_read(db, tenant.id, conversation_id)


@router.post(
    "/{conversation_id}/assign",
    response_model=ConversationResponse,
    dependencies=[Depends(require_permission("conversation:assign"))],
)
def assign(
    conversation_id: uuid.UUID,
    data: ConversationAssign,
    tenant: CurrentTenant,
    db: DbSession,
):
    with service_errors(ERRORS):
        return conversation_service.assign_conversation(
            db, tenant.id, conversation_id, data.assigned_user_id,
        )


@router.post(
    "/{conversation_id}/status",
    response_model=ConversationResponse,
    dependencies=[Depends(require_permission("conversation:update"))],
)
def change_status(
    conversation_id: uuid.UUID,
    data: ConversationStatusUpdate,
    tenant: CurrentTenant,
    db: DbSession,
):
    with service_errors(ERRORS):
        return conversation_service.change_status(db, tenant.id, conversation_id, data.status)


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    dependencies=[Depends(require_permission("message:read"))],
)
def list_messages(
    conversation_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    with service_errors(ERRORS):
        return message_service.list_messages(db, tenant.id, conversation_id, page, page_size)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("message:create"))],
)
def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: DbSession,
    idempotency_key: uuid.UUID = Header(..., alias="Idempotency-Key"),
):
    with service_errors(SEND_ERRORS):
        return outbound_message_service.send_message(
            db, tenant.id, user, conversation_id, data, idempotency_key,
        )
