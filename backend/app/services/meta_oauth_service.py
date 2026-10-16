"""
Tenant self-service Meta (Facebook / Instagram) OAuth onboarding.

Flow (server-side; the browser never sees tokens, secrets or codes):

  start   -> create a single-use OAuthState, return the Meta dialog URL
  callback-> validate state, exchange code, discover assets, issue a
             selection token, redirect back to the dashboard
  assets  -> (authenticated) return the safe discovered asset list
  select  -> (authenticated) verify the chosen Page/account with Meta,
             subscribe webhooks, store encrypted credentials, create or
             update the tenant's ChannelConnection

Security model:
- The callback is authorized ONLY by the random `state_token`; tenant and
  user come from the OAuthState row, never from the request.
- `assets`/`select` are authenticated and must match the state's tenant and
  user, so Tenant A's selection token is useless to Tenant B.
- State is tenant/user/provider-bound, short-lived, single-use and
  replay-protected (unique tokens + status/expiry/consumed checks).
- Provider-specific Meta verification stays in the Facebook/Instagram
  providers; the generic inbound/outbound core is untouched.
"""
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.base import (
    ProviderCredentials,
    ProviderError,
    ProviderUnavailableError,
    ProviderVerificationError,
)
from app.integrations.facebook.provider import FacebookProvider
from app.integrations.instagram.provider import InstagramProvider
from app.integrations.meta.graph_client import (
    MetaGraphError,
    MetaGraphUnavailableError,
    is_meta_configured,
)
from app.integrations.registry import get_provider
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    OAuthState,
    OAuthStatus,
)
from app.schemas.channel import ChannelConnectionResponse
from app.services import channel_service
from app.services.credential_service import get_credential_service

logger = logging.getLogger(__name__)

# Facebook Login permissions, per the official Messenger / Instagram docs.
SCOPES: dict[str, str] = {
    ChannelType.FACEBOOK.value: "pages_show_list,pages_messaging,pages_manage_metadata",
    ChannelType.INSTAGRAM.value: (
        "instagram_business_basic,instagram_business_manage_messages"
    ),
}

DISCOVERY_FIELDS: dict[str, str] = {
    ChannelType.FACEBOOK.value: "id,name,access_token",
    ChannelType.INSTAGRAM.value: "id,name,access_token,instagram_business_account{id,username,name}",
}

# Safe, user-facing callback error reasons (never raw Meta errors).
CALLBACK_ERRORS = {
    "cancelled", "invalid_state", "expired", "exchange_failed",
    "no_pages", "no_instagram", "provider_error",
}


class OAuthError(Exception):
    """Base OAuth onboarding error."""


class OAuthNotConfiguredError(OAuthError):
    """Meta app credentials are not configured."""


class OAuthStateInvalidError(OAuthError):
    """Selection token is unknown, expired, already used, or not this user's."""


class OAuthSelectionError(OAuthError):
    """The chosen account could not be connected (sanitized reason)."""


