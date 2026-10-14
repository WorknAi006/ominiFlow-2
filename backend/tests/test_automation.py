"""Rule-based automations: CRUD API, options, tenant isolation, and live dispatch."""
from app.models import AutomationRun, ContactTag, Tag
from app.schemas.automation import AutomationCreate
from app.services import automation_service, contact_service
from tests.inbox_fixtures import InboxTestCase


class AutomationApiTests(InboxTestCase):
    def head(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def test_crud_and_tenant_isolation(self):
        created = self.client.post("/api/v1/automations", headers=self.head(), json={
            "name": "Welcome new contacts",
            "trigger_type": "new_contact_created",
            "actions": [{"type": "add_tags", "config": {"value": "vip"}}],
        })
        self.assertEqual(created.status_code, 201, created.text)
        automation_id = created.json()["id"]

        listed = self.client.get("/api/v1/automations", headers=self.head()).json()
        self.assertTrue(any(a["id"] == automation_id for a in listed["items"]))

        # Another tenant cannot see it.
        cross = self.client.get(f"/api/v1/automations/{automation_id}", headers=self.head(self.owner_b, self.tenant_b))
        self.assertEqual(cross.status_code, 404)

        paused = self.client.post(f"/api/v1/automations/{automation_id}/pause", headers=self.head())
        self.assertEqual(paused.status_code, 200)
        self.assertFalse(paused.json()["is_active"])

        deleted = self.client.delete(f"/api/v1/automations/{automation_id}", headers=self.head())
        self.assertEqual(deleted.status_code, 204)

    def test_options_catalogue(self):
        opts = self.client.get("/api/v1/automations/options", headers=self.head()).json()
        trigger_values = {t["value"] for t in opts["triggers"]}
        self.assertIn("new_contact_created", trigger_values)
        action_values = {a["value"] for a in opts["actions"]}
        self.assertIn("add_tags", action_values)

    def test_new_contact_dispatch_runs_action(self):
        # Rule: on new contact, add tag "vip" (no conditions = always run).
        automation_service.create_automation(
            self.db, self.tenant_a.id, self.owner,
            AutomationCreate(
                name="Tag new contacts",
                trigger_type="new_contact_created",
                actions=[{"type": "add_tags", "config": {"value": "vip"}}],
            ),
        )
        self.db.commit()

        contact = self.make_contact(self.tenant_a, phone="+12025550111")
        self.db.commit()
        automation_service.on_contact_created(self.db, contact)
        self.db.expire_all()

        tag = self.db.query(Tag).filter_by(tenant_id=self.tenant_a.id, name="vip").first()
        self.assertIsNotNone(tag)
        link = self.db.query(ContactTag).filter_by(tenant_id=self.tenant_a.id, contact_id=contact.id, tag_id=tag.id).first()
        self.assertIsNotNone(link)
        runs = self.db.query(AutomationRun).filter_by(tenant_id=self.tenant_a.id).all()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "success")

    def test_condition_blocks_action(self):
        # Rule only runs when existing_contact name is "Nobody" — so it skips.
        automation_service.create_automation(
            self.db, self.tenant_a.id, self.owner,
            AutomationCreate(
                name="Conditional tag",
                trigger_type="new_contact_created",
                match_type="all",
                conditions=[{"field": "existing_contact", "operator": "is", "value": "Nobody"}],
                actions=[{"type": "add_tags", "config": {"value": "shouldnot"}}],
            ),
        )
        self.db.commit()
        contact = self.make_contact(self.tenant_a, phone="+12025550112", first_name="Someone")
        self.db.commit()
        automation_service.on_contact_created(self.db, contact)
        self.db.expire_all()
        tag = self.db.query(Tag).filter_by(tenant_id=self.tenant_a.id, name="shouldnot").first()
        self.assertIsNone(tag)
