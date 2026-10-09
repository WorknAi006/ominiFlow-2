"""
Tests for Users & Team Management: listing, invitations, updates,
removal, owner protection, RBAC and tenant isolation.
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.models import Role, TeamInvitation, TenantMembership, User
from tests.base import TEST_PASSWORD, DatabaseTestCase, bearer

USERS_URL = "/api/v1/users"
INVITE_URL = "/api/v1/users/invite"
INVITATIONS_URL = "/api/v1/users/invitations"
ACCEPT_URL = "/api/v1/users/invitations/accept"
TENANT_URL = "/api/v1/tenants/current"

MEMBER_FIELDS = {
    "id", "email", "first_name", "last_name", "role", "role_id",
    "membership_status", "is_active", "is_verified", "created_at",
}

FORBIDDEN = {"detail": "You do not have permission to perform this action."}


class TeamTestCase(DatabaseTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        cls.tenant_a = cls.make_tenant("Tenant A")
        cls.owner = cls.make_member(cls.tenant_a, "OWNER")
        cls.admin = cls.make_member(cls.tenant_a, "ADMIN")
        cls.manager = cls.make_member(cls.tenant_a, "MANAGER")
        cls.agent = cls.make_member(cls.tenant_a, "AGENT")
        cls.viewer = cls.make_member(cls.tenant_a, "VIEWER")
        cls.developer = cls.make_member(
            cls.tenant_a, "DEVELOPER", first_name="Zebrafish",
        )

        cls.tenant_b = cls.make_tenant("Tenant B")
        cls.owner_b = cls.make_member(cls.tenant_b, "OWNER")
        cls.member_b = cls.make_member(cls.tenant_b, "AGENT")

        # Agent also belongs to tenant B, to check cross-tenant effects.
        cls.add_member(cls.agent, cls.tenant_b, "VIEWER")

        cls.roles = {
            role.name: role for role in cls.db.query(Role).all()
        }

    # ---------- helpers ----------

    def role_id(self, name: str) -> str:
        return str(self.roles[name].id)

    def invite(self, actor, email, role_name="AGENT", tenant=None):
        return self.client.post(
            INVITE_URL,
            headers=self.auth(actor, tenant or self.tenant_a),
            json={"email": email, "role_id": self.role_id(role_name)},
        )

    def invite_token(self, email, role_name="AGENT"):
        response = self.invite(self.owner, email, role_name)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def accept(self, token, **fields):
        body = {"token": token, "password": TEST_PASSWORD, **fields}
        return self.client.post(ACCEPT_URL, json=body)

    def patch_member(self, actor, target_id, body, tenant=None):
        return self.client.patch(
            f"{USERS_URL}/{target_id}",
            headers=self.auth(actor, tenant or self.tenant_a),
            json=body,
        )

    def delete_member(self, actor, target_id, tenant=None):
        return self.client.delete(
            f"{USERS_URL}/{target_id}",
            headers=self.auth(actor, tenant or self.tenant_a),
        )

    def list_emails(self, actor, query=""):
        response = self.client.get(
            f"{USERS_URL}{query}", headers=self.auth(actor, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {item["email"] for item in response.json()["items"]}

    def tenant_a_emails(self):
        return {
            user.email for user in (
                self.owner, self.admin, self.manager,
                self.agent, self.viewer, self.developer,
            )
        }


class AuthorizationTests(TeamTestCase):

    def test_01_missing_jwt(self):
        self.assertEqual(self.client.get(USERS_URL).status_code, 401)

    def test_02_invalid_jwt(self):
        response = self.client.get(USERS_URL, headers=bearer("not.a.jwt"))
        self.assertEqual(response.status_code, 401)

    def test_03_no_permission(self):
        response = self.delete_member(self.agent, self.viewer.id)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), FORBIDDEN)


class ListTests(TeamTestCase):

    def test_04_to_07_roles_can_list_own_tenant_only(self):
        for actor in (self.owner, self.admin, self.agent, self.viewer):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.list_emails(actor), self.tenant_a_emails())

    def test_list_response_fields(self):
        response = self.client.get(
            USERS_URL, headers=self.auth(self.owner, self.tenant_a)
        )
        body = response.json()
        self.assertEqual(body["total"], 6)
        self.assertEqual(set(body["items"][0]), MEMBER_FIELDS)

        owner_item = next(
            item for item in body["items"] if item["email"] == self.owner.email
        )
        self.assertEqual(owner_item["role"], "OWNER")
        self.assertEqual(owner_item["membership_status"], "active")

    def test_08_pagination(self):
        headers = self.auth(self.owner, self.tenant_a)
        seen = []
        for page in (1, 2, 3):
            body = self.client.get(
                f"{USERS_URL}?page={page}&page_size=2", headers=headers
            ).json()
            self.assertEqual(body["total"], 6)
            self.assertEqual(body["page"], page)
            self.assertEqual(len(body["items"]), 2)
            seen += [item["id"] for item in body["items"]]
        self.assertEqual(len(set(seen)), 6)

        body = self.client.get(
            f"{USERS_URL}?page=4&page_size=2", headers=headers
        ).json()
        self.assertEqual(body["items"], [])

        for query in ("?page=0", "?page_size=0", "?page_size=101", "?page=abc"):
            with self.subTest(query=query):
                response = self.client.get(f"{USERS_URL}{query}", headers=headers)
                self.assertEqual(response.status_code, 422)

    def test_09_search(self):
        self.assertEqual(
            self.list_emails(self.owner, "?search=zebraFISH"),
            {self.developer.email},
        )
        self.assertEqual(
            self.list_emails(self.owner, f"?search={self.manager.email[:12]}"),
            {self.manager.email},
        )
        # LIKE wildcards are escaped, not interpreted.
        self.assertEqual(self.list_emails(self.owner, "?search=%25"), set())
        self.assertEqual(self.list_emails(self.owner, "?search=_"), set())
        # Members of other tenants are never matched.
        self.assertEqual(
            self.list_emails(self.owner, f"?search={self.member_b.email}"),
            set(),
        )

    def test_suspended_listed_removed_hidden(self):
        self.patch_member(self.owner, self.viewer.id, {"status": "suspended"})
        self.delete_member(self.owner, self.developer.id)

        response = self.client.get(
            USERS_URL, headers=self.auth(self.owner, self.tenant_a)
        )
        items = {item["email"]: item for item in response.json()["items"]}
        self.assertEqual(items[self.viewer.email]["membership_status"], "suspended")
        self.assertNotIn(self.developer.email, items)

    def test_get_single_member(self):
        response = self.client.get(
            f"{USERS_URL}/{self.agent.id}",
            headers=self.auth(self.viewer, self.tenant_a),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), MEMBER_FIELDS)
        self.assertEqual(body["email"], self.agent.email)
        self.assertEqual(body["role"], "AGENT")

    def test_get_member_of_other_tenant_is_404(self):
        headers = self.auth(self.owner, self.tenant_a)
        for user_id in (self.member_b.id, self.owner_b.id, uuid.uuid4()):
            with self.subTest(user_id=user_id):
                response = self.client.get(
                    f"{USERS_URL}/{user_id}", headers=headers
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json(), {"detail": "Team member not found."}
                )

        response = self.client.get(f"{USERS_URL}/not-a-uuid", headers=headers)
        self.assertEqual(response.status_code, 422)


class InviteTests(TeamTestCase):

    def test_10_owner_can_invite(self):
        response = self.invite(self.owner, "New.Person@Example.COM ", "ADMIN")
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["email"], "new.person@example.com")
        self.assertEqual(body["role"], "ADMIN")
        self.assertTrue(body["invitation_token"])
        self.assertNotIn("token_hash", body)

        invitation = self.db.get(TeamInvitation, uuid.UUID(body["id"]))
        self.assertEqual(invitation.tenant_id, self.tenant_a.id)
        self.assertEqual(invitation.created_by, self.owner.id)
        self.assertNotEqual(invitation.token_hash, body["invitation_token"])
        self.assertEqual(len(invitation.token_hash), 64)

    def test_11_admin_can_invite(self):
        self.assertEqual(
            self.invite(self.admin, "admin-invite@example.com").status_code, 201
        )

    def test_12_manager_can_invite_lower_roles_only(self):
        self.assertEqual(
            self.invite(self.manager, "mgr-invite@example.com", "AGENT").status_code,
            201,
        )
        for role_name in ("ADMIN", "OWNER"):
            with self.subTest(role=role_name):
                response = self.invite(
                    self.manager, f"esc-{role_name}@example.com", role_name
                )
                self.assertEqual(response.status_code, 403)

    def test_admin_cannot_invite_owner(self):
        response = self.invite(self.admin, "owner-invite@example.com", "OWNER")
        self.assertEqual(response.status_code, 403)

    def test_13_14_agent_and_viewer_cannot_invite(self):
        for actor in (self.agent, self.viewer):
            with self.subTest(actor=actor.email):
                response = self.invite(actor, "nope@example.com")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), FORBIDDEN)

    def test_15_invalid_role_rejected(self):
        inactive = Role(name=f"INACTIVE_{uuid.uuid4().hex[:6]}", is_active=False)
        self.db.add(inactive)
        self.db.commit()

        headers = self.auth(self.owner, self.tenant_a)
        for role_id in (str(uuid.uuid4()), str(inactive.id)):
            with self.subTest(role_id=role_id):
                response = self.client.post(INVITE_URL, headers=headers, json={
                    "email": "bad-role@example.com", "role_id": role_id,
                })
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json(), {"detail": "Invalid role."})

        for body in (
            {"email": "not-an-email", "role_id": self.role_id("AGENT")},
            {"email": "x@example.com", "role_id": "not-a-uuid"},
            {"email": "x@example.com"},
        ):
            with self.subTest(body=body):
                response = self.client.post(INVITE_URL, headers=headers, json=body)
                self.assertEqual(response.status_code, 422)

    def test_16_duplicate_membership_rejected(self):
        for email in (self.agent.email, self.agent.email.upper()):
            with self.subTest(email=email):
                response = self.invite(self.owner, email)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.json(),
                    {"detail": "This user is already a member of this workspace."},
                )

    def test_17_duplicate_active_invitation_rejected(self):
        self.assertEqual(self.invite(self.owner, "dup@example.com").status_code, 201)

        response = self.invite(self.admin, "DUP@example.com", "VIEWER")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"detail": "An active invitation already exists for this email."},
        )

    def test_same_email_can_be_invited_by_another_tenant(self):
        self.assertEqual(self.invite(self.owner, "shared@example.com").status_code, 201)
        response = self.invite(
            self.owner_b, "shared@example.com", tenant=self.tenant_b
        )
        self.assertEqual(response.status_code, 201)

    def test_expired_invitation_can_be_reissued(self):
        first = self.invite_token("reissue@example.com")
        invitation = self.db.get(TeamInvitation, uuid.UUID(first["id"]))
        invitation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()

        second = self.invite(self.owner, "reissue@example.com")
        self.assertEqual(second.status_code, 201)

        self.db.expire_all()
        self.assertIsNotNone(
            self.db.get(TeamInvitation, uuid.UUID(first["id"])).revoked_at
        )

    def test_removed_member_can_be_reinvited(self):
        self.assertEqual(self.delete_member(self.owner, self.viewer.id).status_code, 204)
        self.assertEqual(self.invite(self.owner, self.viewer.email).status_code, 201)

    def test_list_and_revoke_invitations(self):
        invitation = self.invite_token("listed@example.com")

        response = self.client.get(
            INVITATIONS_URL, headers=self.auth(self.viewer, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([i["email"] for i in response.json()], ["listed@example.com"])
        self.assertNotIn("invitation_token", response.text)
        self.assertNotIn("token_hash", response.text)

        # Other tenants cannot see or revoke it.
        response = self.client.get(
            INVITATIONS_URL, headers=self.auth(self.owner_b, self.tenant_b)
        )
        self.assertEqual(response.json(), [])
        response = self.client.delete(
            f"{INVITATIONS_URL}/{invitation['id']}",
            headers=self.auth(self.owner_b, self.tenant_b),
        )
        self.assertEqual(response.status_code, 404)

        # Viewer lacks user:create.
        response = self.client.delete(
            f"{INVITATIONS_URL}/{invitation['id']}",
            headers=self.auth(self.viewer, self.tenant_a),
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(
            f"{INVITATIONS_URL}/{invitation['id']}",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 204)

        response = self.client.get(
            INVITATIONS_URL, headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertEqual(response.json(), [])

    def test_manager_cannot_revoke_admin_invitation(self):
        invitation = self.invite_token("admin-to-be@example.com", "ADMIN")
        response = self.client.delete(
            f"{INVITATIONS_URL}/{invitation['id']}",
            headers=self.auth(self.manager, self.tenant_a),
        )
        self.assertEqual(response.status_code, 403)


class UpdateTests(TeamTestCase):

    def test_18_owner_can_update_role_and_status(self):
        response = self.patch_member(
            self.owner, self.agent.id,
            {"role_id": self.role_id("VIEWER"), "status": "suspended"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["role"], "VIEWER")
        self.assertEqual(body["membership_status"], "suspended")

        # Suspended members lose access to this tenant only.
        self.assertEqual(
            self.client.get(
                TENANT_URL, headers=self.auth(self.agent, self.tenant_a)
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                TENANT_URL, headers=self.auth(self.agent, self.tenant_b)
            ).status_code,
            200,
        )

        response = self.patch_member(self.owner, self.agent.id, {"status": "active"})
        self.assertEqual(response.json()["membership_status"], "active")

    def test_19_admin_can_update_role_and_status(self):
        response = self.patch_member(
            self.admin, self.agent.id,
            {"role_id": self.role_id("DEVELOPER"), "status": "suspended"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["role"], "DEVELOPER")

    def test_20_manager_can_update_lower_roles_only(self):
        response = self.patch_member(
            self.manager, self.agent.id, {"role_id": self.role_id("VIEWER")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "VIEWER")

        # Escalation and managing higher roles are blocked.
        blocked = [
            (self.agent.id, {"role_id": self.role_id("ADMIN")}),
            (self.agent.id, {"role_id": self.role_id("OWNER")}),
            (self.manager.id, {"role_id": self.role_id("ADMIN")}),
            (self.admin.id, {"status": "suspended"}),
            (self.owner.id, {"status": "suspended"}),
        ]
        for target_id, body in blocked:
            with self.subTest(target=str(target_id), body=body):
                response = self.patch_member(self.manager, target_id, body)
                self.assertEqual(response.status_code, 403)

    def test_admin_cannot_manage_owner(self):
        for body in ({"status": "suspended"}, {"role_id": self.role_id("VIEWER")}):
            with self.subTest(body=body):
                response = self.patch_member(self.admin, self.owner.id, body)
                self.assertEqual(response.status_code, 403)

        response = self.patch_member(
            self.admin, self.agent.id, {"role_id": self.role_id("OWNER")}
        )
        self.assertEqual(response.status_code, 403)

    def test_21_22_agent_and_viewer_cannot_update(self):
        for actor in (self.agent, self.viewer):
            with self.subTest(actor=actor.email):
                response = self.patch_member(
                    actor, self.developer.id, {"status": "suspended"}
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), FORBIDDEN)

    def test_23_cross_tenant_update_blocked(self):
        response = self.patch_member(
            self.owner, self.member_b.id, {"status": "suspended"}
        )
        self.assertEqual(response.status_code, 404)

        # Token claiming tenant B without membership there.
        response = self.patch_member(
            self.owner, self.member_b.id, {"status": "suspended"},
            tenant=self.tenant_b,
        )
        self.assertEqual(response.status_code, 403)

        self.db.expire_all()
        membership = self.db.query(TenantMembership).filter_by(
            user_id=self.member_b.id, tenant_id=self.tenant_b.id
        ).one()
        self.assertEqual(membership.status, "active")

    def test_24_invalid_update_rejected(self):
        invalid = [
            {"role_id": str(uuid.uuid4())},
            {"role_id": "not-a-uuid"},
            {"status": "removed"},
            {"status": "deleted"},
            {"status": None},
            {"role_id": None},
            {},
            {"email": "new@example.com"},
            {"password": "NewPassword123"},
            {"password_hash": "x"},
            {"tenant_id": str(self.tenant_b.id)},
            {"id": str(uuid.uuid4())},
            {"created_at": "2020-01-01T00:00:00Z"},
            {"is_deleted": True},
        ]
        for body in invalid:
            with self.subTest(body=body):
                response = self.patch_member(self.owner, self.agent.id, body)
                self.assertEqual(response.status_code, 422)

    def test_owner_can_promote_to_owner(self):
        response = self.patch_member(
            self.owner, self.admin.id, {"role_id": self.role_id("OWNER")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "OWNER")


class DeleteTests(TeamTestCase):

    def test_25_owner_can_remove_member(self):
        response = self.delete_member(self.owner, self.agent.id)
        self.assertEqual(response.status_code, 204)

        response = self.client.get(
            f"{USERS_URL}/{self.agent.id}",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 404)

        # Existing JWT no longer grants access to tenant A.
        response = self.client.get(
            USERS_URL, headers=self.auth(self.agent, self.tenant_a)
        )
        self.assertEqual(response.status_code, 403)

        # Global user and other tenant membership are preserved.
        self.db.expire_all()
        user = self.db.get(User, self.agent.id)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        response = self.client.get(
            TENANT_URL, headers=self.auth(self.agent, self.tenant_b)
        )
        self.assertEqual(response.status_code, 200)

        # Removing again is a 404.
        self.assertEqual(self.delete_member(self.owner, self.agent.id).status_code, 404)

    def test_26_admin_can_remove_member(self):
        self.assertEqual(self.delete_member(self.admin, self.viewer.id).status_code, 204)

    def test_27_unauthorized_roles_cannot_remove(self):
        for actor in (self.manager, self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                response = self.delete_member(actor, self.viewer.id)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), FORBIDDEN)

    def test_28_cross_tenant_delete_blocked(self):
        self.assertEqual(self.delete_member(self.owner, self.member_b.id).status_code, 404)
        self.assertEqual(self.delete_member(self.owner, self.owner_b.id).status_code, 404)

        response = self.client.get(
            f"{USERS_URL}/{self.member_b.id}",
            headers=self.auth(self.owner_b, self.tenant_b),
        )
        self.assertEqual(response.status_code, 200)

    def test_29_last_owner_cannot_be_removed(self):
        response = self.delete_member(self.owner, self.owner.id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"detail": "A workspace must keep at least one active owner."},
        )

        # Admin cannot remove the owner at all.
        self.assertEqual(self.delete_member(self.admin, self.owner.id).status_code, 403)

        # With a second owner, one may be removed, but not the last.
        self.patch_member(self.owner, self.admin.id, {"role_id": self.role_id("OWNER")})
        self.assertEqual(self.delete_member(self.admin, self.owner.id).status_code, 204)
        self.assertEqual(self.delete_member(self.admin, self.admin.id).status_code, 409)

    def test_30_self_last_owner_protection(self):
        for body in (
            {"status": "suspended"},
            {"role_id": self.role_id("ADMIN")},
            {"role_id": self.role_id("VIEWER"), "status": "active"},
        ):
            with self.subTest(body=body):
                response = self.patch_member(self.owner, self.owner.id, body)
                self.assertEqual(response.status_code, 409)

        self.assertEqual(self.delete_member(self.owner, self.owner.id).status_code, 409)

        # Suspended owners do not count as active owners.
        self.patch_member(self.owner, self.admin.id, {"role_id": self.role_id("OWNER")})
        self.patch_member(self.owner, self.admin.id, {"status": "suspended"})
        self.assertEqual(
            self.patch_member(
                self.owner, self.owner.id, {"role_id": self.role_id("ADMIN")}
            ).status_code,
            409,
        )

        # Owner still has access after all rejected attempts.
        response = self.client.get(
            TENANT_URL, headers=self.auth(self.owner, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)


class InvitationAcceptTests(TeamTestCase):

    def test_31_valid_invitation_accepted_new_user(self):
        invitation = self.invite_token("brand.new@example.com", "MANAGER")

        response = self.accept(
            invitation["invitation_token"],
            first_name="  Brand ", last_name="New",
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["user"]["email"], "brand.new@example.com")
        self.assertEqual(body["user"]["first_name"], "Brand")
        self.assertEqual(body["tenant"]["id"], str(self.tenant_a.id))

        # The returned JWT works and has the invited role.
        headers = bearer(body["access_token"])
        me = self.client.get(f"{USERS_URL}/{body['user']['id']}", headers=headers)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["role"], "MANAGER")

        # The new user can log in.
        login = self.client.post("/api/v1/auth/login", json={
            "email": "brand.new@example.com", "password": TEST_PASSWORD,
        })
        self.assertEqual(login.status_code, 200)

        self.db.expire_all()
        stored = self.db.get(TeamInvitation, uuid.UUID(invitation["id"]))
        self.assertIsNotNone(stored.accepted_at)

    def test_new_user_requires_first_name(self):
        invitation = self.invite_token("noname@example.com")
        response = self.accept(invitation["invitation_token"])
        self.assertEqual(response.status_code, 422)

        # The invitation remains usable.
        response = self.accept(invitation["invitation_token"], first_name="Named")
        self.assertEqual(response.status_code, 200)

    def test_32_expired_invitation_rejected(self):
        invitation = self.invite_token("expired@example.com")
        stored = self.db.get(TeamInvitation, uuid.UUID(invitation["id"]))
        stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()

        response = self.accept(invitation["invitation_token"], first_name="E")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid or expired invitation."})

    def test_33_revoked_invitation_rejected(self):
        invitation = self.invite_token("revoked@example.com")
        self.client.delete(
            f"{INVITATIONS_URL}/{invitation['id']}",
            headers=self.auth(self.owner, self.tenant_a),
        )
        response = self.accept(invitation["invitation_token"], first_name="R")
        self.assertEqual(response.status_code, 400)

    def test_34_already_accepted_invitation_rejected(self):
        invitation = self.invite_token("twice@example.com")
        token = invitation["invitation_token"]
        self.assertEqual(self.accept(token, first_name="T").status_code, 200)

        response = self.accept(token, first_name="T")
        self.assertEqual(response.status_code, 400)

    def test_35_invalid_token_rejected(self):
        response = self.accept("x" * 43, first_name="X")
        self.assertEqual(response.status_code, 400)

        for body in (
            {"token": "short", "password": TEST_PASSWORD},
            {"token": "x" * 43, "password": "short"},
            {"token": "x" * 43, "password": TEST_PASSWORD, "tenant_id": "x"},
        ):
            with self.subTest(body=body):
                response = self.client.post(ACCEPT_URL, json=body)
                self.assertEqual(response.status_code, 422)

    def test_36_existing_user_invitation(self):
        # owner_b exists globally but is not a member of tenant A.
        invitation = self.invite_token(self.owner_b.email, "AGENT")
        token = invitation["invitation_token"]

        # Wrong password: rejected, invitation still usable.
        response = self.accept(token, password="WrongPassword1")
        self.assertEqual(response.status_code, 401)

        response = self.accept(token, first_name="Ignored")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["id"], str(self.owner_b.id))

        self.db.expire_all()
        self.assertEqual(
            self.db.query(User).filter(User.email == self.owner_b.email).count(), 1
        )
        # Existing profile is not overwritten.
        self.assertNotEqual(self.db.get(User, self.owner_b.id).first_name, "Ignored")

        memberships = {
            m.tenant_id: m.status
            for m in self.db.query(TenantMembership).filter_by(user_id=self.owner_b.id)
        }
        self.assertEqual(
            memberships, {self.tenant_a.id: "active", self.tenant_b.id: "active"}
        )

    def test_37_duplicate_membership_prevented(self):
        invitation = self.invite_token("late-member@example.com")

        # The user joins tenant A through another path before accepting.
        user = self.make_user("late")
        user.email = "late-member@example.com"
        self.add_member(user, self.tenant_a, "VIEWER")
        self.db.commit()

        response = self.accept(invitation["invitation_token"])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.db.query(TenantMembership).filter_by(
                user_id=user.id, tenant_id=self.tenant_a.id
            ).count(),
            1,
        )

    def test_removed_member_reactivated_by_invitation(self):
        self.delete_member(self.owner, self.viewer.id)
        invitation = self.invite_token(self.viewer.email, "AGENT")

        response = self.accept(invitation["invitation_token"])
        self.assertEqual(response.status_code, 200, response.text)

        member = self.client.get(
            f"{USERS_URL}/{self.viewer.id}",
            headers=self.auth(self.owner, self.tenant_a),
        ).json()
        self.assertEqual(member["membership_status"], "active")
        self.assertEqual(member["role"], "AGENT")


class SecurityTests(TeamTestCase):

    def test_38_to_40_no_secrets_in_responses(self):
        headers = self.auth(self.owner, self.tenant_a)
        invitation = self.invite_token("secrets@example.com")
        accepted = self.accept(invitation["invitation_token"], first_name="S")

        responses = [
            self.client.get(USERS_URL, headers=headers),
            self.client.get(f"{USERS_URL}/{self.agent.id}", headers=headers),
            self.patch_member(self.owner, self.agent.id, {"status": "active"}),
            self.client.get(INVITATIONS_URL, headers=headers),
            accepted,
        ]
        for response in responses:
            with self.subTest(url=str(response.url)):
                self.assertNotIn("password_hash", response.text)
                self.assertNotIn(TEST_PASSWORD, response.text)
                self.assertNotIn("token_hash", response.text)
                self.assertNotIn(invitation["invitation_token"], response.text)

        stored = self.db.get(TeamInvitation, uuid.UUID(invitation["id"]))
        self.assertNotIn(stored.token_hash, accepted.text)

    def test_41_tenant_id_query_cannot_change_scope(self):
        query = f"?tenant_id={self.tenant_b.id}"
        self.assertEqual(self.list_emails(self.owner, query), self.tenant_a_emails())

        response = self.client.get(
            f"{USERS_URL}/{self.member_b.id}{query}",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 404)

    def test_42_tenant_id_body_cannot_change_scope(self):
        headers = self.auth(self.owner, self.tenant_a)

        response = self.client.post(INVITE_URL, headers=headers, json={
            "email": "body-scope@example.com",
            "role_id": self.role_id("AGENT"),
            "tenant_id": str(self.tenant_b.id),
        })
        self.assertEqual(response.status_code, 422)

        response = self.patch_member(
            self.owner, self.agent.id,
            {"status": "active", "tenant_id": str(self.tenant_b.id)},
        )
        self.assertEqual(response.status_code, 422)

        self.assertEqual(
            self.db.query(TeamInvitation).filter_by(tenant_id=self.tenant_b.id).count(),
            0,
        )

    def test_cannot_invite_into_other_tenant(self):
        # Owner of A using a token claiming tenant B.
        response = self.invite(self.owner, "into-b@example.com", tenant=self.tenant_b)
        self.assertEqual(response.status_code, 403)


ROLES_URL = "/api/v1/roles"


class RolesEndpointTests(TeamTestCase):
    """GET /roles: assignable flags, RBAC, tenant scoping, no secrets."""

    def get_roles_response(self, actor, tenant=None):
        response = self.client.get(ROLES_URL, headers=bearer(self.token_for(actor, tenant or self.tenant_a)))
        self.assertEqual(response.status_code, 200, response.text)
        return {item["name"]: item for item in response.json()}

    def test_lists_all_active_roles_with_fields(self):
        roles_data = self.get_roles_response(self.owner)
        self.assertEqual(
            set(roles_data),
            {"OWNER", "ADMIN", "MANAGER", "AGENT", "VIEWER", "DEVELOPER"},
        )
        for item in roles_data.values():
            self.assertEqual(set(item), {"id", "name", "description", "assignable"})

    def test_owner_can_assign_every_role(self):
        roles_data = self.get_roles_response(self.owner)
        self.assertTrue(all(item["assignable"] for item in roles_data.values()))

    def test_non_owner_cannot_assign_owner(self):
        for actor in (self.admin, self.manager):
            with self.subTest(actor=actor.email):
                roles_data = self.get_roles_response(actor)
                self.assertFalse(roles_data["OWNER"]["assignable"])

    def test_manager_cannot_assign_above_itself(self):
        roles_data = self.get_roles_response(self.manager)
        self.assertTrue(roles_data["MANAGER"]["assignable"])
        self.assertTrue(roles_data["AGENT"]["assignable"])
        self.assertFalse(roles_data["ADMIN"]["assignable"])

    def test_read_only_roles_can_view_roles(self):
        # user:read is granted to every role; viewers can see role names.
        for actor in (self.viewer, self.developer, self.agent):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.client.get(
                    ROLES_URL, headers=bearer(self.token_for(actor, self.tenant_a)),
                ).status_code, 200)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(ROLES_URL).status_code, 401)

    def test_no_permission_names_or_secrets_leaked(self):
        response = self.client.get(ROLES_URL, headers=bearer(self.token_for(self.owner, self.tenant_a)))
        for needle in ("permission", "user:read", "token", "password", "hash"):
            self.assertNotIn(needle, response.text.lower())

from unittest.mock import patch
import smtplib
from app.core.config import settings

class EmailDeliveryTests(TeamTestCase):
    @patch("smtplib.SMTP")
    def test_successful_email_delivery(self, mock_smtp):
        mock_server = mock_smtp.return_value.__enter__.return_value
        
        # Enable SMTP for test
        original_host = settings.smtp_host
        settings.smtp_host = "smtp.example.com"
        
        try:
            response = self.invite(self.owner, "success@example.com", "AGENT")
            self.assertEqual(response.status_code, 201)
            mock_server.send_message.assert_called_once()
            
            # Check message details
            msg = mock_server.send_message.call_args[0][0]
            self.assertEqual(msg["To"], "success@example.com")
            self.assertIn("token=", msg.get_content())
        finally:
            settings.smtp_host = original_host

    def test_provider_configuration_missing(self):
        original_host = settings.smtp_host
        settings.smtp_host = ""
        
        try:
            # Should skip email delivery and succeed without error
            response = self.invite(self.owner, "no-smtp@example.com", "AGENT")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["email"], "no-smtp@example.com")
        finally:
            settings.smtp_host = original_host

    @patch("smtplib.SMTP")
    def test_provider_failure_revokes_invitation(self, mock_smtp):
        mock_server = mock_smtp.return_value.__enter__.return_value
        mock_server.send_message.side_effect = smtplib.SMTPException("Connection failed")
        
        original_host = settings.smtp_host
        settings.smtp_host = "smtp.example.com"
        
        try:
            response = self.invite(self.owner, "fail@example.com", "AGENT")
            # Should map EmailDeliveryError to 503
            self.assertEqual(response.status_code, 503)
            self.assertIn("Could not deliver the invitation email", response.json()["detail"])
            
            # Since it was revoked, we should be able to invite again
            mock_server.send_message.side_effect = None
            retry_response = self.invite(self.owner, "fail@example.com", "AGENT")
            self.assertEqual(retry_response.status_code, 201)
        finally:
            settings.smtp_host = original_host
