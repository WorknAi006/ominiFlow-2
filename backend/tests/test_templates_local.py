"""Local (draft) template creation through the API."""
from tests.inbox_fixtures import InboxTestCase


class LocalTemplateTests(InboxTestCase):
    def head(self):
        return self.auth(self.owner, self.tenant_a)

    def test_create_local_draft_template(self):
        r = self.client.post("/api/v1/templates", headers=self.head(), json={
            "channel_connection_id": str(self.wa_a.id),
            "name": "welcome_offer",
            "language": "en_US",
            "category": "MARKETING",
            "body_text": "Hi {{1}}, welcome!",
            "footer_text": "Reply STOP to opt out",
            "buttons": ["Shop now", "Talk to us"],
        })
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        self.assertEqual(body["status"], "draft")
        self.assertFalse(body["is_usable"])
        self.assertTrue(any(c.get("type") == "BODY" for c in body["components"]))

        # Appears in the tenant-wide list.
        listed = self.client.get("/api/v1/templates", headers=self.head()).json()
        self.assertTrue(any(t["name"] == "welcome_offer" for t in listed["items"]))

    def test_create_local_media_header_draft(self):
        response = self.client.post("/api/v1/templates", headers=self.head(), json={
            "channel_connection_id": str(self.wa_a.id),
            "name": "invoice_video",
            "language": "en_US",
            "category": "UTILITY",
            "header_format": "VIDEO",
            "body_text": "Your update is ready.",
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIn(
            {"type": "HEADER", "format": "VIDEO"},
            response.json()["components"],
        )

    def test_duplicate_name_language_rejected(self):
        payload = {
            "channel_connection_id": str(self.wa_a.id),
            "name": "dup_tpl", "language": "en_US", "body_text": "Hello",
        }
        self.assertEqual(self.client.post("/api/v1/templates", headers=self.head(), json=payload).status_code, 201)
        self.assertEqual(self.client.post("/api/v1/templates", headers=self.head(), json=payload).status_code, 409)

    def test_cross_tenant_channel_rejected(self):
        r = self.client.post("/api/v1/templates", headers=self.head(), json={
            "channel_connection_id": str(self.wa_b.id),  # tenant B's channel
            "name": "sneaky", "language": "en_US", "body_text": "Hi",
        })
        self.assertEqual(r.status_code, 404, r.text)
