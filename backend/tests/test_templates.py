"""
Tests for WhatsApp template sync, template APIs and outbound template
messages.
"""
import logging
import uuid
from copy import deepcopy

import httpx

from app.integrations.meta.graph_client import build_graph_client
from app.models import Message, MessageTemplate
from app.services.whatsapp_event_processor import process_event
from tests.base import bearer
from tests.inbox_fixtures import (
    APP_SECRET,
    CUSTOMER,
    CUSTOMER_E164,
    TOKEN_A,
    TOKEN_B,
    WABA_A,
    WABA_B,
    InboxTestCase,
)
from tests.meta_fakes import FakeMeta


def meta_template(name, *, language="en_US", status="APPROVED", components=None, **extra):
    return {
        "id": f"{abs(hash((name, language))) % 10**15}",
        "name": name,
        "language": language,
        "status": status,
        "category": "UTILITY",
        "components": components if components is not None else [{"type": "BODY", "text": "Hello!"}],
        **extra,
    }


ORDER_UPDATE = meta_template("order_update", components=[
    {"type": "HEADER", "format": "TEXT", "text": "Order {{1}}"},
    {"type": "BODY", "text": "Hi {{1}}, your order {{2}} has shipped."},
    {"type": "FOOTER", "text": "Acme Inc"},
    {"type": "BUTTONS", "buttons": [
        {"type": "URL", "text": "Track", "url": "https://shop.example/track/{{1}}"},
        {"type": "QUICK_REPLY", "text": "Stop"},
    ]},
])
WELCOME = meta_template("welcome", language="en")
PROMO_NAMED = meta_template(
    "promo_named", language="en", parameter_format="NAMED",
    components=[{"type": "BODY", "text": "Hi {{first_name}}, use code {{code}}."}],
)
INVOICE = meta_template("invoice", language="en", components=[
    {"type": "HEADER", "format": "DOCUMENT"},
    {"type": "BODY", "text": "Your invoice {{1}} is attached."},
])
PENDING = meta_template("pending_tpl", language="en", status="PENDING")
REJECTED = meta_template("rejected_tpl", language="en", status="REJECTED", rejected_reason="INVALID_FORMAT")
INVALID_ITEMS = [
    {"name": "Bad Name!", "language": "en", "status": "APPROVED", "components": []},
    {"name": "no_components", "language": "en", "status": "APPROVED"},
    {"name": "bad_language", "language": "english-us", "status": "APPROVED", "components": []},
    {"name": "no_status", "language": "en", "components": []},
]

TEMPLATES_A = [ORDER_UPDATE, WELCOME, PROMO_NAMED, INVOICE, PENDING, REJECTED, *INVALID_ITEMS]


