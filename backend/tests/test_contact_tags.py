"""
Contacts module additions: tags (CRUD + counts + isolation), tag
assignment (single + bulk), enriched list (channel identities + tags),
contact delete (single / bulk / all), CSV export, RBAC and tenant isolation.
Reuses the Unified Inbox fixtures (two tenants, every role, channels).
"""
import csv
import io
import uuid

from app.models import ChannelType, Contact, ContactTag, Conversation, Tag
from tests.inbox_fixtures import InboxTestCase

CONTACTS = "/api/v1/contacts"
TAGS = "/api/v1/tags"


class ContactTagsTestCase(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.c1 = cls.make_contact(cls.tenant_a, phone="15550000011", first_name="Ann")
        cls.c2 = cls.make_contact(cls.tenant_a, phone="15550000012", first_name="Ben")
        cls.c_b = cls.make_contact(cls.tenant_b, phone="15559990001", first_name="Bee")

    def h(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def make_tag(self, name, color="#176b59", actor=None, tenant=None):
        return self.client.post(TAGS, headers=self.h(actor, tenant), json={"name": name, "color": color})

    # ========== tags CRUD ==========

    def test_01_tag_crud_and_counts(self):
        created = self.make_tag("VIP", "#aa0000")
        self.assertEqual(created.status_code, 201, created.text)
        tag = created.json()
        self.assertEqual((tag["name"], tag["color"], tag["contact_count"]), ("VIP", "#aa0000", 0))

        # Duplicate name in the same tenant -> conflict.
        self.assertEqual(self.make_tag("VIP").status_code, 409)

        # Update.
        upd = self.client.patch(f"{TAGS}/{tag['id']}", headers=self.h(), json={"name": "VIP Gold"})
        self.assertEqual(upd.status_code, 200, upd.text)
        self.assertEqual(upd.json()["name"], "VIP Gold")

        listing = self.client.get(TAGS, headers=self.h())
        self.assertEqual(listing.status_code, 200)
        self.assertIn("VIP Gold", {t["name"] for t in listing.json()["items"]})

    def test_02_tag_rbac(self):
        # VIEWER can read tags but not create them.
        self.assertEqual(self.client.get(TAGS, headers=self.h(self.viewer)).status_code, 200)
        self.assertEqual(self.make_tag("NoPerm", actor=self.viewer).status_code, 403)

    def test_03_tag_tenant_isolation(self):
        a_tag = self.make_tag("OnlyA").json()
        # Tenant B cannot see A's tag nor modify it.
        b_names = {t["name"] for t in self.client.get(TAGS, headers=self.h(self.owner_b, self.tenant_b)).json()["items"]}
        self.assertNotIn("OnlyA", b_names)
        self.assertEqual(
            self.client.patch(f"{TAGS}/{a_tag['id']}", headers=self.h(self.owner_b, self.tenant_b), json={"name": "x"}).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"{TAGS}/{a_tag['id']}", headers=self.h(self.owner_b, self.tenant_b)).status_code,
            404,
        )

    # ========== assignment ==========

    def test_04_set_contact_tags_and_enriched_list(self):
        t1 = self.make_tag("Lead").json()
        t2 = self.make_tag("Hot").json()
        resp = self.client.post(f"{CONTACTS}/{self.c1.id}/tags", headers=self.h(), json={"tag_ids": [t1["id"], t2["id"]]})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual({t["name"] for t in resp.json()["tags"]}, {"Lead", "Hot"})

        # The tag now reports a contact count of 1.
        counts = {t["name"]: t["contact_count"] for t in self.client.get(TAGS, headers=self.h()).json()["items"]}
        self.assertEqual(counts["Lead"], 1)

        # Enriched list carries tags, filterable by tag.
        filtered = self.client.get(f"{CONTACTS}?tag_id={t1['id']}", headers=self.h())
        ids = {c["id"] for c in filtered.json()["items"]}
        self.assertEqual(ids, {str(self.c1.id)})

    def test_05_set_contact_tags_replaces(self):
        t1 = self.make_tag("One").json()
        t2 = self.make_tag("Two").json()
        self.client.post(f"{CONTACTS}/{self.c1.id}/tags", headers=self.h(), json={"tag_ids": [t1["id"]]})
        resp = self.client.post(f"{CONTACTS}/{self.c1.id}/tags", headers=self.h(), json={"tag_ids": [t2["id"]]})
        self.assertEqual({t["name"] for t in resp.json()["tags"]}, {"Two"})

    def test_06_cannot_assign_other_tenant_tag(self):
        b_tag = self.make_tag("BTag", actor=self.owner_b, tenant=self.tenant_b).json()
        resp = self.client.post(f"{CONTACTS}/{self.c1.id}/tags", headers=self.h(), json={"tag_ids": [b_tag["id"]]})
        self.assertEqual(resp.status_code, 422)

    def test_07_cannot_tag_other_tenant_contact(self):
        t = self.make_tag("MineA").json()
        resp = self.client.post(f"{CONTACTS}/{self.c_b.id}/tags", headers=self.h(), json={"tag_ids": [t["id"]]})
        self.assertEqual(resp.status_code, 404)

    def test_08_bulk_apply_tags(self):
        t1 = self.make_tag("Bulk1").json()
        t2 = self.make_tag("Bulk2").json()
        resp = self.client.post(f"{CONTACTS}/tags", headers=self.h(), json={
            "contact_ids": [str(self.c1.id), str(self.c2.id), str(self.c_b.id)],  # c_b is another tenant's
            "add_tag_ids": [t1["id"]],
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["affected"], 2)  # only this tenant's two contacts
        # Remove t1, add t2 across both.
        self.client.post(f"{CONTACTS}/tags", headers=self.h(), json={
            "contact_ids": [str(self.c1.id), str(self.c2.id)],
            "add_tag_ids": [t2["id"]], "remove_tag_ids": [t1["id"]],
        })
        got = self.client.get(f"{CONTACTS}/{self.c1.id}", headers=self.h()).json()
        self.assertEqual({t["name"] for t in got["tags"]}, {"Bulk2"})
        # c_b (tenant B) was never tagged.
        self.assertEqual(
            self.db.query(ContactTag).filter_by(tenant_id=self.tenant_b.id).count(), 0,
        )

    # ========== enriched channel identities ==========

    def test_09_list_shows_channel_identities(self):
        contact = self.make_contact(self.tenant_a, phone="15550000099", first_name="Ivy")
        self.db.add_all([])
        from app.models import ContactIdentity
        self.db.add(ContactIdentity(
            tenant_id=self.tenant_a.id, contact_id=contact.id,
            channel_type=ChannelType.INSTAGRAM.value, external_id="ig-xyz", display_name="ivy_ig",
        ))
        self.db.commit()
        got = self.client.get(f"{CONTACTS}/{contact.id}", headers=self.h()).json()
        self.assertEqual([i["channel_type"] for i in got["identities"]], ["instagram"])
        # Filter by channel.
        filtered = self.client.get(f"{CONTACTS}?channel_type=instagram", headers=self.h())
        self.assertIn(str(contact.id), {c["id"] for c in filtered.json()["items"]})

    # ========== delete ==========

    def test_10_delete_single_contact_tenant_scoped(self):
        contact = self.make_contact(self.tenant_a, phone="15550000050")
        self.assertEqual(self.client.delete(f"{CONTACTS}/{contact.id}", headers=self.h()).status_code, 204)
        self.assertIsNone(self.reload(Contact, contact.id))
        # Cannot delete another tenant's contact.
        self.assertEqual(self.client.delete(f"{CONTACTS}/{self.c_b.id}", headers=self.h()).status_code, 404)
        self.assertIsNotNone(self.reload(Contact, self.c_b.id))

    def test_11_delete_cascades_conversations(self):
        contact = self.make_contact(self.tenant_a, phone="15550000051")
        conv = self.make_conversation(self.tenant_a, contact, self.wa_a)
        self.make_message(conv, "hi")
        self.db.commit()
        contact_id, conv_id = contact.id, conv.id
        self.assertEqual(self.client.delete(f"{CONTACTS}/{contact_id}", headers=self.h()).status_code, 204)
        self.db.expire_all()
        self.assertEqual(self.db.query(Contact).filter_by(id=contact_id).count(), 0)
        self.assertEqual(self.db.query(Conversation).filter_by(id=conv_id).count(), 0)

    def test_12_delete_requires_permission(self):
        contact = self.make_contact(self.tenant_a, phone="15550000052")
        # AGENT has contact:update but not contact:delete.
        self.assertEqual(self.client.delete(f"{CONTACTS}/{contact.id}", headers=self.h(self.agent)).status_code, 403)
        self.assertIsNotNone(self.db.get(Contact, contact.id))

    def test_13_bulk_delete(self):
        a = self.make_contact(self.tenant_a, phone="15550000061")
        b = self.make_contact(self.tenant_a, phone="15550000062")
        resp = self.client.post(f"{CONTACTS}/bulk-delete", headers=self.h(), json={
            "contact_ids": [str(a.id), str(b.id), str(self.c_b.id)],  # c_b is tenant B
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["deleted"], 2)
        self.assertIsNotNone(self.db.get(Contact, self.c_b.id))  # tenant B untouched

    def test_14_delete_all_requires_confirmation_and_is_tenant_scoped(self):
        self.make_contact(self.tenant_a, phone="15550000071")
        before_b = self.db.query(Contact).filter_by(tenant_id=self.tenant_b.id).count()
        # Wrong confirmation phrase -> rejected, nothing deleted.
        bad = self.client.post(f"{CONTACTS}/all/delete", headers=self.h(), json={"confirm": "delete"})
        self.assertEqual(bad.status_code, 422)
        self.assertGreater(self.db.query(Contact).filter_by(tenant_id=self.tenant_a.id).count(), 0)
        # Correct phrase -> deletes only tenant A.
        ok = self.client.post(f"{CONTACTS}/all/delete", headers=self.h(), json={"confirm": "DELETE ALL"})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(self.db.query(Contact).filter_by(tenant_id=self.tenant_a.id).count(), 0)
        self.assertEqual(self.db.query(Contact).filter_by(tenant_id=self.tenant_b.id).count(), before_b)

    # ========== export ==========

    def test_15_export_csv_tenant_scoped(self):
        t = self.make_tag("Exp").json()
        self.client.post(f"{CONTACTS}/{self.c1.id}/tags", headers=self.h(), json={"tag_ids": [t["id"]]})
        resp = self.client.get(f"{CONTACTS}/export", headers=self.h())
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("text/csv", resp.headers["content-type"])
        rows = list(csv.DictReader(io.StringIO(resp.text)))
        names = {r["name"] for r in rows}
        self.assertIn("Ann", names)
        self.assertNotIn("Bee", names)  # tenant B contact never exported
        ann = next(r for r in rows if r["name"] == "Ann")
        self.assertEqual(ann["tags"], "Exp")

    def test_16_delete_tag_keeps_contacts(self):
        t = self.make_tag("Temp").json()
        self.client.post(f"{CONTACTS}/{self.c1.id}/tags", headers=self.h(), json={"tag_ids": [t["id"]]})
        self.assertEqual(self.client.delete(f"{TAGS}/{t['id']}", headers=self.h()).status_code, 204)
        # Contact still exists; its tag association is gone.
        self.assertIsNotNone(self.db.get(Contact, self.c1.id))
        got = self.client.get(f"{CONTACTS}/{self.c1.id}", headers=self.h()).json()
        self.assertEqual(got["tags"], [])
        self.assertIsNone(self.db.query(Tag).filter_by(id=uuid.UUID(t["id"])).first())
