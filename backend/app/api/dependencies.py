import uuid
from collections.abc import Callable
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import (
    Permission,
    Role,
    RolePermission,
    Tenant,
    TenantMembership,
    User,
)


# auto_error=False so missing / non-Bearer headers return our own 401
# instead of FastAPI's default 403.
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _workspace_access_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this workspace.",
    )


def _parse_uuid(value: Any) -> uuid.UUID | None:
    if not isinstance(value, str):
        return None

    try:
        return uuid.UUID(value)
    except ValueError:
        return None


# =========================
# AUTHENTICATION
# =========================

def get_token_payload(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> dict[str, Any]:
    """
    Decode and validate the Bearer access token.
    """

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_exception()

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _credentials_exception()

    if payload.get("type") != "access":
        raise _credentials_exception()

    if _parse_uuid(payload.get("sub")) is None:
        raise _credentials_exception()

    if _parse_uuid(payload.get("tenant_id")) is None:
        raise _credentials_exception()

    return payload


TokenPayload = Annotated[dict[str, Any], Depends(get_token_payload)]


from app.models.user_session import UserSession

def get_current_user(
    payload: TokenPayload,
    db: DbSession,
) -> User:
    """
    Return the active user identified by the access token.
    """

    user_id = _parse_uuid(payload["sub"])

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise _credentials_exception()
        
    session_id = _parse_uuid(payload.get("session_id"))
    if session_id:
        user_session = db.get(UserSession, session_id)
        if not user_session or not user_session.is_active:
            raise _credentials_exception()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_platform_super_admin(
    user: CurrentUser,
) -> None:
    if not user.is_platform_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform super-admin access is required.",
        )


# =========================
# TENANT CONTEXT
# =========================

def _get_active_membership(
    db: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> TenantMembership | None:
    return (
        db.query(TenantMembership)
        .filter(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.status == "active",
        )
        .first()
    )


def get_current_tenant(
    payload: TokenPayload,
    user: CurrentUser,
    db: DbSession,
) -> Tenant:
    """
    Return the tenant from the access token, verified against an
    active membership. The token is the only source of tenant_id.
    """

    tenant_id = _parse_uuid(payload["tenant_id"])

    tenant = (
        db.query(Tenant)
        .filter(
            Tenant.id == tenant_id,
            Tenant.is_active.is_(True),
            Tenant.is_deleted.is_(False),
        )
        .first()
    )

    if tenant is None:
        raise _workspace_access_exception()

    if _get_active_membership(db, user.id, tenant.id) is None:
        raise _workspace_access_exception()

    return tenant


CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]


def get_current_membership(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: DbSession,
) -> TenantMembership:
    """
    Return the current user's active membership in the current tenant.
    """

    membership = _get_active_membership(db, user.id, tenant.id)

    if membership is None:
        raise _workspace_access_exception()

    return membership


CurrentMembership = Annotated[
    TenantMembership,
    Depends(get_current_membership),
]


def get_current_role(
    membership: CurrentMembership,
    db: DbSession,
) -> Role:
    """
    Return the active role assigned through the current membership.
    """

    role = (
        db.query(Role)
        .filter(
            Role.id == membership.role_id,
            Role.is_active.is_(True),
        )
        .first()
    )

    if role is None:
        raise _workspace_access_exception()

    return role


CurrentRole = Annotated[Role, Depends(get_current_role)]


# =========================
# AUTHORIZATION (RBAC)
# =========================

def has_permission(
    db: Session,
    role: Role,
    permission_name: str,
) -> bool:
    """
    Check whether a role has an active permission.
    """

    granted = (
        db.query(RolePermission)
        .join(
            Permission,
            Permission.id == RolePermission.permission_id,
        )
        .filter(
            RolePermission.role_id == role.id,
            Permission.name == permission_name,
            Permission.is_active.is_(True),
        )
        .first()
    )

    return granted is not None


def require_permission(
    permission_name: str,
) -> Callable[[Role, Session], None]:
    """
    Build a dependency that enforces a permission for the current role.

    Usage:
        @router.get(
            "/resource",
            dependencies=[Depends(require_permission("resource:read"))],
        )
    """

    def permission_dependency(
        role: CurrentRole,
        db: DbSession,
    ) -> None:
        if not has_permission(db, role, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

    return permission_dependency


# =========================
# PLATFORM / SUPER ADMIN
# =========================

def get_current_platform_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: DbSession,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_exception()

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _credentials_exception()

    if payload.get("type") != "access":
        raise _credentials_exception()

    user_id = _parse_uuid(payload.get("sub"))
    if user_id is None:
        raise _credentials_exception()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_exception()

    if not (getattr(user, "is_platform_admin", False) or getattr(user, "is_platform_super_admin", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin authorization required.",
        )

    return user


CurrentPlatformAdmin = Annotated[User, Depends(get_current_platform_admin)]

