import uuid
from unittest.mock import patch
from sqlalchemy import select

from tests.base import DatabaseTestCase
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_recipient import CampaignRecipient, CampaignRecipientStatus
from app.models.tag import Tag, ContactTag
from app.models.contact import Contact
from app.models.channel_connection import ChannelConnection, ChannelType, ChannelStatus
from app.services.campaign_execution_service import process_pending_recipients
from app.services.campaign import CampaignService

class TestCampaignExecution(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a = self.make_tenant("Tenant A")
        self.admin_a = self.make_member(self.tenant_a, "ADMIN")
        
        self.channel_a = ChannelConnection(
            tenant_id=self.tenant_a.id, 
            name="Test WhatsApp", 
            channel_type=ChannelType.WHATSAPP,
            status=ChannelStatus.CONNECTED
        )
        self.db.add(self.channel_a)
        
        self.tag_1 = Tag(tenant_id=self.tenant_a.id, name="VIP")
        self.db.add(self.tag_1)
        self.db.flush()

        self.contact_1 = Contact(tenant_id=self.tenant_a.id, phone_number="111")
        self.contact_2 = Contact(tenant_id=self.tenant_a.id, phone_number="222")
        self.db.add_all([self.contact_1, self.contact_2])
        self.db.flush()

        self.db.add(ContactTag(tenant_id=self.tenant_a.id, contact_id=self.contact_1.id, tag_id=self.tag_1.id))
        self.db.add(ContactTag(tenant_id=self.tenant_a.id, contact_id=self.contact_2.id, tag_id=self.tag_1.id))
        self.db.commit()

        self.campaign = Campaign(
            tenant_id=self.tenant_a.id,
            name="Promo",
            channel_connection_id=self.channel_a.id,
            text_content="Hello World",
            audience_config={"tags": [str(self.tag_1.id)]},
            status=CampaignStatus.DRAFT
        )
        self.db.add(self.campaign)
        self.db.commit()

    def test_start_campaign(self):
        service = CampaignService(self.db)
        started = service.start_campaign(self.tenant_a.id, self.campaign.id)
        
        self.assertEqual(started.status, CampaignStatus.SENDING)
        self.assertEqual(started.total_recipients, 2)
        
        # Verify recipients created
        recipients = self.db.scalars(select(CampaignRecipient).where(CampaignRecipient.campaign_id == self.campaign.id)).all()
        self.assertEqual(len(recipients), 2)
        self.assertTrue(all(r.status == CampaignRecipientStatus.PENDING for r in recipients))

    def test_start_campaign_twice_fails(self):
        service = CampaignService(self.db)
        service.start_campaign(self.tenant_a.id, self.campaign.id)
        
        with self.assertRaises(ValueError):
            service.start_campaign(self.tenant_a.id, self.campaign.id)

    @patch("app.services.campaign_execution_service.send_message")
    def test_worker_processes_recipients(self, mock_send):
        # Ensure channel has credentials if it's connected (mocking credentials check)
        self.channel_a.access_token_encrypted = b"dummy"
        self.channel_a.external_account_id = "123"
        self.db.commit()
        
        service = CampaignService(self.db)
        service.start_campaign(self.tenant_a.id, self.campaign.id)

        # Mock send_message to return a dummy message response
        class DummyMsg:
            external_message_id = "ext-id-1"
        mock_send.return_value = DummyMsg()
        
        result = process_pending_recipients(self.db, limit=5, worker_id="test-worker")
        
        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["sent"], 2)
        self.assertEqual(result["failed"], 0)
        
        self.db.refresh(self.campaign)
        self.assertEqual(self.campaign.delivered_count, 2)
        
        recipients = self.db.scalars(select(CampaignRecipient).where(CampaignRecipient.campaign_id == self.campaign.id)).all()
        self.assertTrue(all(r.status == CampaignRecipientStatus.SENT for r in recipients))
        self.assertTrue(all(r.external_message_id == "ext-id-1" for r in recipients))

    @patch("app.services.campaign_execution_service.send_message")
    def test_worker_sends_template_broadcast(self, mock_send):
        from app.models.message_template import MessageTemplate
        from app.schemas.message import TemplateMessageCreate

        self.channel_a.access_token_encrypted = b"dummy"
        self.channel_a.external_account_id = "123"
        tpl = MessageTemplate(
            tenant_id=self.tenant_a.id,
            channel_connection_id=self.channel_a.id,
            name="promo_offer",
            language="en_US",
            status="approved",
            components=[{"type": "BODY", "text": "Hi {{1}}, sale is on!"}],
        )
        self.db.add(tpl)
        self.db.commit()

        camp = Campaign(
            tenant_id=self.tenant_a.id,
            name="TemplatePromo",
            channel_connection_id=self.channel_a.id,
            message_template_id=tpl.id,
            template_params=[{"type": "body", "parameters": [{"type": "text", "text": "Alex"}]}],
            audience_config={"tags": [str(self.tag_1.id)]},
            status=CampaignStatus.DRAFT,
        )
        self.db.add(camp)
        self.db.commit()

        CampaignService(self.db).start_campaign(self.tenant_a.id, camp.id)

        class DummyMsg:
            external_message_id = "ext-tpl-1"
        mock_send.return_value = DummyMsg()

        result = process_pending_recipients(self.db, limit=5)
        self.assertEqual(result["sent"], 2)

        # A real template message (not text) was built and sent.
        sent = [c.args[4] for c in mock_send.call_args_list]
        self.assertTrue(sent)
        self.assertIsInstance(sent[0], TemplateMessageCreate)
        self.assertEqual(sent[0].template_name, "promo_offer")
        self.assertEqual(sent[0].language, "en_US")
        self.assertEqual(sent[0].components[0].parameters[0].text, "Alex")

    @patch("app.services.campaign_execution_service.send_message")
    def test_worker_handles_failure(self, mock_send):
        self.channel_a.access_token_encrypted = b"dummy"
        self.channel_a.external_account_id = "123"
        self.db.commit()
        
        service = CampaignService(self.db)
        service.start_campaign(self.tenant_a.id, self.campaign.id)

        from app.services.outbound_message_service import MessageSendFailedError
        mock_send.side_effect = MessageSendFailedError("WhatsApp rejected", uuid.uuid4())
        
        result = process_pending_recipients(self.db, limit=5)
        
        self.assertEqual(result["sent"], 0)
        
        # It should retry twice more
        process_pending_recipients(self.db, limit=5)
        process_pending_recipients(self.db, limit=5)
        
        self.db.refresh(self.campaign)
        self.assertEqual(self.campaign.failed_count, 2)
