import datetime
from sqlalchemy import select

from tests.base import DatabaseTestCase
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationStatus
from app.models.channel_connection import ChannelConnection, ChannelType, ChannelStatus
from app.models.message import Message, MessageDirection, MessageType, MessageStatus

class TestAnalytics(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a = self.make_tenant("Tenant A")
        self.tenant_b = self.make_tenant("Tenant B")
        self.admin_a = self.make_member(self.tenant_a, "ADMIN")
        
        # Add some mock data for Tenant A
        chan = ChannelConnection(
            tenant_id=self.tenant_a.id,
            channel_type=ChannelType.WHATSAPP,
            name="WA Channel",
            status=ChannelStatus.CONNECTED
        )
        self.db.add(chan)
        self.db.commit()
        
        contact1 = Contact(tenant_id=self.tenant_a.id, phone_number="123")
        contact2 = Contact(tenant_id=self.tenant_b.id, phone_number="456") # other tenant
        self.db.add_all([contact1, contact2])
        self.db.commit()
        
        conv1 = Conversation(
            tenant_id=self.tenant_a.id,
            contact_id=contact1.id,
            channel_connection_id=chan.id,
            status=ConversationStatus.OPEN
        )
        conv2 = Conversation(
            tenant_id=self.tenant_a.id,
            contact_id=contact1.id,
            channel_connection_id=chan.id,
            status=ConversationStatus.RESOLVED
        )
        self.db.add_all([conv1, conv2])
        self.db.commit()
        
        # Messages
        msg1 = Message(
            tenant_id=self.tenant_a.id,
            conversation_id=conv1.id,
            contact_id=contact1.id,
            channel_connection_id=chan.id,
            direction=MessageDirection.INBOUND,
            message_type=MessageType.TEXT,
            status=MessageStatus.RECEIVED
        )
        msg2 = Message(
            tenant_id=self.tenant_a.id,
            conversation_id=conv1.id,
            contact_id=contact1.id,
            channel_connection_id=chan.id,
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            status=MessageStatus.DELIVERED
        )
        self.db.add_all([msg1, msg2])
        self.db.commit()
        
        self.chan = chan

    def test_analytics_overview(self):
        res = self.client.get("/api/v1/analytics/overview", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_contacts"], 1)
        self.assertEqual(data["total_chats"], 2)
        self.assertEqual(data["open_chats"], 1)
        self.assertEqual(data["pending_chats"], 0)
        self.assertEqual(data["resolved_chats"], 1)
        self.assertEqual(data["active_flows"], 0)
        
    def test_analytics_overview_with_dates(self):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        res = self.client.get(f"/api/v1/analytics/overview?start_date={today}T00:00:00Z&end_date={today}T23:59:59Z", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        
    def test_analytics_channels(self):
        res = self.client.get("/api/v1/analytics/channels", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "WA Channel")
        
    def test_analytics_time_series(self):
        now = datetime.datetime.now()
        start = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = self.client.get(f"/api/v1/analytics/time-series?start_date={start}&end_date={end}", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["inbound"], 1)
        self.assertEqual(data[0]["outbound"], 1)
        
    def test_analytics_automations(self):
        res = self.client.get("/api/v1/analytics/automations", headers=self.auth(self.admin_a, self.tenant_a))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_executions"], 0)
