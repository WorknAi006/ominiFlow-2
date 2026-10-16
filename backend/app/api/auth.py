import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from user_agents import parse as parse_user_agent

from app.api.dependencies import (
    CurrentUser,
    DbSession,
    TokenPayload,
    require_platform_super_admin,
)
from app.core.database import get_db
from app.models.user_session import UserSession
from app.core.security import create_access_token
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    PasswordResetCompleteRequest,
    PasswordResetRequestCreate,
    PasswordResetRequestResponse,
    PasswordResetStatusResponse,
    RegisterRequest,
)
from app.services.auth_service import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    NoActiveTenantError,
    OwnerRoleNotFoundError,
    PasswordResetEmailError,
    PasswordResetRequestNotFoundError,
    PasswordResetTokenInvalidError,
    TenantSlugAlreadyExistsError,
    approve_password_reset_request,
    authenticate_user,
    complete_password_reset,
    create_password_reset_request,
    list_pending_password_reset_requests,
    register_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/platform-admin/status", response_model=PasswordResetStatusResponse)
def platform_admin_status(user: CurrentUser):
    return {"is_platform_super_admin": user.is_platform_super_admin}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: TokenPayload,
    user: CurrentUser,
    db: DbSession,
):
    session_id = payload.get("session_id")
    if isinstance(session_id, str):
        try:
            parsed_session_id = uuid.UUID(session_id)
        except ValueError:
            parsed_session_id = None
        if parsed_session_id is not None:
            user_session = db.query(UserSession).filter(
                UserSession.id == parsed_session_id,
                UserSession.user_id == user.id,
                UserSession.is_active.is_(True),
            ).first()
            if user_session is not None:
                user_session.is_active = False
                db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/password-reset-requests",
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    data: PasswordResetRequestCreate,
    db: DbSession,
):
    try:
        create_password_reset_request(db, data)
    except SQLAlchemyError:
        logger.exception("Database error creating password reset request.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not submit your request. Please try again later.",
        ) from None
    return {
        "message": "If an active account matches that email, a platform administrator will review the reset request."
    }


@router.get(
    "/password-reset-requests",
    response_model=list[PasswordResetRequestResponse],
    dependencies=[Depends(require_platform_super_admin)],
)
def list_password_reset_requests(db: DbSession):
    return list_pending_password_reset_requests(db)


@router.post(
    "/password-reset-requests/{request_id}/approve",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_platform_super_admin)],
)
def approve_password_reset(
    request_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    try:
        approve_password_reset_request(db, request_id, user)
    except PasswordResetRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except PasswordResetEmailError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except SQLAlchemyError:
        logger.exception("Database error approving password reset.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not approve this request. Please try again.",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    data: PasswordResetCompleteRequest,
    db: DbSession,
):
    try:
        complete_password_reset(db, data)
    except PasswordResetTokenInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except SQLAlchemyError:
        logger.exception("Database error completing password reset.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reset the password. Please try again.",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        user, tenant = register_user(db, data)

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

    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except TenantSlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except OwnerRoleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
        user, tenant = authenticate_user(db, data)

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except NoActiveTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    except SQLAlchemyError:
        logger.exception("Database error during login.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )
        
    user_agent_str = request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else None
    
    device_info = "Unknown Device"
    if user_agent_str:
        ua = parse_user_agent(user_agent_str)
        browser = ua.browser.family if ua.browser.family != 'Other' else 'Unknown Browser'
        os = ua.os.family if ua.os.family != 'Other' else 'Unknown OS'
        device_info = f"{browser} on {os}"
        
    user_session = UserSession(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent_str,
        device_info=device_info,
    )
    db.add(user_session)
    db.commit()
    db.refresh(user_session)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "tenant_id": str(tenant.id),
            "session_id": str(user_session.id),
        },
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
        tenant=tenant,
    )
