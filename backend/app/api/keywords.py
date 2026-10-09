import uuid
from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentTenant, CurrentUser, DbSession
from app.schemas.keyword import KeywordCreate, KeywordResponse, KeywordUpdate
from app.services import keyword_service

router = APIRouter(prefix="/keywords", tags=["keywords"])

@router.get("", response_model=list[KeywordResponse])
def list_keywords_route(
    current_user: CurrentUser,
    tenant: CurrentTenant,
    session: DbSession,
):
    """List all keywords for the tenant."""
    return keyword_service.list_keywords(session, tenant.id)

@router.get("/{keyword_id}", response_model=KeywordResponse)
def get_keyword_route(
    keyword_id: uuid.UUID,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    session: DbSession,
):
    """Get a specific keyword."""
    return keyword_service.get_keyword(session, tenant.id, keyword_id)

@router.post("", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def create_keyword_route(
    data: KeywordCreate,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    session: DbSession,
):
    """Create a new keyword."""
    return keyword_service.create_keyword(session, tenant.id, current_user.id, data)

@router.patch("/{keyword_id}", response_model=KeywordResponse)
def update_keyword_route(
    keyword_id: uuid.UUID,
    data: KeywordUpdate,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    session: DbSession,
):
    """Update an existing keyword."""
    return keyword_service.update_keyword(session, tenant.id, keyword_id, data)

@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_route(
    keyword_id: uuid.UUID,
    current_user: CurrentUser,
    tenant: CurrentTenant,
    session: DbSession,
):
    """Delete a keyword."""
    keyword_service.delete_keyword(session, tenant.id, keyword_id)
