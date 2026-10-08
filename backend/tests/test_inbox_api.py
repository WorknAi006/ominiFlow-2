"""
API tests for contacts, conversations and messages: CRUD, filters,
pagination, RBAC, tenant isolation and query efficiency.
"""
import uuid
from datetime import timedelta

from sqlalchemy import event

from app.core.database import engine
from app.models import ConversationStatus, MessageDirection, TenantMembership
from tests.base import bearer
from tests.inbox_fixtures import BASE_TIME, InboxTestCase

CONTACTS = "/api/v1/contacts"
CONVERSATIONS = "/api/v1/conversations"
FORBIDDEN = {"detail": "You do not have permission to perform this action."}


# =========================
# CONTACTS
# =========================

class ContactApiTests(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.alice = cls.make_contact(cls.tenant_a, "+14155550101", first_name="Alice", last_name="Smith")
        cls.bob = cls.make_contact(cls.tenant_a, "+14155550102", display_name="Bob (VIP)")
        cls.carol = cls.make_contact(cls.tenant_a, None, email="carol@example.com", first_name="Carol")
        cls.b_contact = cls.make_contact(cls.tenant_b, "+14155550101", first_name="Alice B")

    def headers(self, actor=None):
        return self.auth(actor or self.owner, self.tenant_a)

    def test_create_normalizes_phone(self):
        response = self.client.post(CONTACTS, headers=self.headers(), json={
            "phone_number": " +44 (20) 7946-0958 ", "first_name": "Dave", "email": "Dave@Example.COM",
        })
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["normalized_phone_number"], "+442079460958")
        self.assertEqual(body["email"], "dave@example.com")
        self.assertEqual(body["name"], "Dave")
        self.assertFalse(body["is_blocked"])

    def test_create_email_only(self):
        response = self.client.post(CONTACTS, headers=self.headers(), json={"email": "e@example.com"})
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["normalized_phone_number"])

    def test_duplicate_phone_rejected_within_tenant_only(self):
        for phone in ("+14155550101", "0014155550101", "1 415 555 0101"):
            with self.subTest(phone=phone):
                response = self.client.post(CONTACTS, headers=self.headers(), json={"phone_number": phone})
                self.assertEqual(response.status_code, 409)
        # Tenant B already has the same customer; tenant A has its own.
        response = self.client.post(
            CONTACTS, headers=self.auth(self.owner_b, self.tenant_b), json={"phone_number": "+14155550102"},
        )
        self.assertEqual(response.status_code, 201)

    def test_create_validation(self):
        invalid = [
            {},
            {"first_name": "No identity"},
            {"phone_number": "12345"},
            {"phone_number": "not a phone"},
            {"email": "not-an-email"},
            {"phone_number": "+14155550199", "tenant_id": str(self.tenant_b.id)},
            {"phone_number": "+14155550199", "external_identifier": "x"},
            {"phone_number": "+14155550199", "is_blocked": True},
            {"phone_number": "+14155550199", "first_name": "x" * 101},
        ]
        for body in invalid:
            with self.subTest(body=body):
                self.assertEqual(self.client.post(CONTACTS, headers=self.headers(), json=body).status_code, 422)

    def test_get_list_search_and_pagination(self):
        response = self.client.get(f"{CONTACTS}/{self.alice.id}", headers=self.headers(self.viewer))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Alice Smith")

        listing = self.client.get(CONTACTS, headers=self.headers()).json()
        self.assertEqual(listing["total"], 3)

        def names(query):
            return {c["name"] for c in self.client.get(f"{CONTACTS}{query}", headers=self.headers()).json()["items"]}

        self.assertEqual(names("?search=smith"), {"Alice Smith"})
        self.assertEqual(names("?search=VIP"), {"Bob (VIP)"})
        self.assertEqual(names("?search=carol@"), {"Carol"})
        self.assertEqual(names("?search=%25"), set())
        self.assertEqual(names("?phone=%2B1%20415-555-0102"), {"Bob (VIP)"})
        self.assertEqual(names("?phone=0014155550101"), {"Alice Smith"})

        page_1 = self.client.get(f"{CONTACTS}?page=1&page_size=2", headers=self.headers()).json()
        page_2 = self.client.get(f"{CONTACTS}?page=2&page_size=2", headers=self.headers()).json()
        self.assertEqual((len(page_1["items"]), len(page_2["items"])), (2, 1))
        self.assertEqual(len({c["id"] for c in page_1["items"] + page_2["items"]}), 3)

        for query in ("?page=0", "?page_size=101", "?phone=abc"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"{CONTACTS}{query}", headers=self.headers()).status_code, 422)

    def test_update(self):
        response = self.client.patch(f"{CONTACTS}/{self.alice.id}", headers=self.headers(self.agent), json={
            "display_name": "Alice S.", "is_blocked": True, "phone_number": "+1 415 555 0177",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["name"], "Alice S.")
        self.assertTrue(body["is_blocked"])
        self.assertEqual(body["normalized_phone_number"], "+14155550177")

        url = f"{CONTACTS}/{self.bob.id}"
        self.assertEqual(
            self.client.patch(url, headers=self.headers(), json={"phone_number": "+14155550177"}).status_code, 409,
        )
        for body in ({}, {"phone_number": None}, {"is_blocked": None}, {"normalized_phone_number": "+1"},
                     {"external_identifier": "x"}, {"tenant_id": str(self.tenant_b.id)}, {"id": str(uuid.uuid4())}):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch(url, headers=self.headers(), json=body).status_code, 422)

        # Cannot remove the last identity.
        response = self.client.patch(f"{CONTACTS}/{self.carol.id}", headers=self.headers(), json={"email": None})
        self.assertEqual(response.status_code, 422)

    def test_rbac(self):
        body = {"phone_number": "+14155550150"}
        self.assertEqual(self.client.post(CONTACTS, headers=self.headers(self.viewer), json=body).json(), FORBIDDEN)
        self.assertEqual(self.client.post(CONTACTS, headers=self.headers(self.developer), json=body).status_code, 403)
        self.assertEqual(
            self.client.patch(f"{CONTACTS}/{self.bob.id}", headers=self.headers(self.viewer),
                              json={"first_name": "x"}).status_code,
            403,
        )
        self.assertEqual(self.client.post(CONTACTS, headers=self.headers(self.agent), json=body).status_code, 201)
        self.assertEqual(self.client.get(CONTACTS).status_code, 401)
        self.assertEqual(self.client.get(CONTACTS, headers=bearer("bad.jwt")).status_code, 401)

    def test_tenant_isolation(self):
        url = f"{CONTACTS}/{self.b_contact.id}"
        self.assertEqual(self.client.get(url, headers=self.headers()).status_code, 404)
        self.assertEqual(self.client.patch(url, headers=self.headers(), json={"first_name": "Hacked"}).status_code, 404)
        self.assertEqual(self.client.get(f"{CONTACTS}/not-a-uuid", headers=self.headers()).status_code, 422)

        listing = self.client.get(f"{CONTACTS}?search=Alice&tenant_id={self.tenant_b.id}", headers=self.headers()).json()
        self.assertEqual({c["id"] for c in listing["items"]}, {str(self.alice.id)})

        self.db.expire_all()
        self.assertEqual(self.db.get(type(self.b_contact), self.b_contact.id).first_name, "Alice B")


