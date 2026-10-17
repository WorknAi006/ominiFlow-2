from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Tenant
from app.schemas.tenant import TenantUpdateRequest


# Explicit allowlist; guards against mass assignment even if the
# request schema grows later.
UPDATABLE_TENANT_FIELDS = frozenset({
    "name",
    "email",
    "phone",
    "description",
})


def update_tenant(
    db: Session,
    tenant: Tenant,
    data: TenantUpdateRequest,
) -> Tenant:

    changes = data.model_dump(
        include=UPDATABLE_TENANT_FIELDS,
        exclude_unset=True,
    )

    for field, value in changes.items():
        setattr(tenant, field, value)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(tenant)

    return tenant
