import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import (
    CurrentRole,
    CurrentTenant,
    CurrentUser,
    DbSession,
    require_permission,
)
from app.core.security import create_access_token
from app.schemas.auth import AuthResponse
from app.schemas.team import (
    InvitationAcceptRequest,
    InvitationResponse,
    InviteTeamMemberRequest,
    TeamMemberListResponse,
    TeamMemberResponse,
    UpdateTeamMemberRequest,
)
from app.services import user_service
from app.services.user_service import (
    AlreadyMemberError,
    EmailDeliveryError,
    InvalidInvitationError,
    InvalidRoleError,
    InvitationAlreadyExistsError,
    InvitationConflictError,
    InvitationCredentialsError,
    InvitationNotFoundError,
    LastOwnerError,
    MemberNotFoundError,
    MissingProfileError,
    RoleNotAllowedError,
    TeamServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Team Members"])


ERROR_STATUS_CODES: dict[type[TeamServiceError], int] = {
    MemberNotFoundError: status.HTTP_404_NOT_FOUND,
    InvitationNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidRoleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MissingProfileError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RoleNotAllowedError: status.HTTP_403_FORBIDDEN,
    AlreadyMemberError: status.HTTP_409_CONFLICT,
    InvitationAlreadyExistsError: status.HTTP_409_CONFLICT,
    InvitationConflictError: status.HTTP_409_CONFLICT,
    LastOwnerError: status.HTTP_409_CONFLICT,
    InvalidInvitationError: status.HTTP_400_BAD_REQUEST,
    InvitationCredentialsError: status.HTTP_401_UNAUTHORIZED,
    EmailDeliveryError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


@contextmanager
def handle_service_errors() -> Iterator[None]:
    try:
        yield

    except TeamServiceError as exc:
        raise HTTPException(
            status_code=ERROR_STATUS_CODES.get(
                type(exc),
                status.HTTP_400_BAD_REQUEST,
            ),
            detail=str(exc),
        )

    except SQLAlchemyError:
        logger.exception("Database error during team management.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )


# =========================
# TEAM MEMBERS
# =========================

@router.get(
    "",
    response_model=TeamMemberListResponse,
    dependencies=[Depends(require_permission("user:read"))],
)
def list_members(
    tenant: CurrentTenant,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
):
    search = search.strip() if search else None

    with handle_service_errors():
        return user_service.list_team_members(
            db, tenant.id, page, page_size, search or None,
        )


# =========================
# INVITATIONS
# (declared before /{user_id} routes)
# =========================

@router.post(
    "/invite",
    response_model=InvitationResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user:create"))],
)
def invite_member(
    data: InviteTeamMemberRequest,
    user: CurrentUser,
    tenant: CurrentTenant,
    role: CurrentRole,
    db: DbSession,
):
    with handle_service_errors():
        return user_service.invite_team_member(
            db, tenant.id, user, role, data,
        )


@router.get(
    "/invitations",
    response_model=list[InvitationResponse],
    response_model_exclude_none=True,
    dependencies=[Depends(require_permission("user:read"))],
)
def list_invitations(
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return user_service.list_invitations(db, tenant.id)


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:create"))],
)
def revoke_invitation(
    invitation_id: uuid.UUID,
    tenant: CurrentTenant,
    role: CurrentRole,
    db: DbSession,
):
    with handle_service_errors():
        user_service.revoke_invitation(db, tenant.id, role, invitation_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/invitations/accept",
    response_model=AuthResponse,
)
def accept_invitation(
    data: InvitationAcceptRequest,
    db: DbSession,
):
    """
    Public endpoint: the invitation token is the credential.
    """

    with handle_service_errors():
        user, tenant = user_service.accept_invitation(db, data)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "tenant_id": str(tenant.id),
        },
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
        tenant=tenant,
    )


# =========================
# SINGLE MEMBER
# =========================

@router.get(
    "/{user_id}",
    response_model=TeamMemberResponse,
    dependencies=[Depends(require_permission("user:read"))],
)
def get_member(
    user_id: uuid.UUID,
    tenant: CurrentTenant,
    db: DbSession,
):
    with handle_service_errors():
        return user_service.get_team_member(db, tenant.id, user_id)


@router.patch(
    "/{user_id}",
    response_model=TeamMemberResponse,
    dependencies=[Depends(require_permission("user:update"))],
)
def update_member(
    user_id: uuid.UUID,
    data: UpdateTeamMemberRequest,
    tenant: CurrentTenant,
    role: CurrentRole,
    db: DbSession,
):
    with handle_service_errors():
        return user_service.update_team_member(
            db, tenant.id, role, user_id, data,
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:delete"))],
)
def remove_member(
    user_id: uuid.UUID,
    tenant: CurrentTenant,
    role: CurrentRole,
    db: DbSession,
):
    with handle_service_errors():
        user_service.remove_team_member(db, tenant.id, role, user_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