# =========================
# CONVERSATIONS
# =========================

class ConversationApiTests(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.alice = cls.make_contact(cls.tenant_a, "+14155550101", first_name="Alice")
        cls.bob = cls.make_contact(cls.tenant_a, "+14155550102", first_name="Bob")
        cls.carol = cls.make_contact(cls.tenant_a, "+14155550103", first_name="Carol")

        cls.conv_alice = cls.make_conversation(
            cls.tenant_a, cls.alice, cls.wa_a, unread_count=2,
            last_message_at=BASE_TIME + timedelta(hours=2), subject="Order #1",
        )
        cls.make_message(cls.conv_alice, "First question")
        cls.make_message(cls.conv_alice, "Hello world " * 30)

        cls.conv_bob = cls.make_conversation(
            cls.tenant_a, cls.bob, cls.wa_a, status=ConversationStatus.RESOLVED,
            last_message_at=BASE_TIME + timedelta(hours=1), assigned_user_id=cls.agent.id,
        )
        cls.make_message(cls.conv_bob, "Thanks!", MessageDirection.OUTBOUND)

        cls.conv_carol = cls.make_conversation(
            cls.tenant_a, cls.carol, cls.wa_a, status=ConversationStatus.PENDING,
        )

        b_contact = cls.make_contact(cls.tenant_b, "+14155550101", first_name="Alice B")
        cls.conv_b = cls.make_conversation(cls.tenant_b, b_contact, cls.wa_b, unread_count=1)
        cls.make_message(cls.conv_b, "Tenant B secret")

    def headers(self, actor=None):
        return self.auth(actor or self.owner, self.tenant_a)

    def ids(self, query=""):
        response = self.client.get(f"{CONVERSATIONS}{query}", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        return [item["id"] for item in response.json()["items"]]

    def test_list_summary_and_default_sort(self):
        response = self.client.get(CONVERSATIONS, headers=self.headers(self.viewer))
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(
            [item["id"] for item in body["items"]],
            [str(self.conv_alice.id), str(self.conv_bob.id), str(self.conv_carol.id)],
        )

        alice = body["items"][0]
        self.assertEqual(alice["contact"]["name"], "Alice")
        self.assertEqual(alice["contact"]["phone_number"], "+14155550101")
        self.assertEqual(alice["channel"], {"id": str(self.wa_a.id), "name": "WA A", "channel_type": "whatsapp"})
        self.assertEqual(alice["unread_count"], 2)
        self.assertEqual(alice["subject"], "Order #1")
        self.assertIsNone(alice["assigned_user"])
        preview = alice["last_message"]["text"]
        self.assertTrue(preview.startswith("Hello world"))
        self.assertEqual(len(preview), 200)

        bob = body["items"][1]
        self.assertEqual(bob["assigned_user"]["id"], str(self.agent.id))
        self.assertNotIn("email", bob["assigned_user"])
        self.assertEqual(bob["last_message"]["direction"], "outbound")
        self.assertIsNone(body["items"][2]["last_message"])
        self.assertNotIn("Tenant B secret", response.text)

    def test_filters_and_pagination(self):
        self.assertEqual(self.ids("?status=open"), [str(self.conv_alice.id)])
        self.assertEqual(self.ids("?status=pending"), [str(self.conv_carol.id)])
        self.assertEqual(self.ids(f"?assigned_user_id={self.agent.id}"), [str(self.conv_bob.id)])
        self.assertEqual(len(self.ids("?unassigned=true")), 2)
        self.assertEqual(self.ids("?unread=true"), [str(self.conv_alice.id)])
        self.assertEqual(len(self.ids("?unread=false")), 2)
        self.assertEqual(len(self.ids(f"?channel_id={self.wa_a.id}")), 3)
        self.assertEqual(self.ids(f"?channel_id={self.wa_b.id}"), [])
        self.assertEqual(self.ids("?search=carol"), [str(self.conv_carol.id)])
        self.assertEqual(self.ids("?search=0102"), [str(self.conv_bob.id)])
        self.assertEqual(self.ids("?search=order %231"), [str(self.conv_alice.id)])

        page_2 = self.client.get(f"{CONVERSATIONS}?page=2&page_size=2", headers=self.headers()).json()
        self.assertEqual((page_2["total"], [i["id"] for i in page_2["items"]]), (3, [str(self.conv_carol.id)]))

        for query in ("?status=archived", "?page=0", "?page_size=500", "?channel_id=nope", "?unread=maybe"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"{CONVERSATIONS}{query}", headers=self.headers()).status_code, 422)

    def test_get_and_update(self):
        url = f"{CONVERSATIONS}/{self.conv_alice.id}"
        self.assertEqual(self.client.get(url, headers=self.headers(self.viewer)).json()["id"], str(self.conv_alice.id))

        response = self.client.patch(url, headers=self.headers(self.agent), json={"subject": " Refund "})
        self.assertEqual(response.json()["subject"], "Refund")

        for body in ({}, {"status": "closed"}, {"unread_count": 0}, {"tenant_id": str(self.tenant_b.id)},
                     {"assigned_user_id": str(self.agent.id)}):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch(url, headers=self.headers(), json=body).status_code, 422)

    def test_mark_read(self):
        response = self.client.post(f"{CONVERSATIONS}/{self.conv_alice.id}/read", headers=self.headers(self.agent))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 0)
        self.assertEqual(
            self.client.post(f"{CONVERSATIONS}/{self.conv_alice.id}/read", headers=self.headers(self.viewer)).status_code,
            403,
        )

    def test_assignment(self):
        url = f"{CONVERSATIONS}/{self.conv_alice.id}/assign"

        response = self.client.post(url, headers=self.headers(self.manager), json={"assigned_user_id": str(self.agent.id)})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["assigned_user"]["id"], str(self.agent.id))

        response = self.client.post(url, headers=self.headers(), json={"assigned_user_id": None})
        self.assertIsNone(response.json()["assigned_user"])

        # Not a member of this tenant / suspended member / unknown user.
        suspended = self.db.query(TenantMembership).filter_by(user_id=self.developer.id).one()
        suspended.status = "suspended"
        self.db.commit()
        for assignee in (self.owner_b.id, self.developer.id, uuid.uuid4()):
            with self.subTest(assignee=str(assignee)):
                response = self.client.post(url, headers=self.headers(), json={"assigned_user_id": str(assignee)})
                self.assertEqual(response.status_code, 422)

        self.assertEqual(self.client.post(url, headers=self.headers(), json={}).status_code, 422)

        # Agents cannot assign (no conversation:assign).
        for actor in (self.agent, self.viewer):
            with self.subTest(actor=actor.email):
                response = self.client.post(url, headers=self.headers(actor),
                                            json={"assigned_user_id": str(actor.id)})
                self.assertEqual(response.status_code, 403)

    def test_status_changes(self):
        url = f"{CONVERSATIONS}/{self.conv_alice.id}/status"
        for new_status in ("pending", "resolved", "closed", "open"):
            with self.subTest(status=new_status):
                response = self.client.post(url, headers=self.headers(self.agent), json={"status": new_status})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], new_status)

        self.assertEqual(self.client.post(url, headers=self.headers(), json={"status": "archived"}).status_code, 422)
        self.assertEqual(self.client.post(url, headers=self.headers(self.viewer), json={"status": "open"}).status_code, 403)

    def test_reopen_conflicts_with_active_thread(self):
        # Bob's resolved conversation; a new active one exists for Bob.
        self.make_conversation(self.tenant_a, self.bob, self.wa_a)
        self.db.commit()
        response = self.client.post(f"{CONVERSATIONS}/{self.conv_bob.id}/status",
                                    headers=self.headers(), json={"status": "open"})
        self.assertEqual(response.status_code, 409)

    def test_tenant_isolation(self):
        base = f"{CONVERSATIONS}/{self.conv_b.id}"
        calls = {
            "get": self.client.get(base, headers=self.headers()),
            "patch": self.client.patch(base, headers=self.headers(), json={"subject": "x"}),
            "read": self.client.post(f"{base}/read", headers=self.headers()),
            "assign": self.client.post(f"{base}/assign", headers=self.headers(), json={"assigned_user_id": None}),
            "status": self.client.post(f"{base}/status", headers=self.headers(), json={"status": "closed"}),
            "messages": self.client.get(f"{base}/messages", headers=self.headers()),
        }
        for name, response in calls.items():
            with self.subTest(call=name):
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("Tenant B secret", response.text)

        conversation = self.reload(type(self.conv_b), self.conv_b.id)
        self.assertEqual((conversation.status, conversation.unread_count, conversation.subject), ("open", 1, None))

        self.assertNotIn(str(self.conv_b.id), self.ids(f"?channel_id={self.wa_b.id}&tenant_id={self.tenant_b.id}"))

    def test_list_has_no_n_plus_one(self):
        def statements_for_list():
            count = 0

            def counter(*_args):
                nonlocal count
                count += 1

            event.listen(engine, "before_cursor_execute", counter)
            try:
                self.assertEqual(self.client.get(CONVERSATIONS, headers=self.headers()).status_code, 200)
            finally:
                event.remove(engine, "before_cursor_execute", counter)
            return count

        small = statements_for_list()
        for index in range(10):
            contact = self.make_contact(self.tenant_a, f"+1415555{index:04d}")
            conversation = self.make_conversation(self.tenant_a, contact, self.wa_a, assigned_user_id=self.agent.id)
            self.make_message(conversation, f"msg {index}")
        self.db.commit()
        large = statements_for_list()

        self.assertEqual(small, large)


