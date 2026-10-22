"""Read-only auth diagnosis. Never print credentials, tokens or user records."""
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import configure_mappers

from app.core.database import engine, SessionLocal
from app.models import User, Tenant, TenantMembership, UserSession
from app.schemas.auth import LoginRequest
from app.services.auth_service import authenticate_user, InvalidCredentialsError


def report_error(exc):
    original = getattr(exc, "orig", exc)
    print("ERROR_TYPE:", type(exc).__name__, type(original).__name__)
    print("ERROR_DETAIL:", str(original)[:1800])


try:
    configure_mappers()
    print("ORM_MAPPERS: OK")
except Exception as exc:
    report_error(exc)

try:
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        print("DATABASE_IDENTITY:", tuple(connection.execute(text("SELECT current_database(), current_user, current_schema()")).one()))
        print("MIGRATION_VERSION:", list(connection.execute(text("SELECT version_num FROM alembic_version")).scalars()))
        inspector = inspect(connection)
        for model in (User, Tenant, TenantMembership, UserSession):
            actual = {column["name"] for column in inspector.get_columns(model.__tablename__)}
            expected = {column.name for column in model.__table__.columns}
            print("MISSING_COLUMNS:", model.__tablename__, sorted(expected - actual))
        connection.rollback()
    print("EXPECTED_MIGRATION_HEADS:", ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
except Exception as exc:
    report_error(exc)

with SessionLocal() as session:
    try:
        session.execute(text("SET TRANSACTION READ ONLY"))
        authenticate_user(session, LoginRequest(email="deployment-diagnostic-unregistered@example.com", password="diagnostic-invalid-password"))
        print("UNEXPECTED: diagnostic credentials were accepted")
    except InvalidCredentialsError:
        print("AUTH_DATABASE_QUERY: OK (invalid credentials rejected)")
    except Exception as exc:
        report_error(exc)
    finally:
        session.rollback()