class TemplateTestCase(InboxTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.meta = FakeMeta(APP_SECRET, tokens={TOKEN_A: {WABA_A}, TOKEN_B: {WABA_B}})
        self.meta.templates = {
            WABA_A: deepcopy(TEMPLATES_A),
            WABA_B: [meta_template("order_update", components=[{"type": "BODY", "text": "B only"}])],
        }
        transport = httpx.MockTransport(self.meta.handler)
        self.provider.client_factory = lambda: build_graph_client(transport=transport)

    def sync(self, channel=None, actor=None, tenant=None):
        channel = channel or self.wa_a
        return self.client.post(
            f"/api/v1/channels/{channel.id}/templates/sync",
            headers=self.auth(actor or self.owner, tenant or self.tenant_a),
        )

    def list_templates(self, channel=None, query="", actor=None, tenant=None):
        channel = channel or self.wa_a
        return self.client.get(
            f"/api/v1/channels/{channel.id}/templates{query}",
            headers=self.auth(actor or self.viewer, tenant or self.tenant_a),
        )

    def stored(self, channel=None):
        self.db.expire_all()
        return {
            (t.name, t.language): t
            for t in self.db.query(MessageTemplate).filter_by(channel_connection_id=(channel or self.wa_a).id)
        }


# =========================
# SYNC
# =========================

class TemplateSyncTests(TemplateTestCase):

    def test_sync_creates_templates(self):
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"received": 10, "created": 6, "updated": 0, "deactivated": 0, "skipped": 4})

        stored = self.stored()
        self.assertEqual(set(stored), {
            ("order_update", "en_US"), ("welcome", "en"), ("promo_named", "en"),
            ("invoice", "en"), ("pending_tpl", "en"), ("rejected_tpl", "en"),
        })
        order = stored[("order_update", "en_US")]
        self.assertEqual((order.status, order.category, order.tenant_id), ("approved", "utility", self.tenant_a.id))
        self.assertEqual(order.external_template_id, ORDER_UPDATE["id"])
        self.assertEqual(order.components, ORDER_UPDATE["components"])
        self.assertIsNotNone(order.last_synced_at)
        self.assertEqual(stored[("promo_named", "en")].template_metadata, {"parameter_format": "NAMED"})
        self.assertEqual(stored[("rejected_tpl", "en")].template_metadata, {"rejected_reason": "INVALID_FORMAT"})

        # Paging cursors were followed; the token stayed out of URLs.
        template_requests = [r for r in self.meta.requests if r.url.path.endswith("/message_templates")]
        self.assertEqual([r.url.params.get("after") for r in template_requests], [None, "3", "6", "9"])
        for request in template_requests:
            self.assertEqual(request.headers["authorization"], f"Bearer {TOKEN_A}")
            self.assertNotIn(TOKEN_A, str(request.url))
        self.assertNotIn(TOKEN_A, response.text)

    def test_resync_is_idempotent_and_tracks_changes(self):
        self.sync()
        first_ids = {key: t.id for key, t in self.stored().items()}

        response = self.sync()
        self.assertEqual(response.json(), {"received": 10, "created": 0, "updated": 6, "deactivated": 0, "skipped": 4})
        self.assertEqual({key: t.id for key, t in self.stored().items()}, first_ids)
        self.assertEqual(self.db.query(MessageTemplate).filter_by(channel_connection_id=self.wa_a.id).count(), 6)

        # Status change + removal at Meta.
        templates = self.meta.templates[WABA_A]
        next(t for t in templates if t["name"] == "pending_tpl")["status"] = "APPROVED"
        self.meta.templates[WABA_A] = [t for t in templates if t["name"] != "welcome"]

        response = self.sync()
        self.assertEqual(response.json()["deactivated"], 1)
        stored = self.stored()
        self.assertEqual(stored[("pending_tpl", "en")].status, "approved")
        self.assertFalse(stored[("welcome", "en")].is_active)

        names = {t["name"] for t in self.list_templates().json()["items"]}
        self.assertNotIn("welcome", names)
        names = {t["name"] for t in self.list_templates(query="?include_inactive=true").json()["items"]}
        self.assertIn("welcome", names)

        # Reappears -> reactivated, same row.
        self.meta.templates[WABA_A].append(deepcopy(WELCOME))
        self.sync()
        self.assertTrue(self.stored()[("welcome", "en")].is_active)
        self.assertEqual(self.stored()[("welcome", "en")].id, first_ids[("welcome", "en")])

    def test_channel_and_tenant_isolation(self):
        self.sync()
        self.sync(self.wa_b, self.owner_b, self.tenant_b)

        a_order = self.stored()[("order_update", "en_US")]
        b_order = self.stored(self.wa_b)[("order_update", "en_US")]
        self.assertNotEqual(a_order.id, b_order.id)
        self.assertEqual(b_order.components, [{"type": "BODY", "text": "B only"}])

        # Tenant A cannot list/sync tenant B's channel or read its template.
        self.assertEqual(self.list_templates(self.wa_b).status_code, 404)
        self.assertEqual(self.sync(self.wa_b).status_code, 404)
        response = self.client.get(f"/api/v1/templates/{b_order.id}", headers=self.auth(self.owner, self.tenant_a))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("B only", response.text)

        # Listing only returns this channel's templates.
        items = self.list_templates(query="?search=order").json()["items"]
        self.assertEqual([t["id"] for t in items], [str(a_order.id)])

    def test_rbac(self):
        for actor in (self.viewer, self.agent, self.developer):
            with self.subTest(actor=actor.email):
                self.assertEqual(self.sync(actor=actor).status_code, 403)
        self.assertEqual(self.sync(actor=self.manager).status_code, 200)
        self.assertEqual(self.list_templates(actor=self.developer).status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/v1/channels/{self.wa_a.id}/templates", headers=bearer("bad.jwt")).status_code, 401,
        )

    def test_meta_failures_are_sanitized(self):
        self.sync()
        before = {key: (t.status, t.is_active) for key, t in self.stored().items()}

        self.meta.graph_error = (400, "Invalid OAuth token {token}", 190)
        response = self.sync()
        self.assertEqual(response.status_code, 502)
        self.assertIn("Template sync failed", response.text)
        self.assertIn("[redacted]", response.text)
        self.assertNotIn(TOKEN_A, response.text)

        self.meta.graph_error = None
        self.meta.network_down = True
        self.assertEqual(self.sync().status_code, 502)

        self.assertEqual({key: (t.status, t.is_active) for key, t in self.stored().items()}, before)

    def test_channel_requirements(self):
        self.assertEqual(self.sync(self.ig_a).status_code, 422)
        self.client.post(f"/api/v1/channels/{self.wa_a.id}/disconnect", headers=self.auth(self.owner, self.tenant_a))
        self.assertEqual(self.sync().status_code, 409)
        self.assertEqual(self.client.post(
            f"/api/v1/channels/{uuid.uuid4()}/templates/sync", headers=self.auth(self.owner, self.tenant_a),
        ).status_code, 404)

    def test_get_and_filter_templates(self):
        self.sync()
        order = self.stored()[("order_update", "en_US")]
        response = self.client.get(f"/api/v1/templates/{order.id}", headers=self.auth(self.viewer, self.tenant_a))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["is_usable"])
        self.assertEqual(body["components"], ORDER_UPDATE["components"])
        for field in ("access_token", "tenant_id", "_encrypted"):
            self.assertNotIn(field, response.text)

        statuses = {t["name"]: t["is_usable"] for t in self.list_templates().json()["items"]}
        self.assertFalse(statuses["pending_tpl"])
        self.assertFalse(statuses["rejected_tpl"])
        self.assertEqual([t["name"] for t in self.list_templates(query="?status=PENDING").json()["items"]], ["pending_tpl"])

        headers = self.auth(self.viewer, self.tenant_a)
        self.assertEqual(self.client.get("/api/v1/templates/not-a-uuid", headers=headers).status_code, 422)
        self.assertEqual(self.client.get(f"/api/v1/templates/{uuid.uuid4()}", headers=headers).status_code, 404)
        self.assertEqual(self.list_templates(query="?status=bad%20status").status_code, 422)


