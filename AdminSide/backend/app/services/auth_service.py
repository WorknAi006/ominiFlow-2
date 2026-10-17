import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import Role, Tenant, TenantMembership, User
from app.schemas.auth import LoginRequest, RegisterRequest


# Used to run a password verification when the user does not exist,
# so response timing does not reveal whether an email is registered.
_DUMMY_PASSWORD_HASH = hash_password("omniflow-dummy-password")


class AuthServiceError(Exception):
    """Base authentication service error."""


class EmailAlreadyExistsError(AuthServiceError):
    """Raised when a user email already exists."""


class OwnerRoleNotFoundError(AuthServiceError):
    """Raised when the OWNER system role does not exist."""


class TenantSlugAlreadyExistsError(AuthServiceError):
    """Raised when the generated tenant slug already exists."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials are invalid."""


class NoActiveTenantError(AuthServiceError):
    """Raised when the user has no active tenant membership."""


def generate_slug(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        raise ValueError("Invalid tenant name for slug generation.")

    return slug[:100]


def register_user(
    db: Session,
    data: RegisterRequest,
) -> tuple[User, Tenant]:

    email = str(data.email).strip().lower()

    # 1. Check existing user
    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise EmailAlreadyExistsError(
            "An account with this email already exists."
        )

    # 2. Find OWNER role
    owner_role = (
        db.query(Role)
        .filter(
            Role.name == "OWNER",
            Role.is_active.is_(True),
        )
        .first()
    )

    if owner_role is None:
        raise OwnerRoleNotFoundError(
            "OWNER role is not configured."
        )

    # 3. Generate tenant slug
    base_slug = generate_slug(data.tenant_name)

    # 4. Check duplicate tenant
    existing_tenant = (
        db.query(Tenant)
        .filter(Tenant.slug == base_slug)
        .first()
    )

    if existing_tenant:
        raise TenantSlugAlreadyExistsError(
            "A workspace with this name already exists."
        )

    # 5. Create user
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip()
        if data.last_name
        else None,
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    db.flush()

    # 6. Create tenant
    tenant = Tenant(
        name=data.tenant_name.strip(),
        slug=base_slug,
        email=email,
        is_active=True,
        is_deleted=False,
    )

    db.add(tenant)
    db.flush()

    # 7. Create membership
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role_id=owner_role.id,
        status="active",
    )

    db.add(membership)

    # 8. Commit transaction
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    # 9. Refresh objects
    db.refresh(user)
    db.refresh(tenant)

    return user, tenant


def authenticate_user(
    db: Session,
    data: LoginRequest,
) -> tuple[User, Tenant]:

    email = str(data.email).strip().lower()

    # 1. Find user
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    # 2. Verify password (always run Argon2 to keep timing uniform)
    if user is None:
        verify_password(data.password, _DUMMY_PASSWORD_HASH)
        raise InvalidCredentialsError("Invalid email or password.")

    if not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password.")

    # 3. Reject inactive users
    if not user.is_active:
        raise InvalidCredentialsError("Invalid email or password.")

    # 4. Load active membership and tenant
    tenant = (
        db.query(Tenant)
        .join(
            TenantMembership,
            TenantMembership.tenant_id == Tenant.id,
        )
        .filter(
            TenantMembership.user_id == user.id,
            TenantMembership.status == "active",
            Tenant.is_active.is_(True),
            Tenant.is_deleted.is_(False),
        )
        .order_by(TenantMembership.created_at.asc())
        .first()
    )

    if tenant is None:
        raise NoActiveTenantError(
            "No active workspace is available for this account."
        )

    return user, tenant
