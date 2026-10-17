"""
Test harness that runs against the real PostgreSQL database without
persisting anything.

Each TestCase class opens one connection and an outer transaction that
is always rolled back. Every test runs inside its own SAVEPOINT, and the
API's sessions join that connection with join_transaction_mode=
"create_savepoint", so commits made by the application only release
savepoints and never reach the database.
"""
import unittest
import uuid
import warnings
from typing import Any

warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import engine, get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, Tenant, TenantMembership, User  # noqa: E402
from app.services.realtime_service import InMemoryBroker, set_broker  # noqa: E402

TEST_PASSWORD = "Test@12345"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class DatabaseTestCase(unittest.TestCase):
    connection: Any
    outer_transaction: Any
    db: Session
    client: TestClient

    @classmethod
    def make_session(cls) -> Session:
        return Session(
            bind=cls.connection,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

    @classmethod
    def setUpClass(cls) -> None:
        cls.connection = engine.connect()
        cls.outer_transaction = cls.connection.begin()

        def override_get_db():
            db = cls.make_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        # Never publish realtime events to a real Redis from tests.
        cls.realtime = InMemoryBroker()
        set_broker(cls.realtime)
        cls.client = TestClient(app)
        cls.db = cls.make_session()

        cls.create_fixtures()
        cls.db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()
        app.dependency_overrides.pop(get_db, None)
        set_broker(None)
        cls.outer_transaction.rollback()
        cls.connection.close()

    def setUp(self) -> None:
        self.savepoint = self.connection.begin_nested()

    def tearDown(self) -> None:
        self.db.rollback()
        if self.savepoint.is_active:
            self.savepoint.rollback()
        self.db.expire_all()

    @classmethod
    def create_fixtures(cls) -> None:
        """Override to create class-level fixtures."""

    # ---------- fixture helpers ----------

    @classmethod
    def role(cls, name: str) -> Role:
        return cls.db.query(Role).filter(Role.name == name).one()

    @classmethod
    def make_tenant(cls, name: str = "Test Tenant") -> Tenant:
        tenant = Tenant(name=name, slug=unique("tenant"))
        cls.db.add(tenant)
        cls.db.flush()
        return tenant

    @classmethod
    def make_user(
        cls,
        prefix: str = "user",
        first_name: str = "Test",
        last_name: str | None = "User",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=f"{unique(prefix)}@test.omniflow",
            password_hash=TEST_PASSWORD_HASH,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
        )
        cls.db.add(user)
        cls.db.flush()
        return user

    @classmethod
    def add_member(
        cls,
        user: User,
        tenant: Tenant,
        role_name: str,
        status: str = "active",
    ) -> TenantMembership:
        membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=user.id,
            role_id=cls.role(role_name).id,
            status=status,
        )
        cls.db.add(membership)
        cls.db.flush()
        return membership

    @classmethod
    def make_member(
        cls,
        tenant: Tenant,
        role_name: str,
        **user_kwargs: Any,
    ) -> User:
        user = cls.make_user(prefix=role_name.lower(), **user_kwargs)
        cls.add_member(user, tenant, role_name)
        return user

    @staticmethod
    def token_for(user: User, tenant: Tenant, **kwargs: Any) -> str:
        extra = {"tenant_id": str(tenant.id), **kwargs.pop("extra", {})}
        return create_access_token(
            subject=str(user.id),
            extra_claims=extra,
            **kwargs,
        )

    def auth(self, user: User, tenant: Tenant) -> dict[str, str]:
        return bearer(self.token_for(user, tenant))