class OAuthConflictError(OAuthError):
    """The Page/account is already connected to another tenant."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _provider(provider: str) -> FacebookProvider | InstagramProvider:
    obj = get_provider(ChannelType(provider))
    assert isinstance(obj, (FacebookProvider, InstagramProvider))
    return obj


def _normalize_provider(provider: str) -> str:
    try:
        ctype = ChannelType(provider)
    except ValueError:
        raise OAuthError("Unsupported provider.") from None
    if ctype not in (ChannelType.FACEBOOK, ChannelType.INSTAGRAM):
        raise OAuthError("This provider does not support Meta OAuth.")
    return ctype.value


# =========================
# START
# =========================

def start_oauth(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    provider: str,
) -> str:
    """Create a single-use OAuth state and return the Meta dialog URL."""
    provider = _normalize_provider(provider)
    if not is_meta_configured():
        raise OAuthNotConfiguredError("Meta integration is not configured.")

    state_token = secrets.token_urlsafe(32)
    row = OAuthState(
        tenant_id=tenant_id,
        user_id=user_id,
        provider=provider,
        state_token=state_token,
        status=OAuthStatus.PENDING,
        expires_at=_utcnow() + timedelta(minutes=settings.oauth_state_expiry_minutes),
    )
    db.add(row)
    db.commit()

    query = urlencode({
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_oauth_redirect_uri,
        "state": state_token,
        "scope": SCOPES[provider],
        "response_type": "code",
    })
    base = settings.meta_facebook_login_base_url.rstrip("/")
    return f"{base}/{settings.meta_graph_api_version}/dialog/oauth?{query}"


# =========================
# CALLBACK (public; authorized by state_token only)
# =========================

def _frontend_redirect(**params: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/channels?{urlencode(params)}"


def _discover_assets(provider: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict) or not page.get("id"):
            continue
        if provider == ChannelType.FACEBOOK.value:
            assets.append({
                "external_account_id": str(page["id"]),
                "name": page.get("name") or str(page["id"]),
            })
        else:
            iba = page.get("instagram_business_account")
            if isinstance(iba, dict) and iba.get("id"):
                assets.append({
                    "external_account_id": str(iba["id"]),
                    "name": iba.get("username") or iba.get("name") or str(iba["id"]),
                    "page_id": str(page["id"]),
                    "page_name": page.get("name"),
                })
    return assets


def handle_callback(
    db: Session,
    *,
    code: str | None,
    state_token: str | None,
    error: str | None,
) -> str:
    """
    Validate the state, exchange the code and discover assets. Returns a URL
    to redirect the browser back to the dashboard (success or a safe error).
    """
    if not state_token:
        return _frontend_redirect(connect_error="invalid_state")

    row = (
        db.query(OAuthState)
        .filter(OAuthState.state_token == state_token)
        .with_for_update()
        .first()
    )
    if row is None or row.status != OAuthStatus.PENDING:
        return _frontend_redirect(connect_error="invalid_state")
    if row.expires_at <= _utcnow():
        row.status = OAuthStatus.CONSUMED
        row.consumed_at = _utcnow()
        db.commit()
        return _frontend_redirect(connect_error="expired", provider=row.provider)

    provider = row.provider

    # The user declined the Meta dialog, or any other dialog-level error.
    if error or not code:
        row.status = OAuthStatus.CONSUMED
        row.consumed_at = _utcnow()
        db.commit()
        return _frontend_redirect(connect_error="cancelled", provider=provider)

    try:
        if not is_meta_configured():
            raise OAuthNotConfiguredError("Meta integration is not configured.")
        provider_obj = _provider(provider)
        with provider_obj.client_factory() as client:
            exchanged = client.oauth_exchange_code(code, settings.meta_oauth_redirect_uri)
            short_token = exchanged.get("access_token")
            if not isinstance(short_token, str) or not short_token:
                raise OAuthSelectionError("exchange_failed")
            long_lived = client.long_lived_user_token(short_token)
            user_token = long_lived.get("access_token") or short_token
            pages = client.list_managed_pages(user_token, DISCOVERY_FIELDS[provider])
        assets = _discover_assets(provider, pages.get("data") or [])
    except (MetaGraphUnavailableError, ProviderUnavailableError):
        row.status = OAuthStatus.CONSUMED
        row.consumed_at = _utcnow()
        db.commit()
        return _frontend_redirect(connect_error="provider_error", provider=provider)
    except (MetaGraphError, ProviderError, OAuthError) as exc:
        logger.warning("Meta OAuth callback failed for provider %s: %s", provider, type(exc).__name__)
        row.status = OAuthStatus.CONSUMED
        row.consumed_at = _utcnow()
        db.commit()
        return _frontend_redirect(connect_error="exchange_failed", provider=provider)

    if not assets:
        reason = "no_instagram" if provider == ChannelType.INSTAGRAM.value else "no_pages"
        row.status = OAuthStatus.CONSUMED
        row.consumed_at = _utcnow()
        db.commit()
        return _frontend_redirect(connect_error=reason, provider=provider)

    row.user_token_encrypted = get_credential_service().encrypt(user_token)
    row.assets = assets
    row.selection_token = secrets.token_urlsafe(32)
    row.status = OAuthStatus.DISCOVERED
    db.commit()

    return _frontend_redirect(connect=row.selection_token, provider=provider)


# =========================
# SELECTION (authenticated; tenant + user bound)
# =========================

def _load_for_selection(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    selection_token: str,
    for_update: bool = False,
) -> OAuthState:
    query = db.query(OAuthState).filter(
        OAuthState.selection_token == selection_token,
        OAuthState.tenant_id == tenant_id,
        OAuthState.user_id == user_id,
        OAuthState.status == OAuthStatus.DISCOVERED,
    )
    if for_update:
        query = query.with_for_update()
    row = query.first()
    if row is None or row.expires_at <= _utcnow():
        raise OAuthStateInvalidError("This connection session is invalid or has expired.")
    return row


@dataclass(frozen=True)
class OAuthAssets:
    provider: str
    assets: list[dict[str, Any]]


def get_assets(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    selection_token: str,
) -> OAuthAssets:
    row = _load_for_selection(db, tenant_id, user_id, selection_token)
    # Strip any internal-only keys; expose only safe display fields.
    safe = [
        {k: v for k, v in asset.items() if k in ("external_account_id", "name", "page_id", "page_name")}
        for asset in (row.assets or [])
    ]
    return OAuthAssets(provider=row.provider, assets=safe)


def _find_page_for_asset(
    provider: str,
    pages: list[dict[str, Any]],
    external_account_id: str,
) -> tuple[dict[str, Any], str, str]:
    """Return (page, page_access_token, resolved_external_account_id)."""
    for page in pages:
        if not isinstance(page, dict):
            continue
        token = page.get("access_token")
        if not token:
            continue
        if provider == ChannelType.FACEBOOK.value:
            if str(page.get("id")) == external_account_id:
                return page, str(token), external_account_id
        else:
            iba = page.get("instagram_business_account")
            if isinstance(iba, dict) and str(iba.get("id")) == external_account_id:
                return page, str(token), external_account_id
    raise OAuthSelectionError("The selected account is no longer available. Start again.")


def _conflict_in_other_tenant(
    db: Session, tenant_id: uuid.UUID, channel_type: str, external_account_id: str,
) -> bool:
    other = (
        db.query(ChannelConnection.id)
        .filter(
            ChannelConnection.tenant_id != tenant_id,
            ChannelConnection.channel_type == channel_type,
            ChannelConnection.external_account_id == external_account_id,
            ChannelConnection.status == ChannelStatus.CONNECTED,
            ChannelConnection.is_deleted.is_(False),
        )
        .first()
    )
    return other is not None


def complete_selection(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    actor_id: uuid.UUID,
    selection_token: str,
    external_account_id: str,
) -> ChannelConnectionResponse:
    row = _load_for_selection(db, tenant_id, user_id, selection_token, for_update=True)
    provider = row.provider

    if not is_meta_configured():
        raise OAuthNotConfiguredError("Meta integration is not configured.")
    if not row.user_token_encrypted:
        raise OAuthStateInvalidError("This connection session is invalid or has expired.")

    user_token = get_credential_service().decrypt(row.user_token_encrypted)
    provider_obj = _provider(provider)

    # Re-fetch pages to obtain a fresh Page access token for the choice; end
    # any read transaction before the external calls.
    db.rollback()
    try:
        with provider_obj.client_factory() as client:
            pages = client.list_managed_pages(user_token, DISCOVERY_FIELDS[provider])
        page, page_token, resolved_id = _find_page_for_asset(
            provider, pages.get("data") or [], external_account_id,
        )
        credentials = ProviderCredentials(access_token=page_token)

        if provider == ChannelType.FACEBOOK.value:
            info = provider_obj.verify_page(credentials, resolved_id)
            provider_obj.subscribe_webhooks(credentials, resolved_id)
            business_id = None
        else:
            page_id = str(page["id"])
            info = provider_obj.verify_account(credentials, resolved_id, page_id)
            provider_obj.subscribe_webhooks(credentials, page_id)
            business_id = page_id
    except (MetaGraphUnavailableError, ProviderUnavailableError):
        raise OAuthSelectionError("Could not reach Meta. Please try again.") from None
    except (MetaGraphError, ProviderVerificationError) as exc:
        logger.warning("Meta OAuth selection verification failed: %s", type(exc).__name__)
        raise OAuthSelectionError(
            "The selected account could not be verified. Check your Meta permissions and try again."
        ) from None
    finally:
        del user_token

    encrypted = get_credential_service().encrypt(page_token)
    name = (info.display_name or external_account_id)[:150]

    # Reconnect our own channel if it already exists; otherwise refuse a
    # Page/account already connected to another tenant, else create.
    existing = (
        db.query(ChannelConnection)
        .filter(
            ChannelConnection.tenant_id == tenant_id,
            ChannelConnection.channel_type == provider,
            ChannelConnection.external_account_id == info.external_account_id,
            ChannelConnection.is_deleted.is_(False),
        )
        .with_for_update()
        .first()
    )

    if existing is None and _conflict_in_other_tenant(
        db, tenant_id, provider, info.external_account_id,
    ):
        raise OAuthConflictError(
            "This account is already connected to another workspace."
        )

    channel = existing or ChannelConnection(
        tenant_id=tenant_id,
        channel_type=provider,
        name=name,
        created_by=actor_id,
    )
    channel.status = ChannelStatus.CONNECTED
    channel.external_account_id = info.external_account_id
    channel.external_business_id = business_id
    channel.access_token_encrypted = encrypted
    channel.refresh_token_encrypted = None
    channel.token_expires_at = None
    channel.provider_metadata = info.metadata
    channel.is_active = True
    channel.last_connected_at = _utcnow()
    channel.last_error = None
    if existing is None:
        channel.name = name
        db.add(channel)

    # Single-use: spend the state and clear the stored user token.
    row.status = OAuthStatus.CONSUMED
    row.consumed_at = _utcnow()
    row.user_token_encrypted = None
    row.assets = None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise OAuthConflictError(
            "This account is already connected to another workspace."
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(channel)
    logger.info("Meta OAuth connected %s channel %s for tenant %s.", provider, channel.id, tenant_id)
    return channel_service.get_channel(db, tenant_id, channel.id)
