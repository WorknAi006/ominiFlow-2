"""
Stateful flow engine: a keyword starts a flow that walks multiple nodes,
branches on a button reply, captures user input into a variable, evaluates a
condition, and resumes after a delay — all delivered through the provider.
"""
from datetime import datetime, timedelta, timezone

from app.integrations.registry import get_provider
from app.models import ChannelType, FlowSession, Message, MessageDirection
from app.services import flow_engine, flow_runner, inbound_event_service
from tests.inbox_fixtures import BASE_TIME, CUSTOMER, InboxTestCase


def raw_text(body, message_id, sender=CUSTOMER):
    return {
        "payload": {
            "message": {"id": message_id, "from": sender, "type": "text", "text": {"body": body}},
            "contact": {"wa_id": sender, "profile": {"name": "Jane"}},
        },
        "external_message_id": message_id,
        "external_sender_id": sender,
        "external_event_id": f"message:{message_id}",
        "occurred_at": BASE_TIME,
    }


class FlowEngineTests(InboxTestCase):
    def head(self):
        return self.auth(self.owner, self.tenant_a)

    def make_flow_graph(self, nodes, edges, name="Graph"):
        created = self.client.post("/api/v1/flows", headers=self.head(), json={"name": name, "channels": ["whatsapp"]})
        self.assertEqual(created.status_code, 201, created.text)
        fid = created.json()["id"]
        up = self.client.patch(f"/api/v1/flows/{fid}", headers=self.head(), json={"nodes": nodes, "edges": edges})
        self.assertEqual(up.status_code, 200, up.text)
        return fid

    def make_keyword(self, text, flow_id, match_type="exact"):
        r = self.client.post("/api/v1/keywords", headers=self.head(), json={
            "keyword_text": text, "match_type": match_type, "flow_id": flow_id, "is_active": True,
        })
        self.assertEqual(r.status_code, 201, r.text)

    def ingest(self, body, mid):
        provider = get_provider(ChannelType.WHATSAPP)
        event = provider.normalize_inbound_message(self.wa_a, raw_text(body, mid))
        inbound_event_service.process_inbound_event(self.db, event)
        self.db.commit()
        self.db.expire_all()

    def pump(self):
        flow_runner.process_pending(self.db, 50)
        flow_engine.resume_pending_replies(self.db, 50)
        flow_engine.resume_due_delays(self.db, 50)
        self.db.expire_all()

    def sent_texts(self):
        return [
            m.text for m in self.db.query(Message)
            .filter_by(tenant_id=self.tenant_a.id, direction=MessageDirection.OUTBOUND)
            .order_by(Message.created_at.asc()).all()
        ]

    def session(self):
        return self.db.query(FlowSession).filter_by(tenant_id=self.tenant_a.id).one()

    def sent_payloads(self):
        import json
        out = []
        for r in self.send_api.requests:
            if r.url.path.rstrip("/").endswith("/messages"):
                try:
                    out.append(json.loads(r.content))
                except ValueError:
                    pass
        return out

    def ingest_interactive(self, reply_id, title, mid, sender=CUSTOMER):
        provider = get_provider(ChannelType.WHATSAPP)
        raw = {
            "payload": {
                "message": {
                    "id": mid, "from": sender, "type": "interactive",
                    "interactive": {"type": "button_reply", "button_reply": {"id": reply_id, "title": title}},
                },
                "contact": {"wa_id": sender, "profile": {"name": "Jane"}},
            },
            "external_message_id": mid, "external_sender_id": sender,
            "external_event_id": f"message:{mid}", "occurred_at": BASE_TIME,
        }
        event = provider.normalize_inbound_message(self.wa_a, raw)
        inbound_event_service.process_inbound_event(self.db, event)
        self.db.commit()
        self.db.expire_all()

    # ---- button branch ----
    def test_button_branch(self):
        nodes = [
            {"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {"isStart": True, "messageType": "text", "message": "Welcome"}},
            {"id": "menu", "type": "message", "position": {"x": 1, "y": 0}, "data": {"messageType": "button", "message": "Pick:", "buttons": [{"id": "a", "title": "Sales"}, {"id": "b", "title": "Support"}]}},
            {"id": "sales", "type": "message", "position": {"x": 2, "y": 0}, "data": {"messageType": "text", "message": "Sales team here"}},
            {"id": "support", "type": "message", "position": {"x": 2, "y": 1}, "data": {"messageType": "text", "message": "Support team here"}},
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "menu", "sourceHandle": "continue"},
            {"id": "e2", "source": "menu", "target": "sales", "sourceHandle": "btn:a"},
            {"id": "e3", "source": "menu", "target": "support", "sourceHandle": "btn:b"},
        ]
        self.make_keyword("menu", self.make_flow_graph(nodes, edges, "Menu"))

        self.ingest("menu", "wamid.F1")
        self.pump()
        texts = self.sent_texts()
        self.assertIn("Welcome", texts)
        # The button node now sends a real interactive message; its body is
        # stored as the message text and it has tappable reply buttons.
        self.assertIn("Pick:", texts)
        menu = self.db.query(Message).filter_by(
            tenant_id=self.tenant_a.id, direction=MessageDirection.OUTBOUND, text="Pick:",
        ).one()
        self.assertEqual(str(menu.message_type), "interactive")
        self.assertEqual(self.session().status, "waiting")

        self.ingest("1", "wamid.F2")  # choose Sales
        self.pump()
        texts = self.sent_texts()
        self.assertIn("Sales team here", texts)
        self.assertNotIn("Support team here", texts)
        self.assertEqual(self.session().status, "completed")

    # ---- interactive button: header + footer + reply/url buttons ----
    def test_button_interactive_header_footer_and_url(self):
        nodes = [
            {"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {
                "isStart": True, "messageType": "button", "message": "Choose",
                "header": {"type": "text", "text": "Welcome!"}, "footer": "Tap below",
                "buttons": [
                    {"id": "a", "title": "Yes", "kind": "reply"},
                    {"id": "w", "title": "Website", "kind": "url", "url": "https://example.com"},
                ],
            }},
            {"id": "done", "type": "message", "position": {"x": 1, "y": 0}, "data": {"messageType": "text", "message": "Thanks"}},
        ]
        edges = [{"id": "e1", "source": "start", "target": "done", "sourceHandle": "btn:a"}]
        self.make_keyword("hi", self.make_flow_graph(nodes, edges, "BtnFlow"))

        self.ingest("hi", "wamid.B1")
        self.pump()
        interactive = [p for p in self.sent_payloads() if p.get("type") == "interactive"]
        self.assertEqual(len(interactive), 1)
        body = interactive[0]["interactive"]
        self.assertEqual(body["type"], "button")
        self.assertEqual(body["header"], {"type": "text", "text": "Welcome!"})
        self.assertEqual(body["footer"]["text"], "Tap below")
        self.assertIn("https://example.com", body["body"]["text"])  # url appended
        self.assertEqual(body["action"]["buttons"][0]["reply"]["id"], "a")
        self.assertEqual(self.session().status, "waiting")

        # Tapping the "Yes" reply button branches to done.
        self.ingest_interactive("a", "Yes", "wamid.B2")
        self.pump()
        self.assertIn("Thanks", self.sent_texts())
        self.assertEqual(self.session().status, "completed")

    # ---- global fallback routing ----
    def test_global_fallback_flow(self):
        nodes = [{"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {
            "isStart": True, "messageType": "text", "message": "Fallback hello",
        }}]
        fid = self.make_flow_graph(nodes, [], "Fallback")
        r = self.client.put(
            "/api/v1/routing-config", headers=self.head(),
            json={"fallback_action": "flow", "fallback_flow_id": fid},
        )
        self.assertEqual(r.status_code, 200, r.text)

        # A message that matches no keyword routes into the fallback flow.
        self.ingest("literally anything xyz", "wamid.GF1")
        self.pump()
        self.assertIn("Fallback hello", self.sent_texts())

    def test_global_fallback_ai_reply(self):
        from unittest.mock import patch
        from app.models import CreditUsage, TenantAiCredit
        from app.services import payment_service

        # Give the tenant a known balance.
        payment_service.get_or_create_balance(self.db, self.tenant_a.id)
        self.db.commit()

        r = self.client.put(
            "/api/v1/routing-config", headers=self.head(),
            json={"fallback_action": "ai"},
        )
        self.assertEqual(r.status_code, 200, r.text)

        fake = {"text": "Thanks for reaching out! How can I help?", "tokens_in": 800, "tokens_out": 200, "model": "gpt-4o-mini"}
        with patch("app.services.ai_reply_service.generate_reply", return_value=fake):
            self.ingest("hi there, random question", "wamid.AI1")
            self.pump()

        self.assertIn("Thanks for reaching out! How can I help?", self.sent_texts())
        usage = self.db.query(CreditUsage).filter_by(tenant_id=self.tenant_a.id).all()
        self.assertEqual(len(usage), 1)
        self.assertEqual(float(usage[0].credits), 1.0)  # 1000 tokens -> 1.0 credit
        balance = self.db.query(TenantAiCredit).filter_by(tenant_id=self.tenant_a.id).one().balance
        self.assertEqual(float(balance), 499.0)  # 500 default - 1.0

    def test_no_fallback_when_unconfigured(self):
        self.ingest("some random text", "wamid.GF2")
        self.pump()
        self.assertEqual(self.sent_texts(), [])

    # ---- text header + footer compose into the body ----
    def test_text_header_footer_compose(self):
        nodes = [{"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {
            "isStart": True, "messageType": "text", "message": "Body here",
            "header": {"type": "text", "text": "Hi there"}, "footer": "Reply STOP to opt out",
        }}]
        self.make_keyword("hdr", self.make_flow_graph(nodes, [], "HdrFlow"))
        self.ingest("hdr", "wamid.H1")
        self.pump()
        msg = next((t for t in self.sent_texts() if "Body here" in t), "")
        self.assertIn("*Hi there*", msg)
        self.assertIn("Reply STOP to opt out", msg)

    # ---- media node sends a real media message ----
    def test_media_node_sends_media(self):
        up = self.client.post(
            "/api/v1/flows/upload", headers=self.head(),
            files={"file": ("clip.mp4", b"\x00\x01\x02fakevideo", "video/mp4")},
        )
        self.assertEqual(up.status_code, 200, up.text)
        nodes = [{"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {
            "isStart": True, "messageType": "video", "message": "Watch this",
            "mediaUrl": up.json()["url"], "mediaName": "clip.mp4",
        }}]
        self.make_keyword("vid", self.make_flow_graph(nodes, [], "VidFlow"))

        self.ingest("vid", "wamid.V1")
        self.pump()
        media = [p for p in self.sent_payloads() if p.get("type") == "video"]
        self.assertEqual(len(media), 1)
        self.assertIn("id", media[0]["video"])
        self.assertEqual(media[0]["video"].get("caption"), "Watch this")
        self.assertEqual(self.session().status, "completed")

    # ---- get user data + variable interpolation ----
    def test_get_user_data_and_variable(self):
        nodes = [
            {"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {"isStart": True, "messageType": "get_user_data", "message": "What's your city?", "variable": "city"}},
            {"id": "echo", "type": "message", "position": {"x": 1, "y": 0}, "data": {"messageType": "text", "message": "You are in {{city}}"}},
        ]
        edges = [{"id": "e1", "source": "start", "target": "echo", "sourceHandle": "continue"}]
        self.make_keyword("hello", self.make_flow_graph(nodes, edges, "Ask"))

        self.ingest("hello", "wamid.G1")
        self.pump()
        self.assertIn("What's your city?", self.sent_texts())
        self.assertEqual(self.session().status, "waiting")

        self.ingest("Mumbai", "wamid.G2")
        self.pump()
        self.assertIn("You are in Mumbai", self.sent_texts())
        self.assertEqual(self.session().status, "completed")

    # ---- condition branch ----
    def test_condition_branch(self):
        nodes = [
            {"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {"isStart": True, "messageType": "get_user_data", "message": "Type yes or no", "variable": "ans"}},
            {"id": "cond", "type": "message", "position": {"x": 1, "y": 0}, "data": {"messageType": "condition", "condition": {"source": "variable:ans", "operator": "is", "value": "yes"}}},
            {"id": "good", "type": "message", "position": {"x": 2, "y": 0}, "data": {"messageType": "text", "message": "Great!"}},
            {"id": "bad", "type": "message", "position": {"x": 2, "y": 1}, "data": {"messageType": "text", "message": "No problem"}},
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "cond", "sourceHandle": "continue"},
            {"id": "e2", "source": "cond", "target": "good", "sourceHandle": "true"},
            {"id": "e3", "source": "cond", "target": "bad", "sourceHandle": "false"},
        ]
        self.make_keyword("q", self.make_flow_graph(nodes, edges, "Cond"))

        self.ingest("q", "wamid.C1")
        self.pump()
        self.ingest("yes", "wamid.C2")
        self.pump()
        texts = self.sent_texts()
        self.assertIn("Great!", texts)
        self.assertNotIn("No problem", texts)
        self.assertEqual(self.session().status, "completed")

    # ---- delay resume ----
    def test_delay_resume(self):
        nodes = [
            {"id": "start", "type": "message", "position": {"x": 0, "y": 0}, "data": {"isStart": True, "messageType": "text", "message": "First"}},
            {"id": "wait", "type": "message", "position": {"x": 1, "y": 0}, "data": {"messageType": "delay", "delaySeconds": 3600}},
            {"id": "after", "type": "message", "position": {"x": 2, "y": 0}, "data": {"messageType": "text", "message": "Second"}},
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "wait", "sourceHandle": "continue"},
            {"id": "e2", "source": "wait", "target": "after", "sourceHandle": "continue"},
        ]
        self.make_keyword("go", self.make_flow_graph(nodes, edges, "Delay"))

        self.ingest("go", "wamid.D1")
        self.pump()
        self.assertIn("First", self.sent_texts())
        self.assertNotIn("Second", self.sent_texts())
        s = self.session()
        self.assertEqual(s.status, "waiting")
        self.assertEqual(s.wait_kind, "delay")

        # Force the delay to be due, then resume.
        s.resume_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()
        flow_engine.resume_due_delays(self.db, 50)
        self.db.expire_all()
        self.assertIn("Second", self.sent_texts())
        self.assertEqual(self.session().status, "completed")
