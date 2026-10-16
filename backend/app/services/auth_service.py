import hashlib
import logging
import re
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import PasswordResetRequest, Role, Tenant, TenantMembership, User, UserSession
from app.schemas.auth import (
    LoginRequest,
    PasswordResetCompleteRequest,
    PasswordResetRequestCreate,
    RegisterRequest,
)

logger = logging.getLogger(__name__)


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


class PasswordResetRequestNotFoundError(AuthServiceError):
    """Raised when a reset request is unavailable for review."""


class PasswordResetTokenInvalidError(AuthServiceError):
    """Raised when a password reset token is invalid or expired."""


class PasswordResetEmailError(AuthServiceError):
    """Raised when SMTP is not configured or reset email delivery fails."""


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


def create_password_reset_request(
    db: Session,
    data: PasswordResetRequestCreate,
) -> None:
    email = str(data.email).strip().lower()
    user = db.scalar(
        select(User).where(User.email == email, User.is_active.is_(True))
    )
    if user is None:
        return

    pending = db.scalar(
        select(PasswordResetRequest.id).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == "pending",
        )
    )
    if pending is not None:
        return

    db.add(PasswordResetRequest(user_id=user.id, email=email))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    except SQLAlchemyError:
        db.rollback()
        raise


def list_pending_password_reset_requests(
    db: Session,
) -> list[PasswordResetRequest]:
    return list(
        db.scalars(
            select(PasswordResetRequest)
            .where(PasswordResetRequest.status == "pending")
            .order_by(PasswordResetRequest.requested_at.asc())
        ).all()
    )


def _send_password_reset_email(email: str, raw_token: str) -> None:
    if not settings.smtp_host:
        raise PasswordResetEmailError(
            "Password reset email delivery is not configured. Set up SMTP first."
        )

    reset_url = f"{settings.frontend_url}/reset-password?token={raw_token}"
    message = EmailMessage()
    message["Subject"] = "Reset your Omniflow password"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = email
    message.set_content(
        "A platform administrator approved your password reset request.\n\n"
        f"Choose a new password using this one-time link:\n{reset_url}\n\n"
        f"This link expires in {settings.password_reset_expire_minutes} minutes. "
        "If you did not request a reset, contact your platform administrator."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Could not deliver approved password reset email.")
        raise PasswordResetEmailError(
            "Could not deliver the reset email. Check SMTP and try approving again."
        ) from None


def approve_password_reset_request(
    db: Session,
    request_id: uuid.UUID,
    admin: User,
) -> None:
    reset_request = db.scalar(
        select(PasswordResetRequest)
        .where(
            PasswordResetRequest.id == request_id,
            PasswordResetRequest.status == "pending",
        )
        .with_for_update()
    )
    if reset_request is None:
        raise PasswordResetRequestNotFoundError(
            "Pending password reset request not found."
        )

    user = db.get(User, reset_request.user_id)
    if user is None or not user.is_active:
        raise PasswordResetRequestNotFoundError(
            "The account for this reset request is no longer active."
        )

    raw_token = secrets.token_urlsafe(48)
    _send_password_reset_email(reset_request.email, raw_token)

    reset_request.status = "approved"
    reset_request.reviewed_by = admin.id
    reset_request.reviewed_at = datetime.now(timezone.utc)
    reset_request.reset_token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset_request.token_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_expire_minutes
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def complete_password_reset(
    db: Session,
    data: PasswordResetCompleteRequest,
) -> None:
    digest = hashlib.sha256(data.token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    reset_request = db.scalar(
        select(PasswordResetRequest)
        .where(
            PasswordResetRequest.reset_token_hash == digest,
            PasswordResetRequest.status == "approved",
            PasswordResetRequest.token_expires_at > now,
        )
        .with_for_update()
    )
    if reset_request is None:
        raise PasswordResetTokenInvalidError(
            "This password reset link is invalid or expired."
        )

    user = db.get(User, reset_request.user_id)
    if user is None or not user.is_active:
        raise PasswordResetTokenInvalidError(
            "This password reset link is invalid or expired."
        )

    user.password_hash = hash_password(data.password)
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.is_active.is_(True))
        .values(is_active=False)
    )
    db.execute(
        update(PasswordResetRequest)
        .where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status.in_(["pending", "approved"]),
        )
        .values(
            status="completed",
            reset_token_hash=None,
            token_expires_at=None,
        )
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
