"""Read-only auth diagnosis. Never print credentials, tokens or user records."""
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select, text, create_engine
from sqlalchemy.engine import make_url, URL
from sqlalchemy.orm import configure_mappers

from app.core.database import engine, SessionLocal
from app.models import User, Tenant, TenantMembership, UserSession
from app.schemas.auth import LoginRequest
from app.services.auth_service import authenticate_user, InvalidCredentialsError
from app.core.config import settings
import os
from pathlib import Path


def report_error(exc):
    original = getattr(exc, "orig", exc)
    print("ERROR_TYPE:", type(exc).__name__, type(original).__name__)
    print("ERROR_DETAIL:", str(original)[:1800])


def url_summary(value):
    if not value:
        return None
    url = make_url(value)
    return dict(host=url.host, port=url.port, database=url.database, user=url.username)


print("SETTINGS_DATABASE_TARGET:", url_summary(settings.database_url))
print("CONTAINER_DATABASE_TARGET:", url_summary(os.environ.get("DATABASE_URL")))
for proc in Path('/proc').glob('[0-9]*'):
    try:
        command = (proc / 'cmdline').read_bytes()
        if b'uvicorn' not in command:
            continue
        environment = dict(item.split(b'=',1) for item in (proc/'environ').read_bytes().split(b'\0') if b'=' in item)
        print("UVICORN_DATABASE_TARGET:", proc.name, url_summary(environment.get(b'DATABASE_URL',b'').decode()))
    except (OSError, ValueError):
        pass

if os.environ.get('POSTGRES_PASSWORD'):
    candidate = URL.create('postgresql+psycopg', username='fmfilms', password=os.environ['POSTGRES_PASSWORD'], host='postgres', port=5432, database='fmfilms')
    try:
        probe = create_engine(candidate, connect_args={'connect_timeout':5}, hide_parameters=True)
        with probe.connect() as connection:
            connection.execute(text('SET TRANSACTION READ ONLY'))
            print('DOCKER_DATABASE_PROBE:', tuple(connection.execute(text('SELECT current_database(), current_user')).one()))
        probe.dispose()
    except Exception as exc:
        report_error(exc)


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
