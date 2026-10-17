import uuid
from sqlalchemy import select

from tests.base import DatabaseTestCase
from app.models.tag import Tag, ContactTag
from app.models.campaign import CampaignStatus

class TestCampaigns(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a = self.make_tenant("Tenant A")
        self.tenant_b = self.make_tenant("Tenant B")
        self.admin_a = self.make_member(self.tenant_a, "ADMIN")
        self.admin_b = self.make_member(self.tenant_b, "ADMIN")

        from app.models.channel_connection import ChannelConnection, ChannelType, ChannelStatus
        self.channel_a = ChannelConnection(
            tenant_id=self.tenant_a.id, 
            name="Test WhatsApp", 
            channel_type=ChannelType.WHATSAPP,
            status=ChannelStatus.CONNECTED
        )
        self.db.add(self.channel_a)
        self.db.commit()
        
        # Contacts and Tags for Audience
        self.tag_1 = Tag(tenant_id=self.tenant_a.id, name="VIP")
        self.tag_2 = Tag(tenant_id=self.tenant_a.id, name="Newsletter")
        self.db.add_all([self.tag_1, self.tag_2])
        self.db.commit()

        from app.models.contact import Contact
        self.contact_1 = Contact(tenant_id=self.tenant_a.id, phone_number="111")
        self.contact_2 = Contact(tenant_id=self.tenant_a.id, phone_number="222")
        self.db.add_all([self.contact_1, self.contact_2])
        self.db.commit()
        
        # Link contact_1 to tag_1
        self.db.add(ContactTag(tenant_id=self.tenant_a.id, contact_id=self.contact_1.id, tag_id=self.tag_1.id))
        self.db.commit()

    def test_preview_audience(self):
        res = self.client.post(
            "/api/v1/campaigns/preview-audience", 
            json={"audience_config": {"tags": [str(self.tag_1.id)]}}, 
            headers=self.auth(self.admin_a, self.tenant_a)
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total_contacts"], 1)

    def test_create_and_get_campaign(self):
        campaign_data = {
            "name": "Promo Q4",
            "channel_connection_id": str(self.channel_a.id),
            "text_content": "Hello!",
            "audience_config": {"tags": [str(self.tag_1.id)]}
        }
        res = self.client.post("/api/v1/campaigns", json=campaign_data, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        
        campaign = res.json()
        self.assertEqual(campaign["name"], "Promo Q4")
        self.assertEqual(campaign["total_recipients"], 1)
        self.assertEqual(campaign["status"], "draft")
        
        res = self.client.get(f"/api/v1/campaigns/{campaign['id']}", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], campaign["id"])

    def test_update_campaign(self):
        campaign_data = {
            "name": "Draft 1",
            "channel_connection_id": str(self.channel_a.id)
        }
        res = self.client.post("/api/v1/campaigns", json=campaign_data, headers=self.auth(self.admin_a, self.tenant_a))
        campaign_id = res.json()["id"]

        # Link contact 2 to tag 1 to increase audience
        self.db.add(ContactTag(tenant_id=self.tenant_a.id, contact_id=self.contact_2.id, tag_id=self.tag_1.id))
        self.db.commit()

        # Update config, verify audience is recalculated
        update_data = {
            "audience_config": {"tags": [str(self.tag_1.id)]},
            "name": "Draft 1 Updated"
        }
        res = self.client.patch(f"/api/v1/campaigns/{campaign_id}", json=update_data, headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total_recipients"], 2)

    def test_tenant_isolation(self):
        campaign_data = {
            "name": "Tenant A Campaign",
            "channel_connection_id": str(self.channel_a.id)
        }
        res = self.client.post("/api/v1/campaigns", json=campaign_data, headers=self.auth(self.admin_a, self.tenant_a))
        campaign_id = res.json()["id"]
        
        # Tenant B cannot read it
        res = self.client.get(f"/api/v1/campaigns/{campaign_id}", headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 404)
        
        # Tenant B cannot create campaign using Tenant A's channel
        bad_create = {
            "name": "Sneaky",
            "channel_connection_id": str(self.channel_a.id)
        }
        res = self.client.post("/api/v1/campaigns", json=bad_create, headers=self.auth(self.admin_b, self.tenant_b))
        self.assertEqual(res.status_code, 400)
