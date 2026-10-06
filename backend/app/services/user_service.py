import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import (
    Permission,
    Role,
    RolePermission,
    TeamInvitation,
    Tenant,
    TenantMembership,
    User,
)
from app.schemas.team import (
    InvitationAcceptRequest,
    InvitationResponse,
    InviteTeamMemberRequest,
    TeamMemberListResponse,
    TeamMemberResponse,
    UpdateTeamMemberRequest,
)

logger = logging.getLogger(__name__)


OWNER_ROLE = "OWNER"

MEMBERSHIP_ACTIVE = "active"
MEMBERSHIP_SUSPENDED = "suspended"
# Soft-removed from the tenant. The global User record is preserved.
MEMBERSHIP_REMOVED = "removed"

VISIBLE_MEMBERSHIP_STATUSES = (MEMBERSHIP_ACTIVE, MEMBERSHIP_SUSPENDED)


# =========================
# ERRORS
# =========================

class TeamServiceError(Exception):
    """Base team management error."""


class MemberNotFoundError(TeamServiceError):
    """Raised when the member does not exist in the current tenant."""


class InvitationNotFoundError(TeamServiceError):
    """Raised when the invitation does not exist in the current tenant."""


class InvalidRoleError(TeamServiceError):
    """Raised when a role does not exist or is inactive."""


class RoleNotAllowedError(TeamServiceError):
    """Raised when the actor may not assign or manage a role."""


class AlreadyMemberError(TeamServiceError):
    """Raised when the user already belongs to the tenant."""


class InvitationAlreadyExistsError(TeamServiceError):
    """Raised when an open invitation already exists."""


class LastOwnerError(TeamServiceError):
    """Raised when a change would leave the tenant without an owner."""


class InvalidInvitationError(TeamServiceError):
    """Raised for unknown, expired, revoked or accepted invitations."""


class InvitationCredentialsError(TeamServiceError):
    """Raised when an existing account's password does not match."""


class MissingProfileError(TeamServiceError):
    """Raised when a new account is missing required profile fields."""


class InvitationConflictError(TeamServiceError):
    """Raised when acceptance conflicts with a concurrent change."""


