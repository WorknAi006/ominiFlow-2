"""
Comprehensive test suite for Platform Admin operations, Multi-Tenant management,
role enforcement, and tenant boundary verification.
"""
import uuid
from typing import Any

from app.core.security import create_access_token, hash_password
from app.models import (
    ChannelConnection,
    ChannelStatus,
    ChannelType,
    Conversation,
    Role,
    Tenant,
    TenantAiCredit,
    TenantMembership,
    User,
)
from tests.base import TEST_PASSWORD, DatabaseTestCase, bearer, unique


class AdminPlatformTests(DatabaseTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        # Platform Super Admin
        cls.super_admin = cls.make_user("platform_admin")
        cls.super_admin.is_platform_super_admin = True
        cls.db.commit()

        # Tenant A (active)
        cls.tenant_a = cls.make_tenant("Gym Alpha")
        cls.owner_a = cls.make_member(cls.tenant_a, "OWNER")
        cls.agent_a = cls.make_member(cls.tenant_a, "AGENT")

        # Tenant B (active)
        cls.tenant_b = cls.make_tenant("Gym Beta")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")

        # Connect a dummy WhatsApp channel to Tenant A
        cls.channel_a = ChannelConnection(
            id=uuid.uuid4(),
            tenant_id=cls.tenant_a.id,
            name="Alpha WhatsApp",
            channel_type=ChannelType.WHATSAPP,
            status=ChannelStatus.CONNECTED,
            external_account_id=f"phone_{uuid.uuid4().hex[:8]}",
            external_business_id=f"waba_{uuid.uuid4().hex[:8]}",
            access_token_encrypted=b"dummy_encrypted_token",
            is_active=True,
            is_deleted=False,
        )
        cls.db.add(cls.channel_a)
        cls.db.commit()

    def admin_headers(self) -> dict[str, str]:
        token = create_access_token(
            subject=str(self.super_admin.id),
            extra_claims={"is_platform_admin": True},
        )
        return bearer(token)

    # =========================================================================
    # PHASE 1: ADMIN AUTHENTICATION & ACCESS CONTROL
    # =========================================================================

    def test_super_admin_login_success(self):
        response = self.client.post(
            "/api/v1/admin/auth/login",
            json={"email": self.super_admin.email, "password": TEST_PASSWORD},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertTrue(data["user"]["is_platform_admin"])

    def test_regular_tenant_owner_denied_admin_login(self):
        response = self.client.post(
            "/api/v1/admin/auth/login",
            json={"email": self.owner_a.email, "password": TEST_PASSWORD},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("not authorized for platform administration", response.text)

    def test_regular_user_cannot_access_admin_endpoints(self):
        # Tenant token
        tenant_token = self.auth(self.owner_a, self.tenant_a)
        response = self.client.get("/api/v1/admin/tenants", headers=tenant_token)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Super admin authorization required", response.text)

    def test_unauthenticated_admin_request_rejected(self):
        response = self.client.get("/api/v1/admin/tenants")
        self.assertEqual(response.status_code, 401)

    # =========================================================================
    # PHASE 2: ADMIN TENANTS DIRECTORY, SEARCH, AND STATS
    # =========================================================================

    def test_list_tenants_returns_accurate_metadata(self):
        headers = self.admin_headers()
        response = self.client.get("/api/v1/admin/tenants?page=1&page_size=20", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertIn("items", data)
        self.assertGreaterEqual(data["total"], 2)

        # Find Tenant A in results
        t_a = next((item for item in data["items"] if item["id"] == str(self.tenant_a.id)), None)
        self.assertIsNotNone(t_a)
        self.assertEqual(t_a["name"], "Gym Alpha")
        self.assertEqual(t_a["user_count"], 2)  # owner + agent
        self.assertEqual(t_a["channel_count"], 1)  # 1 connected channel
        self.assertTrue(t_a["is_active"])

    def test_search_tenants_by_name_and_slug(self):
        headers = self.admin_headers()
        response = self.client.get("/api/v1/admin/tenants?search=Alpha", headers=headers)
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertTrue(any(t["name"] == "Gym Alpha" for t in items))
        self.assertFalse(any(t["name"] == "Gym Beta" for t in items))

    def test_filter_tenants_by_status(self):
        headers = self.admin_headers()
        # Suspend Tenant B temporarily
        self.tenant_b.is_active = False
        self.db.commit()

        # Active filter
        active_resp = self.client.get("/api/v1/admin/tenants?status=active", headers=headers)
        self.assertEqual(active_resp.status_code, 200)
        self.assertTrue(all(t["is_active"] is True for t in active_resp.json()["items"]))

        # Suspended filter
        susp_resp = self.client.get("/api/v1/admin/tenants?status=suspended", headers=headers)
        self.assertEqual(susp_resp.status_code, 200)
        self.assertTrue(all(t["is_active"] is False for t in susp_resp.json()["items"]))

        # Restore
        self.tenant_b.is_active = True
        self.db.commit()

    # =========================================================================
    # PHASE 3: PROVISIONING NEW TENANT (CREATE TENANT)
    # =========================================================================

    def test_create_tenant_provisions_organization_and_owner(self):
        headers = self.admin_headers()
        org_name = f"Fitness Hub {uuid.uuid4().hex[:6]}"
        owner_email = f"owner_{uuid.uuid4().hex[:6]}@fitnesshub.com"

        response = self.client.post(
            "/api/v1/admin/tenants",
            headers=headers,
            json={
                "name": org_name,
                "email": owner_email,
                "owner_email": owner_email,
                "owner_first_name": "Marcus",
                "owner_last_name": "Vance",
                "plan": "Standard",
                "initial_credits": 750.0,
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertEqual(data["tenant"]["name"], org_name)
        self.assertIsNotNone(data["tenant"]["slug"])
        self.assertEqual(data["owner_user"]["email"], owner_email)
        self.assertEqual(data["initial_credits"], 750.0)

        # Verify DB records
        created_tenant_id = uuid.UUID(data["tenant"]["id"])
        tenant_db = self.db.query(Tenant).filter(Tenant.id == created_tenant_id).first()
        self.assertIsNotNone(tenant_db)

        # Verify membership
        owner_db = self.db.query(User).filter(User.email == owner_email).first()
        membership = self.db.query(TenantMembership).filter(
            TenantMembership.tenant_id == created_tenant_id,
            TenantMembership.user_id == owner_db.id,
        ).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.status, "active")

        # Verify AI credits
        credits = self.db.query(TenantAiCredit).filter(TenantAiCredit.tenant_id == created_tenant_id).first()
        self.assertIsNotNone(credits)
        self.assertEqual(float(credits.balance), 750.0)

    # =========================================================================
    # PHASE 4: INSPECT, SUSPEND, RESTORE, AND DELETE TENANT
    # =========================================================================

    def test_inspect_tenant_detail(self):
        headers = self.admin_headers()
        response = self.client.get(f"/api/v1/admin/tenants/{self.tenant_a.id}", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["name"], "Gym Alpha")
        self.assertEqual(data["user_count"], 2)
        self.assertEqual(data["channel_count"], 1)
        self.assertGreaterEqual(len(data["users"]), 2)
        self.assertEqual(len(data["channels"]), 1)

    def test_suspend_and_restore_tenant_lifecycle(self):
        headers = self.admin_headers()
        tenant_headers = self.auth(self.owner_a, self.tenant_a)

        # Baseline: Tenant A active
        base_resp = self.client.get("/api/v1/tenants/current", headers=tenant_headers)
        self.assertEqual(base_resp.status_code, 200)

        # 1. Suspend Tenant A
        suspend_resp = self.client.patch(
            f"/api/v1/admin/tenants/{self.tenant_a.id}/status",
            headers=headers,
            json={"is_active": False},
        )
        self.assertEqual(suspend_resp.status_code, 200)

        # 2. Verify tenant user is now blocked from API
        blocked_resp = self.client.get("/api/v1/tenants/current", headers=tenant_headers)
        self.assertEqual(blocked_resp.status_code, 403)

        # 3. Restore Tenant A
        restore_resp = self.client.patch(
            f"/api/v1/admin/tenants/{self.tenant_a.id}/status",
            headers=headers,
            json={"is_active": True},
        )
        self.assertEqual(restore_resp.status_code, 200)

        # 4. Verify tenant user access is restored
        restored_resp = self.client.get("/api/v1/tenants/current", headers=tenant_headers)
        self.assertEqual(restored_resp.status_code, 200)

    def test_delete_tenant_soft_deletes_and_revokes_access(self):
        headers = self.admin_headers()
        # Create a disposable tenant
        disposable = self.make_tenant("To Delete")
        disp_owner = self.make_member(disposable, "OWNER")
        disp_headers = self.auth(disp_owner, disposable)

        del_resp = self.client.delete(f"/api/v1/admin/tenants/{disposable.id}", headers=headers)
        self.assertEqual(del_resp.status_code, 200)

        # Verify access revoked
        access_resp = self.client.get("/api/v1/tenants/current", headers=disp_headers)
        self.assertEqual(access_resp.status_code, 403)

        # Verify excluded from admin tenant list
        list_resp = self.client.get("/api/v1/admin/tenants", headers=headers)
        self.assertFalse(any(t["id"] == str(disposable.id) for t in list_resp.json()["items"]))

    # =========================================================================
    # PHASE 5: ADMIN USER MANAGEMENT & CROSS-TENANT ISOLATION
    # =========================================================================

    def test_admin_create_and_delete_user(self):
        headers = self.admin_headers()
        new_email = f"staff_{uuid.uuid4().hex[:6]}@gymalpha.com"

        # Create user assigned to Tenant A as AGENT
        create_resp = self.client.post(
            "/api/v1/admin/users",
            headers=headers,
            json={
                "email": new_email,
                "password": TEST_PASSWORD,
                "first_name": "Elena",
                "last_name": "Rostova",
                "is_platform_admin": False,
                "tenant_id": str(self.tenant_a.id),
                "role_name": "AGENT",
            },
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        user_id = create_resp.json()["id"]

        # Delete user
        del_resp = self.client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
        self.assertEqual(del_resp.status_code, 200)

    def test_cross_tenant_resource_isolation(self):
        # Tenant A user trying to access Tenant B channels
        headers_a = self.auth(self.owner_a, self.tenant_a)
        response = self.client.get(
            f"/api/v1/channels/{self.channel_a.id}",
            headers=self.auth(self.owner_b, self.tenant_b),  # Owner B tries to get Channel A
        )
        self.assertEqual(response.status_code, 404)
