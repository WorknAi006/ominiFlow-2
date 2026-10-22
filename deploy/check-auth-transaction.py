"""Exercise real registration/login against PostgreSQL; roll back all test rows."""
import secrets
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.main import app

identity = uuid.uuid4().hex
password = secrets.token_urlsafe(32)
connection = engine.connect()
transaction = connection.begin()


def isolated_session():
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = isolated_session
try:
    with TestClient(app, raise_server_exceptions=False) as client:
        email = f"deployment-check-{identity}@example.com"
        response = client.post("/api/v1/auth/register", json={
            "email": email, "password": password, "first_name": "Deployment",
            "last_name": "Check", "tenant_name": f"Deployment check {identity}",
        })
        print("REGISTRATION_STATUS:", response.status_code)
        assert response.status_code == 201, "Registration failed"
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        print("LOGIN_STATUS:", response.status_code)
        assert response.status_code == 200, "Login failed"
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        response = client.get("/api/v1/tenants/current", headers=headers)
        print("AUTHENTICATED_WORKSPACE_STATUS:", response.status_code)
        assert response.status_code == 200, "Authenticated workspace request failed"
        response = client.post("/api/v1/auth/logout", headers=headers)
        print("LOGOUT_STATUS:", response.status_code)
        assert response.status_code == 204, "Logout failed"
        response = client.get("/api/v1/tenants/current", headers=headers)
        print("REVOKED_SESSION_STATUS:", response.status_code)
        assert response.status_code == 401, "Session revocation failed"
finally:
    app.dependency_overrides.pop(get_db, None)
    transaction.rollback()
    connection.close()
    print("TEST_RECORDS: rolled back")
