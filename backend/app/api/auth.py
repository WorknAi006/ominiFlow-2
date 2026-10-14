import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from user_agents import parse as parse_user_agent

from app.core.database import get_db
from app.models.user_session import UserSession
from app.core.security import create_access_token
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth_service import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    NoActiveTenantError,
    OwnerRoleNotFoundError,
    TenantSlugAlreadyExistsError,
    authenticate_user,
    register_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
