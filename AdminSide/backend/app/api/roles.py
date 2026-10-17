from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentRole, DbSession, require_permission
from app.schemas.team import RoleResponse
from app.services import user_service

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get(
    "",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_permission("user:read"))],
)
def list_roles(role: CurrentRole, db: DbSession):
    """
    Active roles for the current workspace, each flagged with whether the
    requesting member may assign it. Used to populate invite and role-change
    selectors. Carries no permission internals or secrets.
    """
    return user_service.list_assignable_roles(db, role)