# =========================
# MESSAGES
# =========================

class MessageApiTests(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        contact = cls.make_contact(cls.tenant_a, "+14155550101")
        cls.conversation = cls.make_conversation(cls.tenant_a, contact, cls.wa_a)
        cls.messages = [cls.make_message(cls.conversation, f"message {i}") for i in range(5)]

        b_contact = cls.make_contact(cls.tenant_b, "+14155550101")
        cls.conversation_b = cls.make_conversation(cls.tenant_b, b_contact, cls.wa_b)
        cls.message_b = cls.make_message(cls.conversation_b, "Tenant B private")

    def test_list_newest_first_with_pagination(self):
        url = f"{CONVERSATIONS}/{self.conversation.id}/messages"
        headers = self.auth(self.viewer, self.tenant_a)

        page_1 = self.client.get(f"{url}?page_size=2", headers=headers).json()
        self.assertEqual(page_1["total"], 5)
        self.assertEqual([m["text"] for m in page_1["items"]], ["message 4", "message 3"])

        page_3 = self.client.get(f"{url}?page=3&page_size=2", headers=headers).json()
        self.assertEqual([m["text"] for m in page_3["items"]], ["message 0"])

        self.assertEqual(self.client.get(f"{url}?page_size=101", headers=headers).status_code, 422)

    def test_get_message(self):
        response = self.client.get(f"/api/v1/messages/{self.messages[0].id}", headers=self.auth(self.developer, self.tenant_a))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["text"], "message 0")
        for secret_field in ("access_token", "_encrypted", "tenant_id"):
            self.assertNotIn(secret_field, response.text)

    def test_tenant_isolation(self):
        headers = self.auth(self.owner, self.tenant_a)
        response = self.client.get(f"/api/v1/messages/{self.message_b.id}", headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Tenant B private", response.text)
        self.assertEqual(
            self.client.get(f"{CONVERSATIONS}/{self.conversation_b.id}/messages", headers=headers).status_code, 404,
        )
        self.assertEqual(self.client.get("/api/v1/messages/not-a-uuid", headers=headers).status_code, 422)
        self.assertEqual(self.client.get(f"/api/v1/messages/{uuid.uuid4()}", headers=headers).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/messages/{self.messages[0].id}").status_code, 401)


class OutboundIdempotencyApiTests(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        contact = cls.make_contact(cls.tenant_a, "+14155550101", first_name="Send Test")
        cls.conversation = cls.make_conversation(cls.tenant_a, contact, cls.wa_a)
        cls.db.commit()

    def test_duplicate_send_returns_existing_message_and_conflict_is_rejected(self):
        key = str(uuid.uuid4())
        headers = {**self.auth(self.owner, self.tenant_a), "Idempotency-Key": key}
        url = f"{CONVERSATIONS}/{self.conversation.id}/messages"
        first = self.client.post(url, headers=headers, json={"type": "text", "text": "hello"})
        duplicate = self.client.post(url, headers=headers, json={"type": "text", "text": "hello"})
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(duplicate.status_code, 201, duplicate.text)
        self.assertEqual(first.json()["id"], duplicate.json()["id"])
        self.assertEqual(len(self.send_api.requests), 1)

        conflict = self.client.post(url, headers=headers, json={"type": "text", "text": "different"})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(len(self.send_api.requests), 1)

    def test_ambiguous_provider_failure_is_not_retried_for_same_key(self):
        key = str(uuid.uuid4())
        headers = {**self.auth(self.owner, self.tenant_a), "Idempotency-Key": key}
        url = f"{CONVERSATIONS}/{self.conversation.id}/messages"
        self.send_api.network_down = True
        first = self.client.post(url, headers=headers, json={"type": "text", "text": "hello"})
        retry = self.client.post(url, headers=headers, json={"type": "text", "text": "hello"})
        self.assertEqual(first.status_code, 502)
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(retry.json()["status"], "pending")
        self.assertEqual(len(self.send_api.requests), 1)

    def test_idempotency_keys_are_scoped_to_tenant(self):
        contact_b = self.make_contact(self.tenant_b, "+14155550102", first_name="Tenant B")
        conversation_b = self.make_conversation(self.tenant_b, contact_b, self.wa_b)
        self.db.commit()
        key = str(uuid.uuid4())
        response_a = self.client.post(
            f"{CONVERSATIONS}/{self.conversation.id}/messages",
            headers={**self.auth(self.owner, self.tenant_a), "Idempotency-Key": key},
            json={"type": "text", "text": "hello"},
        )
        response_b = self.client.post(
            f"{CONVERSATIONS}/{conversation_b.id}/messages",
            headers={**self.auth(self.owner_b, self.tenant_b), "Idempotency-Key": key},
            json={"type": "text", "text": "hello"},
        )
        self.assertEqual(response_a.status_code, 201, response_a.text)
        self.assertEqual(response_b.status_code, 201, response_b.text)
        self.assertNotEqual(response_a.json()["id"], response_b.json()["id"])
        self.assertEqual(len(self.send_api.requests), 2)
