"""
Regression tests for authentication, auth dependencies, tenant context,
RBAC and tenant management.
"""
import uuid

import jwt

from app.core.security import create_access_token, decode_token
from tests.base import TEST_PASSWORD, DatabaseTestCase, bearer, unique

TENANT_URL = "/api/v1/tenants/current"
SAFE_TENANT_FIELDS = {
    "id", "name", "slug", "email", "phone", "description",
    "is_active", "created_at", "updated_at",
}


class AuthTenantTests(DatabaseTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant_a = cls.make_tenant("Tenant A")
        cls.owner_a = cls.make_member(cls.tenant_a, "OWNER")
        cls.viewer_a = cls.make_member(cls.tenant_a, "VIEWER")

        cls.tenant_b = cls.make_tenant("Tenant B")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

        cls.inactive_user = cls.make_user("inactive", is_active=False)
        cls.add_member(cls.inactive_user, cls.tenant_a, "OWNER")

    # ---------- health ----------

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_database_health(self):
        response = self.client.get("/health/database")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    # ---------- register / login ----------

    def test_register(self):
        response = self.client.post("/api/v1/auth/register", json={
            "email": f"{unique('reg')}@test.omniflow",
            "password": TEST_PASSWORD,
            "first_name": "Reg",
            "tenant_name": f"Reg Tenant {uuid.uuid4().hex[:8]}",
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotIn("password_hash", response.text)

        token = response.json()["access_token"]
        tenant = self.client.get(TENANT_URL, headers=bearer(token))
        self.assertEqual(tenant.status_code, 200)

    def test_login(self):
        response = self.client.post("/api/v1/auth/login", json={
            "email": f"  {self.owner_a.email.upper()} ",
            "password": TEST_PASSWORD,
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["tenant"]["id"], str(self.tenant_a.id))
        self.assertNotIn("password_hash", response.text)

        claims = decode_token(body["access_token"])
        self.assertEqual(claims["type"], "access")
        self.assertEqual(claims["sub"], str(self.owner_a.id))
        self.assertEqual(claims["tenant_id"], str(self.tenant_a.id))

    def test_login_failures_are_identical(self):
        wrong_password = self.client.post("/api/v1/auth/login", json={
            "email": self.owner_a.email, "password": "WrongPassword",
        })
        unknown_email = self.client.post("/api/v1/auth/login", json={
            "email": "nobody@test.omniflow", "password": TEST_PASSWORD,
        })
        for response in (wrong_password, unknown_email):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(
                response.json(), {"detail": "Invalid email or password."}
            )

    # ---------- authentication dependency ----------

    def test_valid_token(self):
        response = self.client.get(
            TENANT_URL, headers=self.auth(self.owner_a, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_header(self):
        response = self.client.get(TENANT_URL)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Could not validate credentials."}
        )
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_non_bearer_scheme(self):
        token = self.token_for(self.owner_a, self.tenant_a)
        response = self.client.get(
            TENANT_URL, headers={"Authorization": f"Basic {token}"}
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_tokens(self):
        forged = jwt.encode(
            {
                "sub": str(self.owner_a.id),
                "type": "access",
                "tenant_id": str(self.tenant_a.id),
            },
            "wrong-secret-wrong-secret-wrong-secret",
            algorithm="HS256",
        )
        tokens = [
            "not.a.jwt",
            forged,
            create_access_token(
                subject="not-a-uuid",
                extra_claims={"tenant_id": str(self.tenant_a.id)},
            ),
            create_access_token(subject=str(self.owner_a.id)),
            create_access_token(
                subject=str(uuid.uuid4()),
                extra_claims={"tenant_id": str(self.tenant_a.id)},
            ),
        ]
        for token in tokens:
            with self.subTest(token=token[:20]):
                response = self.client.get(TENANT_URL, headers=bearer(token))
                self.assertEqual(response.status_code, 401)

    def test_expired_token(self):
        token = self.token_for(self.owner_a, self.tenant_a, expires_minutes=-1)
        response = self.client.get(TENANT_URL, headers=bearer(token))
        self.assertEqual(response.status_code, 401)

    def test_wrong_token_type(self):
        token = self.token_for(
            self.owner_a, self.tenant_a, extra={"type": "refresh"}
        )
        response = self.client.get(TENANT_URL, headers=bearer(token))
        self.assertEqual(response.status_code, 401)

    def test_inactive_user(self):
        response = self.client.get(
            TENANT_URL, headers=self.auth(self.inactive_user, self.tenant_a)
        )
        self.assertEqual(response.status_code, 401)

    # ---------- tenant context ----------

    def test_get_current_tenant(self):
        response = self.client.get(
            TENANT_URL, headers=self.auth(self.owner_a, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), SAFE_TENANT_FIELDS)
        self.assertEqual(body["id"], str(self.tenant_a.id))
        self.assertEqual(body["slug"], self.tenant_a.slug)

    def test_inactive_membership(self):
        membership = self.add_member(
            self.make_user("suspended"), self.tenant_a, "VIEWER"
        )
        membership.status = "suspended"
        self.db.commit()

        user_id = membership.user_id
        token = create_access_token(
            subject=str(user_id),
            extra_claims={"tenant_id": str(self.tenant_a.id)},
        )
        response = self.client.get(TENANT_URL, headers=bearer(token))
        self.assertEqual(response.status_code, 403)

    def test_deleted_and_inactive_tenant(self):
        headers = self.auth(self.owner_b, self.tenant_b)

        self.tenant_b.is_deleted = True
        self.db.commit()
        self.assertEqual(
            self.client.get(TENANT_URL, headers=headers).status_code, 403
        )

        self.tenant_b.is_deleted = False
        self.tenant_b.is_active = False
        self.db.commit()
        self.assertEqual(
            self.client.get(TENANT_URL, headers=headers).status_code, 403
        )

    def test_cross_tenant_access(self):
        headers = self.auth(self.owner_a, self.tenant_b)

        response = self.client.get(TENANT_URL, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": "You do not have access to this workspace."},
        )

        response = self.client.patch(
            TENANT_URL, headers=headers, json={"name": "Hacked"}
        )
        self.assertEqual(response.status_code, 403)

    def test_tenant_id_query_and_body_ignored(self):
        headers = self.auth(self.owner_a, self.tenant_a)

        response = self.client.get(
            f"{TENANT_URL}?tenant_id={self.tenant_b.id}", headers=headers
        )
        self.assertEqual(response.json()["id"], str(self.tenant_a.id))

        response = self.client.patch(
            TENANT_URL,
            headers=headers,
            json={"tenant_id": str(self.tenant_b.id), "name": "X Name"},
        )
        self.assertEqual(response.status_code, 422)

    # ---------- tenant management / RBAC ----------

    def test_patch_tenant(self):
        headers = self.auth(self.owner_a, self.tenant_a)
        before = self.client.get(TENANT_URL, headers=headers).json()

        response = self.client.patch(TENANT_URL, headers=headers, json={
            "name": "  Tenant A Updated ",
            "email": "Contact@Omniflow.com",
            "phone": "+1 555-123-4567",
            "description": "Demo workspace",
        })
        self.assertEqual(response.status_code, 200, response.text)
        after = response.json()

        self.assertEqual(after["name"], "Tenant A Updated")
        self.assertEqual(after["email"], "contact@omniflow.com")
        self.assertEqual(after["phone"], "+1 555-123-4567")
        self.assertEqual(after["description"], "Demo workspace")
        for field in ("id", "slug", "is_active", "created_at"):
            self.assertEqual(after[field], before[field])

    def test_patch_tenant_protected_fields_rejected(self):
        headers = self.auth(self.owner_a, self.tenant_a)
        protected = {
            "slug": "hijack",
            "is_active": False,
            "is_deleted": True,
            "id": str(uuid.uuid4()),
            "created_at": "2020-01-01T00:00:00Z",
            "owner_id": str(self.owner_b.id),
        }
        for field, value in protected.items():
            with self.subTest(field=field):
                response = self.client.patch(
                    TENANT_URL, headers=headers,
                    json={"name": "Valid Name", field: value},
                )
                self.assertEqual(response.status_code, 422)

        for body in ({}, {"name": None}, {"name": "x"},
                     {"email": "not-an-email"}, {"phone": "abc"}):
            with self.subTest(body=body):
                response = self.client.patch(
                    TENANT_URL, headers=headers, json=body
                )
                self.assertEqual(response.status_code, 422)

    def test_viewer_cannot_update_tenant(self):
        headers = self.auth(self.viewer_a, self.tenant_a)

        self.assertEqual(
            self.client.get(TENANT_URL, headers=headers).status_code, 200
        )

        response = self.client.patch(
            TENANT_URL, headers=headers, json={"name": "Viewer Edit"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": "You do not have permission to perform this action."},
        )
