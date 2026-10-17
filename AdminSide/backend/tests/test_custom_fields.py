"""
Custom fields (definitions + per-contact values), CSV import, and the
derived source filter. Reuses the Unified Inbox fixtures (two tenants).
"""
import uuid

from app.models import ContactFieldValue, CustomFieldDefinition
from tests.inbox_fixtures import InboxTestCase

CONTACTS = "/api/v1/contacts"
FIELDS = "/api/v1/custom-fields"


class CustomFieldsTestCase(InboxTestCase):

    @classmethod
    def create_fixtures(cls) -> None:
        super().create_fixtures()
        cls.c1 = cls.make_contact(cls.tenant_a, phone="15550000081", first_name="Cara")
        cls.c_b = cls.make_contact(cls.tenant_b, phone="15559990081", first_name="Bee")

    def h(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def make_field(self, label, ftype="text", options=None, actor=None, tenant=None):
        body = {"label": label, "field_type": ftype}
        if options is not None:
            body["options"] = options
        return self.client.post(FIELDS, headers=self.h(actor, tenant), json=body)

    # ========== definitions ==========

    def test_01_field_crud(self):
        created = self.make_field("Company")
        self.assertEqual(created.status_code, 201, created.text)
        field = created.json()
        self.assertEqual((field["label"], field["field_type"], field["key"]), ("Company", "text", "company"))

        upd = self.client.patch(f"{FIELDS}/{field['id']}", headers=self.h(), json={"label": "Org"})
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.json()["label"], "Org")

        listing = self.client.get(FIELDS, headers=self.h())
        self.assertIn("Org", {f["label"] for f in listing.json()["items"]})

    def test_02_unique_key_suffix(self):
        a = self.make_field("City").json()
        b = self.make_field("City").json()
        self.assertEqual(a["key"], "city")
        self.assertEqual(b["key"], "city_2")

    def test_03_select_requires_options(self):
        bad = self.make_field("Plan", "select")
        self.assertEqual(bad.status_code, 422)
        ok = self.make_field("Plan", "select", ["Free", "Pro"])
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["options"], ["Free", "Pro"])

    def test_04_rbac_and_isolation(self):
        self.assertEqual(self.make_field("NoPerm", actor=self.viewer).status_code, 403)
        a_field = self.make_field("Secret").json()
        b_fields = {f["label"] for f in self.client.get(FIELDS, headers=self.h(self.owner_b, self.tenant_b)).json()["items"]}
        self.assertNotIn("Secret", b_fields)
        self.assertEqual(self.client.patch(f"{FIELDS}/{a_field['id']}", headers=self.h(self.owner_b, self.tenant_b), json={"label": "x"}).status_code, 404)

    # ========== values ==========

    def test_05_set_values_by_type(self):
        text = self.make_field("Note").json()
        num = self.make_field("Age", "number").json()
        boolean = self.make_field("VIP", "boolean").json()
        sel = self.make_field("Tier", "select", ["Gold", "Silver"]).json()
        multi = self.make_field("Interests", "multiselect", ["A", "B", "C"]).json()
        dt = self.make_field("DOB", "date").json()

        resp = self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {
            text["id"]: "hello", num["id"]: 42, boolean["id"]: True,
            sel["id"]: "Gold", multi["id"]: ["A", "C"], dt["id"]: "2026-01-15",
        }})
        self.assertEqual(resp.status_code, 200, resp.text)
        by_key = {fv["key"]: fv["value"] for fv in resp.json()["field_values"]}
        self.assertEqual(by_key["note"], "hello")
        self.assertEqual(by_key["age"], 42)
        self.assertEqual(by_key["vip"], True)
        self.assertEqual(by_key["tier"], "Gold")
        self.assertEqual(by_key["interests"], ["A", "C"])
        self.assertEqual(by_key["dob"], "2026-01-15")

    def test_06_value_validation(self):
        num = self.make_field("Score", "number").json()
        self.assertEqual(self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {num["id"]: "notnum"}}).status_code, 422)
        sel = self.make_field("Band", "select", ["X", "Y"]).json()
        self.assertEqual(self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {sel["id"]: "Z"}}).status_code, 422)

    def test_07_clear_value_with_null(self):
        f = self.make_field("Temp").json()
        self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {f["id"]: "v"}})
        resp = self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {f["id"]: None}})
        self.assertEqual([fv for fv in resp.json()["field_values"] if fv["key"] == "temp"], [])

    def test_08_cannot_use_other_tenant_field_or_contact(self):
        b_field = self.make_field("BOnly", actor=self.owner_b, tenant=self.tenant_b).json()
        self.assertEqual(self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {b_field["id"]: "x"}}).status_code, 404)
        a_field = self.make_field("AOnly").json()
        self.assertEqual(self.client.post(f"{CONTACTS}/{self.c_b.id}/fields", headers=self.h(), json={"values": {a_field["id"]: "x"}}).status_code, 404)

    def test_09_delete_field_removes_values_keeps_contacts(self):
        f = self.make_field("Gone").json()
        self.client.post(f"{CONTACTS}/{self.c1.id}/fields", headers=self.h(), json={"values": {f["id"]: "v"}})
        self.assertEqual(self.client.delete(f"{FIELDS}/{f['id']}", headers=self.h()).status_code, 204)
        got = self.client.get(f"{CONTACTS}/{self.c1.id}", headers=self.h()).json()
        self.assertEqual([fv for fv in got["field_values"] if fv["key"] == "gone"], [])
        self.db.expire_all()
        self.assertEqual(self.db.query(ContactFieldValue).filter_by(tenant_id=self.tenant_a.id).count(), 0)
        self.assertIsNotNone(self.client.get(f"{CONTACTS}/{self.c1.id}", headers=self.h()).json()["id"])

    # ========== import ==========

    def test_10_import_creates_skips_and_errors(self):
        resp = self.client.post(f"{CONTACTS}/import", headers=self.h(), json={"rows": [
            {"first_name": "New1", "phone_number": "15550010001"},
            {"first_name": "New2", "email": "new2@x.io"},
            {"first_name": "Dup", "phone_number": "15550000081"},   # matches c1
            {"first_name": "Empty"},                                 # no phone/email -> skipped
            {"first_name": "Bad", "phone_number": "not-a-phone"},    # invalid -> error
        ]})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["imported"], 2)
        self.assertEqual(body["skipped"], 2)   # dup + empty
        self.assertEqual(len(body["errors"]), 1)

    def test_11_import_is_tenant_scoped(self):
        before_b = self.db.query(type(self.c_b)).filter_by(tenant_id=self.tenant_b.id).count()
        self.client.post(f"{CONTACTS}/import", headers=self.h(), json={"rows": [{"first_name": "X", "phone_number": "15550020002"}]})
        self.assertEqual(self.db.query(type(self.c_b)).filter_by(tenant_id=self.tenant_b.id).count(), before_b)

    # ========== source filter ==========

    def test_12_source_filter(self):
        # c1 was created manually (no identity). Give a fresh contact an identity.
        from app.models import ContactIdentity, ChannelType
        inbox_contact = self.make_contact(self.tenant_a, phone="15550030003", first_name="Inboxer")
        self.db.add(ContactIdentity(tenant_id=self.tenant_a.id, contact_id=inbox_contact.id, channel_type=ChannelType.WHATSAPP.value, external_id="wa-1"))
        self.db.commit()
        manual = {c["id"] for c in self.client.get(f"{CONTACTS}?source=manual", headers=self.h()).json()["items"]}
        inbox = {c["id"] for c in self.client.get(f"{CONTACTS}?source=inbox", headers=self.h()).json()["items"]}
        self.assertIn(str(self.c1.id), manual)
        self.assertNotIn(str(self.c1.id), inbox)
        self.assertIn(str(inbox_contact.id), inbox)
        self.assertNotIn(str(inbox_contact.id), manual)
