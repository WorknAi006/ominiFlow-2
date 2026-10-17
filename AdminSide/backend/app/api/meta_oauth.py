import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentTenant, CurrentUser, DbSession, require_permission
from app.schemas.channel import ChannelConnectionResponse
from app.schemas.oauth import (
    OAuthAssetsResponse,
    OAuthSelectRequest,
    OAuthStartResponse,
)
from app.services import meta_oauth_service
from app.services.credential_service import CredentialEncryptionError
from app.services.meta_oauth_service import (
    OAuthConflictError,
    OAuthError,
    OAuthNotConfiguredError,
    OAuthSelectionError,
    OAuthStateInvalidError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Meta OAuth"])


ERROR_STATUS_CODES: dict[type[Exception], int] = {
    OAuthNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
    OAuthConflictError: status.HTTP_409_CONFLICT,
    OAuthStateInvalidError: status.HTTP_400_BAD_REQUEST,
    OAuthSelectionError: status.HTTP_400_BAD_REQUEST,
    OAuthError: status.HTTP_400_BAD_REQUEST,
}


@contextmanager
def _handle_errors() -> Iterator[None]:
    try:
        yield
    except tuple(ERROR_STATUS_CODES) as exc:
        raise HTTPException(status_code=ERROR_STATUS_CODES[type(exc)], detail=str(exc))
    except CredentialEncryptionError:
        logger.error("Channel credential encryption is unavailable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is temporarily unavailable.",
        )
    except SQLAlchemyError:
        logger.exception("Database error during Meta OAuth.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )


# =========================
# START (authenticated)
# =========================

@router.post(
    "/channels/oauth/{provider}/start",
    response_model=OAuthStartResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def start_oauth(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
    provider: str = Path(..., pattern=r"^(facebook|instagram)$"),
):
    with _handle_errors():
        url = meta_oauth_service.start_oauth(db, tenant.id, user.id, provider)
    return OAuthStartResponse(authorization_url=url)


# =========================
# CALLBACK (public; authorized by the random state token only)
# =========================

@router.get("/channels/oauth/callback")
def oauth_callback(
    db: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_reason: str | None = Query(default=None),
):
    # Never raises to the browser: always a redirect back to the dashboard.
    try:
        destination = meta_oauth_service.handle_callback(
            db, code=code, state_token=state, error=error or error_reason,
        )
    except SQLAlchemyError:
        logger.error("Database error during Meta OAuth callback.")
        destination = meta_oauth_service._frontend_redirect(connect_error="provider_error")
    return RedirectResponse(url=destination, status_code=status.HTTP_303_SEE_OTHER)


# =========================
# ASSET SELECTION (authenticated; tenant + user bound)
# =========================

@router.get(
    "/channels/oauth/assets",
    response_model=OAuthAssetsResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def oauth_assets(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
    token: str = Query(..., min_length=10, max_length=128),
):
    with _handle_errors():
        result = meta_oauth_service.get_assets(db, tenant.id, user.id, token)
    return OAuthAssetsResponse(provider=result.provider, assets=result.assets)


@router.post(
    "/channels/oauth/select",
    response_model=ChannelConnectionResponse,
    dependencies=[Depends(require_permission("channel:update"))],
)
def oauth_select(
    data: OAuthSelectRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
):
    with _handle_errors():
        return meta_oauth_service.complete_selection(
            db, tenant.id, user.id, user.id, data.token, data.external_account_id,
        )
