"""Automation API, tenant isolation, durable triggers and safe simulation."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import settings
from app.models import MessageDirection, MessageStatus
from app.models.automation import AutomationExecution, AutomationExecutionStatus, AutomationWorkerHeartbeat
from app.services.automation_execution_service import _claim, _condition_matches, utcnow, worker_health
from app.services.outbound_message_service import MessageSendFailedError
from app.services.automation_service import enqueue_for_inbound_message
from app.services.automation_execution_service import process_execution
from tests.inbox_fixtures import InboxTestCase


class AutomationApiTests(InboxTestCase):
    def headers(self, actor=None, tenant=None):
        return self.auth(actor or self.owner, tenant or self.tenant_a)

    def create_flow(self):
        response = self.client.post("/api/v1/automations", headers=self.headers(), json={"name": "Pricing follow-up"})
        self.assertEqual(response.status_code, 201, response.text)
        automation_id = response.json()["id"]
        detail = self.client.get(f"/api/v1/automations/{automation_id}", headers=self.headers()).json()
        trigger = detail["nodes"][0]
        condition_id, action_id = str(uuid.uuid4()), str(uuid.uuid4())
        body = {
            "nodes": [
                {"id": trigger["id"], "node_type": "trigger_message", "name": "Inbound WhatsApp Message", "config": {"channel_connection_id": str(self.wa_a.id)}, "sort_order": 0},
                {"id": condition_id, "node_type": "message_contains", "name": "Contains pricing", "config": {"value": "price", "case_sensitive": False}, "sort_order": 1},
                {"id": action_id, "node_type": "send_text", "name": "Reply", "config": {"text": "Thanks for asking about pricing."}, "sort_order": 2},
            ],
            "edges": [
                {"source_node_id": trigger["id"], "target_node_id": condition_id},
                {"source_node_id": condition_id, "target_node_id": action_id, "branch": "true"},
            ],
        }
        saved = self.client.put(f"/api/v1/automations/{automation_id}/flow", headers=self.headers(), json=body)
        self.assertEqual(saved.status_code, 200, saved.text)
        return automation_id, trigger["id"], condition_id, action_id

    def test_crud_tenant_isolation_and_rbac(self):
        created = self.client.post("/api/v1/automations", headers=self.headers(), json={"name": "First flow"})
        self.assertEqual(created.status_code, 201)
        automation_id = created.json()["id"]
        self.assertEqual(self.client.get(f"/api/v1/automations/{automation_id}", headers=self.headers(self.owner_b, self.tenant_b)).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/automations", headers=self.headers(self.agent), json={"name": "No permission"}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/automations/{automation_id}", headers=self.headers(), json={"name": "Renamed"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/automations/{automation_id}", headers=self.headers()).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/automations/{automation_id}", headers=self.headers()).json()["status"], "archived")

    def test_validation_simulation_and_inbound_enqueue_are_safe_and_idempotent(self):
        automation_id, _, _, _ = self.create_flow()
        validation = self.client.post(f"/api/v1/automations/{automation_id}/validate", headers=self.headers(), json={})
        self.assertEqual(validation.status_code, 200, validation.text)
        self.assertTrue(validation.json()["valid"], validation.json())
        simulation = self.client.post(f"/api/v1/automations/{automation_id}/simulate", headers=self.headers(), json={"message": "I need the price"})
        self.assertEqual(simulation.status_code, 200, simulation.text)
        self.assertTrue(simulation.json()["trigger_matched"])
        self.assertEqual(simulation.json()["steps"][-1]["result"], "would_execute")
        self.assertEqual(self.send_api.requests, [])

        activated = self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={})
        self.assertEqual(activated.status_code, 200, activated.text)
        contact = self.make_contact(self.tenant_a, "+15550109091")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        message = self.make_message(conversation, "Price please", direction=MessageDirection.INBOUND)
        first = enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=message.id)
        duplicate = enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=message.id)
        self.db.flush()
        rows = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=message.id).all()
        self.assertEqual((first, duplicate, len(rows)), (1, 0, 1))
        self.assertEqual(rows[0].status, "queued")
        execution_id = rows[0].id
        self.assertTrue(process_execution(self.db, execution_id))
        self.db.refresh(rows[0])
        self.assertEqual(rows[0].status, "completed")
        self.assertEqual(len(self.send_api.requests), 1)
        self.assertFalse(process_execution(self.db, execution_id))
        self.assertEqual(len(self.send_api.requests), 1)

    def test_invalid_flow_cannot_activate(self):
        response = self.client.post("/api/v1/automations", headers=self.headers(), json={"name": "Incomplete"})
        automation_id = response.json()["id"]
        activated = self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={})
        self.assertEqual(activated.status_code, 422)
        self.assertEqual(self.client.get(f"/api/v1/automations/{automation_id}", headers=self.headers()).json()["status"], "draft")

    def test_queued_execution_is_cancelled_if_automation_is_paused(self):
        automation_id, _, _, _ = self.create_flow()
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={}).status_code, 200)
        contact = self.make_contact(self.tenant_a, "+15550109092")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        message = self.make_message(conversation, "Price please", direction=MessageDirection.INBOUND)
        self.assertEqual(enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=message.id), 1)
        execution = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=message.id).one()
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/pause", headers=self.headers(), json={}).status_code, 200)
        self.assertFalse(process_execution(self.db, execution.id))
        self.db.refresh(execution)
        self.assertEqual(execution.status, "cancelled")
        self.assertEqual(self.send_api.requests, [])

    def test_transient_provider_failure_retries_with_backoff_and_same_idempotency_path(self):
        automation_id, _, _, _ = self.create_flow()
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={}).status_code, 200)
        contact = self.make_contact(self.tenant_a, "+15550109093")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        inbound = self.make_message(conversation, "Price please", direction=MessageDirection.INBOUND)
        pending = self.make_message(conversation, "Thanks", direction=MessageDirection.OUTBOUND, status=MessageStatus.PENDING)
        enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=inbound.id)
        execution = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=inbound.id).one()
        failure = MessageSendFailedError("provider timeout", pending.id)
        with patch("app.services.automation_execution_service.outbound_message_service.send_message", side_effect=failure):
            self.assertTrue(process_execution(self.db, execution.id))
        self.db.refresh(execution)
        self.assertEqual(execution.status, "retrying")
        self.assertEqual(execution.attempt_count, 1)
        self.assertEqual(execution.last_error_type, "provider_pending")
        first_delay = (execution.next_retry_at - utcnow()).total_seconds()
        self.assertGreater(first_delay, 0)
        self.assertLessEqual(first_delay, 2)
        execution.next_retry_at = utcnow() - timedelta(seconds=1)
        self.db.commit()
        with patch("app.services.automation_execution_service.outbound_message_service.send_message", side_effect=failure):
            self.assertTrue(process_execution(self.db, execution.id))
        self.db.refresh(execution)
        self.assertEqual(execution.attempt_count, 2)
        second_delay = (execution.next_retry_at - utcnow()).total_seconds()
        self.assertGreater(second_delay, 1)
        self.assertLessEqual(second_delay, 3)
        self.assertEqual(self.send_api.requests, [])

    def test_delay_schedules_resume_without_blocking_or_sending(self):
        automation_id, _, _, _ = self.create_flow()
        detail = self.client.get(f"/api/v1/automations/{automation_id}", headers=self.headers()).json()
        trigger_id = detail["nodes"][0]["id"]
        delay_id, send_id = str(uuid.uuid4()), str(uuid.uuid4())
        body = {"nodes": [
            {"id": trigger_id, "node_type": "trigger_message", "name": "Inbound", "config": {"channel_connection_id": str(self.wa_a.id)}, "sort_order": 0},
            {"id": delay_id, "node_type": "delay", "name": "Wait", "config": {"duration": 10, "unit": "minutes"}, "sort_order": 1},
            {"id": send_id, "node_type": "send_text", "name": "Follow-up", "config": {"text": "Follow-up"}, "sort_order": 2},
        ], "edges": [{"source_node_id": trigger_id, "target_node_id": delay_id}, {"source_node_id": delay_id, "target_node_id": send_id}]}
        self.assertEqual(self.client.put(f"/api/v1/automations/{automation_id}/flow", headers=self.headers(), json=body).status_code, 200)
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={}).status_code, 200)
        contact = self.make_contact(self.tenant_a, "+15550109094")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        inbound = self.make_message(conversation, "Hello", direction=MessageDirection.INBOUND)
        enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=inbound.id)
        execution = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=inbound.id).one()
        self.assertTrue(process_execution(self.db, execution.id))
        self.db.refresh(execution)
        self.assertEqual(execution.status, "queued")
        self.assertEqual(execution.resume_node_id, uuid.UUID(send_id))
        self.assertGreater(execution.next_retry_at, utcnow() + timedelta(minutes=9))
        self.assertEqual(self.send_api.requests, [])

    def test_condition_operators_and_timezone_aware_business_hours(self):
        now = datetime(2026, 10, 5, 4, 30, tzinfo=timezone.utc)  # Monday, 10:00 in Kolkata.
        business = {"timezone": "Asia/Kolkata", "working_days": [0, 1, 2, 3, 4], "start_time": "09:00", "end_time": "18:00"}
        self.assertTrue(_condition_matches("business_hours", business, "", now))
        self.assertFalse(_condition_matches("business_hours", business, "", now + timedelta(days=6)))
        checks = [("contains", "a price request", True), ("equals", "PRICE", True), ("starts_with", "Price today", True), ("ends_with", "good price", True)]
        for operator, text, expected in checks:
            with self.subTest(operator=operator):
                self.assertEqual(_condition_matches("message_contains", {"operator": operator, "value": "price"}, text, now), expected)

    def test_claiming_and_worker_heartbeat(self):
        automation_id, _, _, _ = self.create_flow()
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={}).status_code, 200)
        contact = self.make_contact(self.tenant_a, "+15550109095")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        inbound = self.make_message(conversation, "Price please", direction=MessageDirection.INBOUND)
        enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=inbound.id)
        execution = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=inbound.id).one()
        self.assertIsNotNone(_claim(self.db, execution.id, "worker-a"))
        self.assertIsNone(_claim(self.db, execution.id, "worker-b"))
        execution.claimed_at = utcnow() - timedelta(minutes=3)
        execution.attempt_count = 1
        self.db.commit()
        self.assertTrue(process_execution(self.db, execution.id, "worker-b"))
        self.db.refresh(execution)
        self.assertEqual(execution.status, "completed")
        self.assertEqual(len(self.send_api.requests), 1)
        self.db.add(AutomationWorkerHeartbeat(worker_id="test-worker", last_seen_at=utcnow(), processed_count=2))
        self.db.commit()
        self.assertEqual(worker_health(self.db)["status"], "healthy")
        health = self.client.get("/api/v1/automations/worker-health", headers=self.headers())
        self.assertEqual(health.status_code, 200, health.text)
        self.assertEqual(health.json()["status"], "healthy")
        metrics = self.client.get(f"/api/v1/automations/{automation_id}/metrics", headers=self.headers())
        self.assertEqual(metrics.status_code, 200, metrics.text)
        self.assertEqual((metrics.json()["total"], metrics.json()["completed"]), (1, 1))

    def test_execution_snapshot_survives_paused_draft_edits(self):
        automation_id, _, _, _ = self.create_flow()
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={}).status_code, 200)
        contact = self.make_contact(self.tenant_a, "+15550109096")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        inbound = self.make_message(conversation, "Price please", direction=MessageDirection.INBOUND)
        enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=inbound.id)
        execution = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=inbound.id).one()
        snapshot = execution.flow_snapshot
        version = execution.automation_version
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/pause", headers=self.headers(), json={}).status_code, 200)
        detail = self.client.get(f"/api/v1/automations/{automation_id}", headers=self.headers()).json()
        for node in detail["nodes"]:
            if node["node_type"] == "send_text":
                node["config"]["text"] = "Edited draft reply"
        payload = {"nodes": [{key: node[key] for key in ("id", "node_type", "name", "config", "sort_order")} for node in detail["nodes"]],
                   "edges": [{key: edge[key] for key in ("source_node_id", "target_node_id", "branch")} for edge in detail["edges"]]}
        saved = self.client.put(f"/api/v1/automations/{automation_id}/flow", headers=self.headers(), json=payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.db.refresh(execution)
        self.assertEqual(execution.automation_version, version)
        self.assertEqual(execution.flow_snapshot, snapshot)

    def test_execution_step_limit_fails_cleanly(self):
        automation_id, _, _, _ = self.create_flow()
        self.assertEqual(self.client.post(f"/api/v1/automations/{automation_id}/activate", headers=self.headers(), json={}).status_code, 200)
        contact = self.make_contact(self.tenant_a, "+15550109097")
        conversation = self.make_conversation(self.tenant_a, contact, self.wa_a)
        inbound = self.make_message(conversation, "Price please", direction=MessageDirection.INBOUND)
        enqueue_for_inbound_message(self.db, tenant_id=self.tenant_a.id, channel_id=self.wa_a.id, conversation_id=conversation.id, contact_id=contact.id, message_id=inbound.id)
        execution = self.db.query(AutomationExecution).filter_by(tenant_id=self.tenant_a.id, automation_id=uuid.UUID(automation_id), trigger_message_id=inbound.id).one()
        with patch.object(settings, "automation_max_steps", 1):
            self.assertTrue(process_execution(self.db, execution.id))
        self.db.refresh(execution)
        self.assertEqual(execution.status, "failed")
        self.assertIn("step limit", execution.error_summary)
        self.assertEqual(self.send_api.requests, [])
