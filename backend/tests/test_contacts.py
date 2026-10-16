"""
Tests for Contacts Management: CRUD, server-side search and pagination,
duplicate handling, tenant isolation, RBAC, input validation, the
block/unblock deactivate pattern, and the contact -> conversations filter.

Runs against the real PostgreSQL database inside a rolled-back transaction
(see tests/base.py). Reuses the Unified Inbox fixtures (two tenants, every
role, channels) from tests/inbox_fixtures.py.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy.exc import IntegrityError

from app.models import ConversationStatus
from app.services.contact_service import _commit
from tests.inbox_fixtures import InboxTestCase

CONTACTS_URL = "/api/v1/contacts"
CONVERSATIONS_URL = "/api/v1/conversations"

RESPONSE_FIELDS = {
    "id", "name", "phone_number", "normalized_phone_number", "email",
    "first_name", "last_name", "display_name", "profile_name",
    "avatar_url", "is_blocked", "created_at", "updated_at",
    "identities", "tags", "field_values",
}

FORBIDDEN = {"detail": "You do not have permission to perform this action."}


class ContactsTestCase(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.c_alice = cls.make_contact(
            cls.tenant_a, phone="15550000001",
            first_name="Alice", last_name="Anders", email="alice@example.com",
        )
        cls.c_bob = cls.make_contact(
            cls.tenant_a, phone="15550000002",
            display_name="Bob Builder", email="bob@build.example",
        )
        cls.c_email_only = cls.make_contact(
            cls.tenant_a, phone=None, email="carol@example.com", first_name="Carol",
        )
        cls.c_other = cls.make_contact(
            cls.tenant_b, phone="15559999999", first_name="Tenant B Person",
        )

    # ---------- helpers ----------

    def list(self, actor, query="", tenant=None):
        return self.client.get(
            f"{CONTACTS_URL}{query}", headers=self.auth(actor, tenant or self.tenant_a)
        )

    def names(self, actor, query="", tenant=None):
        response = self.list(actor, query, tenant)
        self.assertEqual(response.status_code, 200, response.text)
        return {item["name"] for item in response.json()["items"]}

    def create(self, actor, body, tenant=None):
        return self.client.post(
            CONTACTS_URL, headers=self.auth(actor, tenant or self.tenant_a), json=body
        )

    def patch(self, actor, contact, body, tenant=None):
        cid = contact if isinstance(contact, (str, uuid.UUID)) else contact.id
        return self.client.patch(
            f"{CONTACTS_URL}/{cid}", headers=self.auth(actor, tenant or self.tenant_a), json=body
        )


class ListAndSearchTests(ContactsTestCase):

    def test_read_roles_list_only_own_tenant(self):
        expected = {"Alice Anders", "Bob Builder", "Carol"}
        for actor in (self.owner, self.admin, self.manager, self.agent, self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                got = self.names(actor)
                self.assertEqual(got, expected)
                self.assertNotIn("Tenant B Person", got)

    def test_response_shape_and_total(self):
        body = self.list(self.owner).json()
        self.assertEqual(body["total"], 3)
        for item in body["items"]:
            self.assertEqual(set(item), RESPONSE_FIELDS)

    def test_search_by_name_phone_email(self):
        self.assertEqual(self.names(self.owner, "?search=alice"), {"Alice Anders"})
        self.assertEqual(self.names(self.owner, "?search=ALICE"), {"Alice Anders"})
        self.assertEqual(self.names(self.owner, "?search=builder"), {"Bob Builder"})
        self.assertEqual(self.names(self.owner, "?search=carol@example.com"), {"Carol"})
        self.assertEqual(self.names(self.owner, "?search=5550000001"), {"Alice Anders"})
        self.assertEqual(self.names(self.owner, "?search=nomatch"), set())

    def test_search_does_not_cross_tenant(self):
        self.assertEqual(self.names(self.owner, "?search=Tenant B Person"), set())

    def test_search_like_wildcards_are_escaped(self):
        self.assertEqual(self.names(self.owner, "?search=%25"), set())
        self.assertEqual(self.names(self.owner, "?search=_"), set())

    def test_phone_filter_exact(self):
        self.assertEqual(self.names(self.owner, "?phone=15550000002"), {"Bob Builder"})
        self.assertEqual(self.names(self.owner, "?phone=%2B15550000002"), {"Bob Builder"})

    def test_pagination(self):
        headers = self.auth(self.owner, self.tenant_a)
        p1 = self.client.get(f"{CONTACTS_URL}?page=1&page_size=2", headers=headers).json()
        p2 = self.client.get(f"{CONTACTS_URL}?page=2&page_size=2", headers=headers).json()
        self.assertEqual((p1["total"], len(p1["items"])), (3, 2))
        self.assertEqual((p2["total"], len(p2["items"])), (3, 1))
        ids = [i["id"] for i in p1["items"] + p2["items"]]
        self.assertEqual(len(set(ids)), 3)
        for q in ("?page=0", "?page_size=0", "?page_size=101"):
            with self.subTest(q=q):
                self.assertEqual(self.client.get(f"{CONTACTS_URL}{q}", headers=headers).status_code, 422)

    def test_get_contact_and_404(self):
        response = self.client.get(
            f"{CONTACTS_URL}/{self.c_alice.id}", headers=self.auth(self.viewer, self.tenant_a)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), RESPONSE_FIELDS)
        self.assertEqual(
            self.client.get(f"{CONTACTS_URL}/{uuid.uuid4()}", headers=self.auth(self.owner, self.tenant_a)).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"{CONTACTS_URL}/not-a-uuid", headers=self.auth(self.owner, self.tenant_a)).status_code,
            422,
        )


class CreateTests(ContactsTestCase):

    def test_create_roles_allowed(self):
        for index, actor in enumerate((self.owner, self.admin, self.manager, self.agent)):
            with self.subTest(actor=actor.email):
                response = self.create(actor, {
                    "phone_number": f"1555123400{index}", "first_name": f"New{index}",
                })
                self.assertEqual(response.status_code, 201, response.text)
                body = response.json()
                self.assertFalse(body["is_blocked"])
                self.assertIsNotNone(body["normalized_phone_number"])

    def test_create_email_only(self):
        response = self.create(self.owner, {"email": "New.Person@Example.com"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["email"], "new.person@example.com")

    def test_create_read_only_roles_denied(self):
        for actor in (self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                response = self.create(actor, {"phone_number": "15551110000"})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), FORBIDDEN)

    def test_invalid_input_rejected(self):
        invalid = [
            {},
            {"first_name": "No Identity"},
            {"phone_number": "not-a-phone"},
            {"email": "not-an-email"},
            {"phone_number": "15551110000", "tenant_id": str(self.tenant_b.id)},
            {"phone_number": "15551110000", "is_blocked": True},
            {"phone_number": "15551110000", "first_name": ""},
        ]
        for body in invalid:
            with self.subTest(body=body):
                self.assertEqual(self.create(self.owner, body).status_code, 422)

    def test_duplicate_phone_in_tenant_conflicts(self):
        response = self.create(self.owner, {"phone_number": "15550000001"})
        self.assertEqual(response.status_code, 409)

    def test_same_phone_different_tenant_allowed(self):
        # Tenant B already owns 15559999999; tenant A may hold the same number.
        response = self.create(self.owner, {"phone_number": "15559999999"})
        self.assertEqual(response.status_code, 201, response.text)

    def test_unrelated_integrity_error_is_not_reported_as_duplicate_phone(self):
        db = Mock()
        db.commit.side_effect = IntegrityError(
            "INSERT INTO contacts ...",
            {},
            SimpleNamespace(
                diag=SimpleNamespace(constraint_name="some_other_constraint")
            ),
        )

        with self.assertRaises(IntegrityError):
            _commit(db)

        db.rollback.assert_called_once_with()


class UpdateTests(ContactsTestCase):

    def test_update_roles_allowed(self):
        response = self.patch(self.agent, self.c_alice, {"first_name": "Alicia", "display_name": "Alicia A"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "Alicia A")

    def test_update_read_only_roles_denied(self):
        for actor in (self.viewer, self.developer):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.patch(actor, self.c_alice, {"first_name": "No"}).status_code, 403)

    def test_update_email_and_clear(self):
        response = self.patch(self.owner, self.c_alice, {"email": None})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["email"])

    def test_update_duplicate_phone_conflicts(self):
        response = self.patch(self.owner, self.c_alice, {"phone_number": "15550000002"})
        self.assertEqual(response.status_code, 409)

    def test_update_cannot_remove_last_identity(self):
        # c_email_only has no phone; clearing the email leaves no identity.
        response = self.patch(self.owner, self.c_email_only, {"email": None})
        self.assertEqual(response.status_code, 422)

    def test_block_and_unblock(self):
        blocked = self.patch(self.owner, self.c_bob, {"is_blocked": True})
        self.assertEqual(blocked.status_code, 200, blocked.text)
        self.assertTrue(blocked.json()["is_blocked"])
        unblocked = self.patch(self.owner, self.c_bob, {"is_blocked": False})
        self.assertTrue(unblocked.status_code == 200 and unblocked.json()["is_blocked"] is False)

    def test_empty_update_rejected(self):
        self.assertEqual(self.patch(self.owner, self.c_alice, {}).status_code, 422)


class TenantIsolationTests(ContactsTestCase):

    def test_cannot_read_other_tenant_contact(self):
        not_found = {"detail": "Contact not found."}
        headers = self.auth(self.owner, self.tenant_a)
        target = f"{CONTACTS_URL}/{self.c_other.id}"
        self.assertEqual(self.client.get(target, headers=headers).status_code, 404)
        self.assertEqual(self.client.get(target, headers=headers).json(), not_found)

    def test_cannot_update_other_tenant_contact(self):
        response = self.patch(self.owner, self.c_other, {"first_name": "Hacked"})
        self.assertEqual(response.status_code, 404)
        self.db.expire_all()

    def test_tenant_id_in_body_rejected(self):
        response = self.create(self.owner, {
            "phone_number": "15551112222", "tenant_id": str(self.tenant_b.id),
        })
        self.assertEqual(response.status_code, 422)

    def test_tenant_id_in_query_ignored(self):
        got = self.names(self.owner, f"?tenant_id={self.tenant_b.id}")
        self.assertNotIn("Tenant B Person", got)


class ContactConversationTests(ContactsTestCase):

    def test_filter_conversations_by_contact(self):
        conv = self.make_conversation(self.tenant_a, self.c_alice, self.wa_a, status=ConversationStatus.OPEN)
        # A conversation for a different contact must not appear.
        self.make_conversation(self.tenant_a, self.c_bob, self.wa_a, status=ConversationStatus.OPEN)
        self.db.commit()

        response = self.client.get(
            f"{CONVERSATIONS_URL}?contact_id={self.c_alice.id}",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["items"]
        self.assertEqual([item["id"] for item in items], [str(conv.id)])
        self.assertEqual(items[0]["contact"]["id"], str(self.c_alice.id))

    def test_contact_filter_is_tenant_scoped(self):
        # Tenant A cannot surface tenant B's contact conversations.
        self.make_conversation(self.tenant_b, self.c_other, self.wa_b, status=ConversationStatus.OPEN)
        self.db.commit()
        response = self.client.get(
            f"{CONVERSATIONS_URL}?contact_id={self.c_other.id}",
            headers=self.auth(self.owner, self.tenant_a),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
