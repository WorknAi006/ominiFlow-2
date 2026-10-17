"""
Keywords: CRUD, tenant isolation, flow ownership, the four match types, and
keyword → flow triggering on inbound messages (idempotent, deterministic).
"""
from app.integrations.registry import get_provider
from app.models import ChannelType, Conversation, Message, KeywordTrigger, MessageDirection
from app.services import flow_runner, inbound_event_service, keyword_trigger_service
from tests.inbox_fixtures import BASE_TIME, CUSTOMER, InboxTestCase


def raw_text(body, message_id="wamid.K1", sender=CUSTOMER, name="Jane Customer"):
    return {
        "payload": {
            "message": {"id": message_id, "from": sender, "type": "text", "text": {"body": body}},
            "contact": {"wa_id": sender, "profile": {"name": name}},
        },
        "external_message_id": message_id,
        "external_sender_id": sender,
        "external_event_id": f"message:{message_id}",
        "occurred_at": BASE_TIME,
    }


class KeywordCrudTests(InboxTestCase):
    def head(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def make_flow(self, name="Welcome Flow", tenant=None, actor=None):
        r = self.client.post("/api/v1/flows", headers=self.head(actor, tenant), json={"name": name, "channels": ["whatsapp"]})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def test_crud_and_flow_name(self):
        flow_id = self.make_flow("Pricing Flow")
        created = self.client.post("/api/v1/keywords", headers=self.head(), json={
            "keyword_text": "price", "match_type": "contains", "flow_id": flow_id, "is_active": True,
        })
        self.assertEqual(created.status_code, 201, created.text)
        kw = created.json()
        self.assertEqual(kw["flow_id"], flow_id)
        self.assertEqual(kw["flow_name"], "Pricing Flow")

        listed = self.client.get("/api/v1/keywords", headers=self.head()).json()
        self.assertTrue(any(k["id"] == kw["id"] and k["flow_name"] == "Pricing Flow" for k in listed))

        upd = self.client.patch(f"/api/v1/keywords/{kw['id']}", headers=self.head(), json={"match_type": "ends_with"})
        self.assertEqual(upd.status_code, 200, upd.text)
        self.assertEqual(upd.json()["match_type"], "ends_with")

        deleted = self.client.delete(f"/api/v1/keywords/{kw['id']}", headers=self.head())
        self.assertEqual(deleted.status_code, 204)
        gone = self.client.get(f"/api/v1/keywords/{kw['id']}", headers=self.head())
        self.assertEqual(gone.status_code, 404)

    def test_ends_with_match_type_accepted(self):
        r = self.client.post("/api/v1/keywords", headers=self.head(), json={"keyword_text": "bye", "match_type": "ends_with"})
        self.assertEqual(r.status_code, 201, r.text)

    def test_rejects_cross_tenant_flow(self):
        other_flow = self.make_flow("Tenant B Flow", tenant=self.tenant_b, actor=self.owner_b)
        r = self.client.post("/api/v1/keywords", headers=self.head(), json={
            "keyword_text": "hi", "match_type": "exact", "flow_id": other_flow,
        })
        self.assertEqual(r.status_code, 400, r.text)

    def test_tenant_isolation_list(self):
        self.client.post("/api/v1/keywords", headers=self.head(), json={"keyword_text": "only-a", "match_type": "exact"})
        b_list = self.client.get("/api/v1/keywords", headers=self.head(self.owner_b, self.tenant_b)).json()
        self.assertFalse(any(k["keyword_text"] == "only-a" for k in b_list))

    def test_duplicate_rejected(self):
        self.client.post("/api/v1/keywords", headers=self.head(), json={"keyword_text": "dup", "match_type": "exact"})
        again = self.client.post("/api/v1/keywords", headers=self.head(), json={"keyword_text": "dup", "match_type": "exact"})
        self.assertEqual(again.status_code, 400)


class MatchLogicTests(InboxTestCase):
    def test_four_match_types(self):
        m = keyword_trigger_service.text_matches
        # exact
        self.assertTrue(m("Hello", "hello", "exact"))
        self.assertFalse(m("hello there", "hello", "exact"))
        # contains
        self.assertTrue(m("I want the PRICE now", "price", "contains"))
        self.assertFalse(m("cost", "price", "contains"))
        # starts_with
        self.assertTrue(m("Start here", "start", "starts_with"))
        self.assertFalse(m("please start", "start", "starts_with"))
        # ends_with
        self.assertTrue(m("say BYE", "bye", "ends_with"))
        self.assertFalse(m("bye now", "bye", "ends_with"))
        # whitespace normalization
        self.assertTrue(m("  hello   world  ", "hello world", "exact"))


class KeywordTriggerTests(InboxTestCase):
    def head(self):
        return self.auth(self.owner, self.tenant_a)

    def make_flow(self, name="Trigger Flow"):
        r = self.client.post("/api/v1/flows", headers=self.head(), json={"name": name, "channels": ["whatsapp"]})
        return r.json()["id"]

    def make_keyword(self, text, match_type="contains", flow_id=None, is_active=True, reply_text=None):
        r = self.client.post("/api/v1/keywords", headers=self.head(), json={
            "keyword_text": text, "match_type": match_type, "flow_id": flow_id,
            "is_active": is_active, "reply_text": reply_text,
        })
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def ingest(self, body, message_id="wamid.K1"):
        provider = get_provider(ChannelType.WHATSAPP)
        event = provider.normalize_inbound_message(self.wa_a, raw_text(body, message_id=message_id))
        inbound_event_service.process_inbound_event(self.db, event)
        self.db.commit()
        self.db.expire_all()

    def triggers(self):
        return self.db.query(KeywordTrigger).filter_by(tenant_id=self.tenant_a.id).all()

    def test_active_keyword_triggers_selected_flow(self):
        flow_id = self.make_flow("Pricing")
        kw = self.make_keyword("price", flow_id=flow_id)
        self.ingest("What is the price please", message_id="wamid.T1")
        rows = self.triggers()
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0].keyword_id), kw["id"])
        self.assertEqual(str(rows[0].flow_id), flow_id)
        self.assertEqual(rows[0].action, "run_flow")
        self.assertEqual(rows[0].status, "matched")

    def test_non_matching_message_no_trigger(self):
        self.make_keyword("price", flow_id=self.make_flow())
        self.ingest("hello there", message_id="wamid.T2")
        self.assertEqual(len(self.triggers()), 0)

    def test_inactive_keyword_does_not_trigger(self):
        self.make_keyword("price", flow_id=self.make_flow(), is_active=False)
        self.ingest("the price is high", message_id="wamid.T3")
        self.assertEqual(len(self.triggers()), 0)

    def test_idempotent_on_replay(self):
        self.make_keyword("price", flow_id=self.make_flow())
        self.ingest("price now", message_id="wamid.T4")
        self.ingest("price now", message_id="wamid.T4")  # same provider message id
        self.assertEqual(len(self.triggers()), 1)

    def test_overlapping_matches_single_deterministic_trigger(self):
        f1 = self.make_flow("Flow One")
        self.make_keyword("hello", match_type="contains", flow_id=f1)
        self.make_keyword("hel", match_type="starts_with", flow_id=self.make_flow("Flow Two"))
        self.ingest("hello world", message_id="wamid.T5")
        rows = self.triggers()
        self.assertEqual(len(rows), 1)  # exactly one flow fired

    def test_fallback_text_only_records_send_text(self):
        self.make_keyword("help", flow_id=None, reply_text="How can I help?")
        self.ingest("i need help", message_id="wamid.T6")
        rows = self.triggers()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].action, "send_text")

    def test_outbound_message_does_not_trigger(self):
        self.make_keyword("price", flow_id=self.make_flow())
        contact = self.make_contact(self.tenant_a)
        convo = self.make_conversation(self.tenant_a, contact, self.wa_a)
        outbound = self.make_message(convo, text="price list attached", direction=MessageDirection.OUTBOUND)
        self.db.commit()
        result = keyword_trigger_service.handle_inbound(
            self.db, tenant_id=self.tenant_a.id, channel_type="whatsapp",
            conversation=convo, contact=contact, message=outbound,
        )
        self.assertIsNone(result)
        self.assertEqual(len(self.triggers()), 0)

    # ---- live delivery through the connected provider (flow_runner) ----

    def set_flow_text(self, flow_id, text):
        r = self.client.patch(f"/api/v1/flows/{flow_id}", headers=self.head(), json={
            "nodes": [{"id": "start", "type": "message", "position": {"x": 1, "y": 1},
                       "data": {"isStart": True, "channel": "whatsapp", "messageType": "text", "message": text}}],
            "edges": [],
        })
        self.assertEqual(r.status_code, 200, r.text)

    def test_delivery_sends_flow_start_message_through_provider(self):
        flow_id = self.make_flow("Greeter")
        self.set_flow_text(flow_id, "Hi from the flow!")
        self.make_keyword("hi", match_type="exact", flow_id=flow_id)
        self.ingest("hi", message_id="wamid.D1")
        self.assertEqual(self.triggers()[0].status, "matched")

        counts = flow_runner.process_pending(self.db, limit=10)
        self.db.expire_all()
        self.assertEqual(counts["delivered"], 1)
        self.assertEqual(self.triggers()[0].status, "delivered")
        # The reply actually went out through the WhatsApp provider.
        self.assertEqual(len(self.send_api.requests), 1)
        outbound = self.db.query(Message).filter_by(
            tenant_id=self.tenant_a.id, direction=MessageDirection.OUTBOUND,
        ).all()
        self.assertTrue(any(m.text == "Hi from the flow!" for m in outbound))

    def test_delivery_falls_back_to_reply_text(self):
        flow_id = self.make_flow("NoEntryText")  # start node message is empty
        self.make_keyword("help", match_type="contains", flow_id=flow_id, reply_text="How can I help?")
        self.ingest("i need help", message_id="wamid.D2")

        flow_runner.process_pending(self.db, limit=10)
        self.db.expire_all()
        self.assertEqual(self.triggers()[0].status, "delivered")
        self.assertEqual(len(self.send_api.requests), 1)
        outbound = self.db.query(Message).filter_by(
            tenant_id=self.tenant_a.id, direction=MessageDirection.OUTBOUND,
        ).all()
        self.assertTrue(any(m.text == "How can I help?" for m in outbound))

    def test_delivery_is_idempotent(self):
        flow_id = self.make_flow("Once")
        self.set_flow_text(flow_id, "Only once")
        self.make_keyword("once", match_type="exact", flow_id=flow_id)
        self.ingest("once", message_id="wamid.D3")
        flow_runner.process_pending(self.db, limit=10)
        # A second pass finds nothing still 'matched' → no second provider send.
        counts2 = flow_runner.process_pending(self.db, limit=10)
        self.assertEqual(counts2["delivered"], 0)
        self.assertEqual(len(self.send_api.requests), 1)