# =========================
# OUTBOUND TEMPLATE MESSAGES
# =========================

class TemplateSendTests(TemplateTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.sync()
        self.contact = self.make_contact(self.tenant_a, CUSTOMER_E164)
        self.conversation = self.make_conversation(self.tenant_a, self.contact, self.wa_a)
        contact_b = self.make_contact(self.tenant_b, CUSTOMER_E164)
        self.conversation_b = self.make_conversation(self.tenant_b, contact_b, self.wa_b)
        self.db.commit()
        self.meta.requests.clear()

    def send(self, body, conversation=None, actor=None):
        return self.client.post(
            f"/api/v1/conversations/{(conversation or self.conversation).id}/messages",
            headers={
                **self.auth(actor or self.agent, self.tenant_a),
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json=body,
        )

    def order_update(self, **overrides):
        body = {
            "type": "template",
            "template_name": "order_update",
            "language": "en_US",
            "components": [
                {"type": "header", "parameters": [{"type": "text", "text": "#123"}]},
                {"type": "body", "parameters": [{"type": "text", "text": "Jane"}, {"type": "text", "text": "#123"}]},
                {"type": "button", "sub_type": "url", "index": 0, "parameters": [{"type": "text", "text": "ABC123"}]},
            ],
        }
        body.update(overrides)
        return body

    def test_positional_template(self):
        response = self.send(self.order_update())
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["message_type"], "template")
        self.assertEqual(body["status"], "sent")
        self.assertEqual(body["text"], "Hi Jane, your order #123 has shipped.")
        self.assertEqual(body["metadata"]["template"]["name"], "order_update")
        self.assertTrue(body["external_message_id"].startswith("wamid.T"))

        [sent] = self.meta.sent
        self.assertEqual(sent["type"], "template")
        self.assertEqual(sent["to"], CUSTOMER)
        self.assertEqual(sent["template"]["name"], "order_update")
        self.assertEqual(sent["template"]["language"], {"code": "en_US"})
        self.assertEqual(sent["template"]["components"], [
            {"type": "header", "parameters": [{"type": "text", "text": "#123"}]},
            {"type": "body", "parameters": [{"type": "text", "text": "Jane"}, {"type": "text", "text": "#123"}]},
            {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": "ABC123"}]},
        ])

    def test_template_without_parameters(self):
        response = self.send({"type": "template", "template_name": "welcome", "language": "en"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["text"], "Hello!")
        self.assertNotIn("components", self.meta.sent[0]["template"])

    def test_named_parameters_and_media_header(self):
        response = self.send({
            "type": "template", "template_name": "promo_named", "language": "en",
            "components": [{"type": "body", "parameters": [
                {"type": "text", "parameter_name": "code", "text": "SAVE10"},
                {"type": "text", "parameter_name": "first_name", "text": "Jane"},
            ]}],
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["text"], "Hi Jane, use code SAVE10.")
        self.assertEqual(self.meta.sent[0]["template"]["components"][0]["parameters"][0]["parameter_name"], "code")

        response = self.send({
            "type": "template", "template_name": "invoice", "language": "en",
            "components": [
                {"type": "header", "parameters": [
                    {"type": "document", "link": "https://files.example.com/inv-9.pdf", "filename": "inv-9.pdf"},
                ]},
                {"type": "body", "parameters": [{"type": "text", "text": "INV-9"}]},
            ],
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.meta.sent[1]["template"]["components"][0], {
            "type": "header",
            "parameters": [{"type": "document", "document": {"link": "https://files.example.com/inv-9.pdf", "filename": "inv-9.pdf"}}],
        })

    def test_invalid_templates_rejected(self):
        wa_b_template = {"type": "template", "template_name": "order_update", "language": "en_US"}
        cases = {
            "unknown": {"type": "template", "template_name": "nope", "language": "en"},
            "wrong language": self.order_update(language="fr"),
            "pending": {"type": "template", "template_name": "pending_tpl", "language": "en"},
            "rejected": {"type": "template", "template_name": "rejected_tpl", "language": "en"},
            "missing params": {"type": "template", "template_name": "order_update", "language": "en_US"},
            "too few body params": self.order_update(components=[
                {"type": "header", "parameters": [{"type": "text", "text": "#1"}]},
                {"type": "body", "parameters": [{"type": "text", "text": "Jane"}]},
                {"type": "button", "sub_type": "url", "index": 0, "parameters": [{"type": "text", "text": "x"}]},
            ]),
            "unexpected component": {"type": "template", "template_name": "welcome", "language": "en",
                                     "components": [{"type": "header", "parameters": [{"type": "text", "text": "x"}]}]},
            "missing media header": {"type": "template", "template_name": "invoice", "language": "en",
                                     "components": [{"type": "body", "parameters": [{"type": "text", "text": "x"}]}]},
            "newline in param": self.order_update(components=[
                {"type": "header", "parameters": [{"type": "text", "text": "#1"}]},
                {"type": "body", "parameters": [{"type": "text", "text": "Jane\nX"}, {"type": "text", "text": "#1"}]},
                {"type": "button", "sub_type": "url", "index": 0, "parameters": [{"type": "text", "text": "x"}]},
            ]),
            "unknown named param": {"type": "template", "template_name": "promo_named", "language": "en",
                                    "components": [{"type": "body", "parameters": [
                                        {"type": "text", "parameter_name": "first_name", "text": "a"},
                                        {"type": "text", "parameter_name": "evil", "text": "b"}]}]},
            "http media link": {"type": "template", "template_name": "invoice", "language": "en",
                                "components": [{"type": "header", "parameters": [
                                    {"type": "document", "link": "http://files.example.com/a.pdf"}]},
                                    {"type": "body", "parameters": [{"type": "text", "text": "x"}]}]},
            "bad name": {"type": "template", "template_name": "Bad-Name", "language": "en"},
            "extra field": {**wa_b_template, "tenant_id": str(self.tenant_b.id)},
            "reply_to on template": {**wa_b_template, "reply_to_message_id": str(uuid.uuid4())},
            "bad component type": self.order_update(components=[{"type": "footer", "parameters": []}]),
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                response = self.send(body)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn(TOKEN_A, response.text)

        self.assertEqual(self.meta.sent, [])
        self.assertEqual(self.db.query(Message).filter_by(direction="outbound").count(), 0)

    def test_template_of_other_channel_not_usable(self):
        # Template exists only on a second channel of the same tenant.
        other = self.make_channel(self.tenant_a, "WA A2", "610000000000099", WABA_A, TOKEN_A)
        self.db.add(MessageTemplate(
            tenant_id=self.tenant_a.id, channel_connection_id=other.id, name="other_only",
            language="en", status="approved", components=[{"type": "BODY", "text": "x"}],
        ))
        self.db.commit()
        response = self.send({"type": "template", "template_name": "other_only", "language": "en"})
        self.assertEqual(response.status_code, 422)

    def test_wrong_tenant_and_disconnected_channel(self):
        response = self.send(self.order_update(), conversation=self.conversation_b)
        self.assertEqual(response.status_code, 404)

        self.client.post(f"/api/v1/channels/{self.wa_a.id}/disconnect", headers=self.auth(self.owner, self.tenant_a))
        self.assertEqual(self.send(self.order_update()).status_code, 409)
        self.assertEqual(self.meta.sent, [])

    def test_provider_rejection(self):
        self.meta.send_error = (400, "(#132001) Template name does not exist in the translation. {token}", 132001)
        response = self.send(self.order_update())
        self.assertEqual(response.status_code, 502)
        self.assertNotIn(TOKEN_A, response.text)
        [message] = self.db.query(Message).filter_by(direction="outbound").all()
        self.assertEqual((message.status, message.error_code, message.message_type), ("failed", "132001", "template"))
        self.assertIn("[redacted]", message.error_message)

    def test_text_still_works_and_rbac(self):
        response = self.send({"type": "text", "text": "Plain text still works"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message_type"], "text")
        self.assertEqual(self.meta.sent[0]["type"], "text")

        self.assertEqual(self.send(self.order_update(), actor=self.viewer).status_code, 403)

    def test_status_updates_and_no_duplicate_messages(self):
        external_id = self.send(self.order_update()).json()["external_message_id"]

        def process(event):
            session = self.make_session()
            try:
                return process_event(session, event.id)
            finally:
                session.close()

        self.assertEqual(process(self.status_event(self.wa_a, external_id, "delivered")), "processed")
        self.assertEqual(process(self.status_event(self.wa_a, external_id, "read")), "processed")
        # A provider echo / duplicate with the same wamid creates nothing new.
        echo = self.message_event(self.wa_a, self.text_message(external_id))
        self.assertEqual(process(echo), "processed")

        self.db.expire_all()
        [message] = self.db.query(Message).filter_by(external_message_id=external_id).all()
        self.assertEqual((message.status, message.message_type), ("read", "template"))
        self.assertIsNotNone(message.delivered_at)

    def test_credentials_never_logged(self):
        handler = logging.Handler(level=logging.DEBUG)
        captured: list[str] = []
        handler.emit = lambda record: captured.append(handler.format(record) + (record.exc_text or ""))
        root = logging.getLogger()
        previous = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            self.send(self.order_update())
            self.meta.send_error = (400, "bad {token}", 100)
            self.send(self.order_update())
            self.sync()
        finally:
            root.removeHandler(handler)
            root.setLevel(previous)
        self.assertNotIn(TOKEN_A, "\n".join(captured))
        self.assertNotIn(APP_SECRET, "\n".join(captured))


# =========================
# TENANT-WIDE LIST (GET /templates)
# =========================

ALL_TEMPLATES_URL = "/api/v1/templates"


class ListAllTemplatesTests(TemplateTestCase):
    """GET /templates: tenant-wide listing, filters, isolation, RBAC."""

    def setUp(self) -> None:
        super().setUp()
        self.sync()                                   # tenant A -> wa_a
        self.sync(self.wa_b, self.owner_b, self.tenant_b)  # tenant B -> wa_b

    def get(self, query="", actor=None, tenant=None):
        return self.client.get(
            f"{ALL_TEMPLATES_URL}{query}",
            headers=self.auth(actor or self.viewer, tenant or self.tenant_a),
        )

    def names(self, query="", actor=None, tenant=None):
        response = self.get(query, actor, tenant)
        self.assertEqual(response.status_code, 200, response.text)
        return {item["name"] for item in response.json()["items"]}

    def test_lists_all_active_tenant_templates(self):
        response = self.get()
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["total"], 6)
        self.assertEqual(self.names(), {
            "order_update", "welcome", "promo_named", "invoice", "pending_tpl", "rejected_tpl",
        })

    def test_channel_filter(self):
        self.assertEqual(len(self.get(f"?channel_id={self.wa_a.id}").json()["items"]), 6)
        # A tenant-A channel with no templates returns an empty list.
        self.assertEqual(self.get(f"?channel_id={self.ig_a.id}").json()["items"], [])

    def test_status_filter(self):
        self.assertEqual(self.names("?status=approved"), {"order_update", "welcome", "promo_named", "invoice"})
        self.assertEqual(self.names("?status=pending"), {"pending_tpl"})
        self.assertEqual(self.names("?status=rejected"), {"rejected_tpl"})

    def test_category_filter(self):
        self.assertEqual(len(self.get("?category=utility").json()["items"]), 6)
        self.assertEqual(self.get("?category=marketing").json()["items"], [])

    def test_language_filter(self):
        self.assertEqual(self.names("?language=en_US"), {"order_update"})
        self.assertEqual(
            self.names("?language=en"),
            {"welcome", "promo_named", "invoice", "pending_tpl", "rejected_tpl"},
        )

    def test_search_by_name(self):
        self.assertEqual(self.names("?search=order"), {"order_update"})
        self.assertEqual(self.names("?search=NOMATCH"), set())

    def test_pagination(self):
        page1 = self.get("?page=1&page_size=4").json()
        page2 = self.get("?page=2&page_size=4").json()
        self.assertEqual((page1["total"], len(page1["items"])), (6, 4))
        self.assertEqual((page2["total"], len(page2["items"])), (6, 2))
        ids = [i["id"] for i in page1["items"] + page2["items"]]
        self.assertEqual(len(set(ids)), 6)
        for q in ("?page=0", "?page_size=0", "?page_size=101", "?status=bad!", "?language=english-us"):
            with self.subTest(q=q):
                self.assertEqual(self.get(q).status_code, 422)

    def test_tenant_isolation(self):
        # Tenant A never sees tenant B's templates, even filtering by B's channel.
        self.assertNotIn("B only", self.get().text)
        self.assertEqual(self.get(f"?channel_id={self.wa_b.id}").json()["items"], [])
        # Tenant B sees only its own.
        b_names = self.names(actor=self.owner_b, tenant=self.tenant_b)
        self.assertEqual(b_names, {"order_update"})

    def test_rbac_and_no_secrets(self):
        self.assertEqual(self.client.get(ALL_TEMPLATES_URL, headers=bearer("bad.jwt")).status_code, 401)
        response = self.get()
        self.assertNotIn(TOKEN_A, response.text)
        self.assertNotIn(TOKEN_B, response.text)
        self.assertNotIn("access_token", response.text)


class AiTemplateGenerateTests(TemplateTestCase):
    def test_ai_generate_returns_drafts_and_charges_credits(self):
        from unittest.mock import patch
        fake = {
            "drafts": [{
                "name": "diwali_sale", "category": "MARKETING", "language": "en_US",
                "header_type": "text", "header_text": "Big Diwali Sale",
                "body_text": "Hi {{1}}, get {{2}} off!", "footer_text": "Reply STOP to opt out",
                "buttons": ["Shop now"],
            }],
            "tokens_in": 300, "tokens_out": 150, "model": "gpt-4o-mini",
        }
        with patch("app.services.ai_template_service.generate_templates", return_value=fake):
            res = self.client.post(
                "/api/v1/templates/ai-generate",
                headers=self.auth(self.owner, self.tenant_a),
                json={"prompt": "diwali sale announcement", "count": 5},
            )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["name"], "diwali_sale")
        self.assertEqual(data["credits_used"], 0.45)   # 450 tokens -> 0.45 credits
        self.assertEqual(data["balance"], round(500.0 - 0.45, 2))

    def test_ai_generate_not_configured(self):
        from unittest.mock import patch
        with patch("app.services.ai_template_service.generate_templates", return_value=None):
            res = self.client.post(
                "/api/v1/templates/ai-generate",
                headers=self.auth(self.owner, self.tenant_a),
                json={"prompt": "something"},
            )
        self.assertEqual(res.status_code, 503, res.text)

    def test_ai_generate_provider_error_surfaces_message(self):
        from unittest.mock import patch
        from app.services.ai_template_service import AiProviderError
        with patch(
            "app.services.ai_template_service.generate_templates",
            side_effect=AiProviderError("You have no credits remaining."),
        ):
            res = self.client.post(
                "/api/v1/templates/ai-generate",
                headers=self.auth(self.owner, self.tenant_a),
                json={"prompt": "diwali offer"},
            )
        self.assertEqual(res.status_code, 502, res.text)
        self.assertIn("no credits remaining", res.json()["detail"])