# =========================
# HELPERS
# =========================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_invitation_token(raw_token: str) -> str:
    """
    Tokens are 256-bit random values, so a fast SHA-256 digest is
    sufficient and allows indexed lookup.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def _member_query(db: Session, tenant_id: uuid.UUID) -> Query:
    return (
        db.query(TenantMembership, User, Role)
        .join(User, User.id == TenantMembership.user_id)
        .join(Role, Role.id == TenantMembership.role_id)
        .filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.status.in_(VISIBLE_MEMBERSHIP_STATUSES),
        )
    )


def _to_member_response(
    membership: TenantMembership,
    user: User,
    role: Role,
) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=role.name,
        role_id=role.id,
        membership_status=membership.status,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=membership.created_at,
    )


def _to_invitation_response(
    invitation: TeamInvitation,
    role: Role,
) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=role.name,
        role_id=role.id,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


def _get_member_row(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    for_update: bool = False,
) -> tuple[TenantMembership, User, Role]:
    query = _member_query(db, tenant_id).filter(
        TenantMembership.user_id == user_id,
    )

    if for_update:
        query = query.with_for_update(of=TenantMembership)

    row = query.first()

    if row is None:
        raise MemberNotFoundError("Team member not found.")

    return row


def _get_active_role(db: Session, role_id: uuid.UUID) -> Role:
    role = (
        db.query(Role)
        .filter(
            Role.id == role_id,
            Role.is_active.is_(True),
        )
        .first()
    )

    if role is None:
        raise InvalidRoleError("Invalid role.")

    return role


def _get_role_permission_names(db: Session, role_id: uuid.UUID) -> set[str]:
    rows = (
        db.query(Permission.name)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .filter(
            RolePermission.role_id == role_id,
            Permission.is_active.is_(True),
        )
        .all()
    )

    return {name for (name,) in rows}


def _ensure_role_within_actor(
    db: Session,
    actor_role: Role,
    target_role: Role,
) -> None:
    """
    Prevent privilege escalation: an actor may only assign or manage a
    role whose permissions are a subset of the actor's own, and only an
    OWNER may assign or manage the OWNER role.
    """

    if target_role.name == OWNER_ROLE and actor_role.name != OWNER_ROLE:
        raise RoleNotAllowedError(
            "Only an owner can assign or manage the owner role."
        )

    if target_role.id == actor_role.id:
        return

    target_permissions = _get_role_permission_names(db, target_role.id)
    actor_permissions = _get_role_permission_names(db, actor_role.id)

    if not target_permissions <= actor_permissions:
        raise RoleNotAllowedError(
            "You cannot assign or manage a role with more permissions "
            "than your own."
        )


def _ensure_owner_remains(
    db: Session,
    tenant_id: uuid.UUID,
    membership: TenantMembership,
    current_role: Role,
    new_role: Role,
    new_status: str,
) -> None:
    """
    A tenant must always keep at least one active OWNER.
    """

    was_active_owner = (
        current_role.name == OWNER_ROLE
        and membership.status == MEMBERSHIP_ACTIVE
    )

    stays_active_owner = (
        new_role.name == OWNER_ROLE
        and new_status == MEMBERSHIP_ACTIVE
    )

    if not was_active_owner or stays_active_owner:
        return

    # Lock the other active owner rows so concurrent demotions cannot
    # both pass this check.
    other_owners = (
        db.query(TenantMembership.id)
        .join(Role, Role.id == TenantMembership.role_id)
        .filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.status == MEMBERSHIP_ACTIVE,
            TenantMembership.id != membership.id,
            Role.name == OWNER_ROLE,
        )
        .order_by(TenantMembership.id)
        .with_for_update(of=TenantMembership)
        .all()
    )

    if not other_owners:
        raise LastOwnerError(
            "A workspace must keep at least one active owner."
        )


# =========================
# TEAM MEMBERS
# =========================

def list_team_members(
    db: Session,
    tenant_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
) -> TeamMemberListResponse:

    query = _member_query(db, tenant_id)

    if search:
        pattern = f"%{_escape_like(search)}%"
        query = query.filter(
            or_(
                User.email.ilike(pattern, escape="\\"),
                User.first_name.ilike(pattern, escape="\\"),
                User.last_name.ilike(pattern, escape="\\"),
            )
        )

    total = query.count()

    rows = (
        query.order_by(
            TenantMembership.created_at.asc(),
            TenantMembership.id.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TeamMemberListResponse(
        items=[_to_member_response(*row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_team_member(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamMemberResponse:

    return _to_member_response(*_get_member_row(db, tenant_id, user_id))


def update_team_member(
    db: Session,
    tenant_id: uuid.UUID,
    actor_role: Role,
    user_id: uuid.UUID,
    data: UpdateTeamMemberRequest,
) -> TeamMemberResponse:

    membership, user, current_role = _get_member_row(
        db, tenant_id, user_id, for_update=True,
    )

    _ensure_role_within_actor(db, actor_role, current_role)

    new_role = current_role

    if data.role_id is not None and data.role_id != current_role.id:
        new_role = _get_active_role(db, data.role_id)
        _ensure_role_within_actor(db, actor_role, new_role)

    new_status = data.status or membership.status

    _ensure_owner_remains(
        db, tenant_id, membership, current_role, new_role, new_status,
    )

    membership.role_id = new_role.id
    membership.status = new_status

    _commit(db)
    db.refresh(membership)

    return _to_member_response(membership, user, new_role)


def remove_team_member(
    db: Session,
    tenant_id: uuid.UUID,
    actor_role: Role,
    user_id: uuid.UUID,
) -> None:
    """
    Soft-remove the membership for the current tenant only. The global
    User and the user's other tenant memberships are untouched.
    """

    membership, _, current_role = _get_member_row(
        db, tenant_id, user_id, for_update=True,
    )

    _ensure_role_within_actor(db, actor_role, current_role)

    _ensure_owner_remains(
        db,
        tenant_id,
        membership,
        current_role,
        current_role,
        MEMBERSHIP_REMOVED,
    )

    membership.status = MEMBERSHIP_REMOVED

    _commit(db)


# =========================
# INVITATIONS
# =========================

def deliver_invitation(
    invitation: TeamInvitation,
    raw_token: str,
) -> None:
    """
    Email delivery hook.

    TODO: when an email service exists, send an invitation link
    containing raw_token to invitation.email here. Never log raw_token.
    """

    logger.info(
        "Team invitation %s created for tenant %s.",
        invitation.id,
        invitation.tenant_id,
    )


def invite_team_member(
    db: Session,
    tenant_id: uuid.UUID,
    actor_user: User,
    actor_role: Role,
    data: InviteTeamMemberRequest,
) -> InvitationResponse:

    role = _get_active_role(db, data.role_id)
    _ensure_role_within_actor(db, actor_role, role)

    email = str(data.email)

    existing_member = (
        db.query(TenantMembership.id)
        .join(User, User.id == TenantMembership.user_id)
        .filter(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.status.in_(VISIBLE_MEMBERSHIP_STATUSES),
            User.email == email,
        )
        .first()
    )

    if existing_member:
        raise AlreadyMemberError(
            "This user is already a member of this workspace."
        )

    now = _utcnow()

    open_invitations = db.query(TeamInvitation).filter(
        TeamInvitation.tenant_id == tenant_id,
        TeamInvitation.email == email,
        TeamInvitation.accepted_at.is_(None),
        TeamInvitation.revoked_at.is_(None),
    )

    # Retire expired invitations so a fresh one can be issued.
    open_invitations.filter(
        TeamInvitation.expires_at <= now,
    ).update(
        {TeamInvitation.revoked_at: now},
        synchronize_session=False,
    )

    if open_invitations.filter(TeamInvitation.expires_at > now).first():
        raise InvitationAlreadyExistsError(
            "An active invitation already exists for this email."
        )

    raw_token = secrets.token_urlsafe(32)

    invitation = TeamInvitation(
        tenant_id=tenant_id,
        email=email,
        role_id=role.id,
        token_hash=hash_invitation_token(raw_token),
        expires_at=now + timedelta(hours=settings.invitation_expire_hours),
        created_by=actor_user.id,
    )

    db.add(invitation)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise InvitationAlreadyExistsError(
            "An active invitation already exists for this email."
        )
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(invitation)

    deliver_invitation(invitation, raw_token)

    response = _to_invitation_response(invitation, role)

    # Until email delivery exists, development returns the token so the
    # flow can be exercised. It is never returned in other environments.
    if settings.app_env == "development":
        response.invitation_token = raw_token

    return response


def list_invitations(
    db: Session,
    tenant_id: uuid.UUID,
) -> list[InvitationResponse]:

    rows = (
        db.query(TeamInvitation, Role)
        .join(Role, Role.id == TeamInvitation.role_id)
        .filter(
            TeamInvitation.tenant_id == tenant_id,
            TeamInvitation.accepted_at.is_(None),
            TeamInvitation.revoked_at.is_(None),
            TeamInvitation.expires_at > _utcnow(),
        )
        .order_by(TeamInvitation.created_at.desc())
        .all()
    )

    return [_to_invitation_response(*row) for row in rows]


def revoke_invitation(
    db: Session,
    tenant_id: uuid.UUID,
    actor_role: Role,
    invitation_id: uuid.UUID,
) -> None:

    row = (
        db.query(TeamInvitation, Role)
        .join(Role, Role.id == TeamInvitation.role_id)
        .filter(
            TeamInvitation.id == invitation_id,
            TeamInvitation.tenant_id == tenant_id,
            TeamInvitation.accepted_at.is_(None),
            TeamInvitation.revoked_at.is_(None),
        )
        .with_for_update(of=TeamInvitation)
        .first()
    )

    if row is None:
        raise InvitationNotFoundError("Invitation not found.")

    invitation, role = row

    _ensure_role_within_actor(db, actor_role, role)

    invitation.revoked_at = _utcnow()

    _commit(db)


def accept_invitation(
    db: Session,
    data: InvitationAcceptRequest,
) -> tuple[User, Tenant]:
    """
    Accept an invitation in a single transaction: create the user if
    needed, create or reactivate the membership, and consume the token.
    """

    now = _utcnow()

    invitation = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.token_hash == hash_invitation_token(data.token),
        )
        .with_for_update()
        .first()
    )

    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= now
    ):
        raise InvalidInvitationError("Invalid or expired invitation.")

    tenant = (
        db.query(Tenant)
        .filter(
            Tenant.id == invitation.tenant_id,
            Tenant.is_active.is_(True),
            Tenant.is_deleted.is_(False),
        )
        .first()
    )

    role = (
        db.query(Role)
        .filter(
            Role.id == invitation.role_id,
            Role.is_active.is_(True),
        )
        .first()
    )

    if tenant is None or role is None:
        raise InvalidInvitationError("Invalid or expired invitation.")

    user = (
        db.query(User)
        .filter(User.email == invitation.email)
        .first()
    )

    if user is not None:
        # Existing account: the invitee must prove ownership. The
        # existing password is never changed.
        if not user.is_active or not verify_password(
            data.password, user.password_hash,
        ):
            raise InvitationCredentialsError("Invalid credentials.")
    else:
        if not data.first_name:
            raise MissingProfileError(
                "first_name is required to create an account."
            )

        user = User(
            email=invitation.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        db.flush()

    membership = (
        db.query(TenantMembership)
        .filter(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
        .with_for_update()
        .first()
    )

    if membership is not None:
        if membership.status != MEMBERSHIP_REMOVED:
            raise AlreadyMemberError(
                "This user is already a member of this workspace."
            )

        membership.role_id = role.id
        membership.status = MEMBERSHIP_ACTIVE
    else:
        db.add(
            TenantMembership(
                tenant_id=tenant.id,
                user_id=user.id,
                role_id=role.id,
                status=MEMBERSHIP_ACTIVE,
            )
        )

    invitation.accepted_at = now

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise InvitationConflictError(
            "The invitation could not be accepted. Please try again."
        )
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(user)
    db.refresh(tenant)

    return user, tenant
