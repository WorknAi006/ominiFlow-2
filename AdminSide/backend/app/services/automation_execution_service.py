"""Bounded, retryable automation execution using PostgreSQL row locking."""
import logging
import socket
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_, select
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, SQLAlchemyError, TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Conversation, ConversationStatus, Message, MessageDirection, MessageStatus, TenantMembership, User
from app.models.automation import (
    Automation, AutomationExecution, AutomationExecutionLog, AutomationExecutionStatus,
    AutomationNodeType, AutomationStatus, AutomationWorkerHeartbeat,
)
from app.schemas.message import TemplateMessageCreate, TextMessageCreate
from app.services import conversation_service, outbound_message_service
from app.services.outbound_message_service import MessageSendFailedError

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _log(db: Session, execution_id: uuid.UUID, tenant_id: uuid.UUID, node_id: uuid.UUID | None, level: str, summary: str, details: dict[str, Any] | None = None) -> None:
    db.add(AutomationExecutionLog(tenant_id=tenant_id, execution_id=execution_id, node_id=node_id, level=level, summary=summary, details=details))
    db.commit()


def _worker_heartbeat(db: Session, worker_id: str, processed: int) -> None:
    row = db.get(AutomationWorkerHeartbeat, worker_id)
    now = utcnow()
    if row is None:
        row = AutomationWorkerHeartbeat(worker_id=worker_id, last_seen_at=now, processed_count=processed, last_batch_at=now if processed else None)
        db.add(row)
    else:
        row.last_seen_at = now
        row.processed_count += processed
        if processed:
            row.last_batch_at = now
    db.commit()


def worker_health(db: Session) -> dict[str, Any]:
    latest = db.query(AutomationWorkerHeartbeat).order_by(AutomationWorkerHeartbeat.last_seen_at.desc()).first()
    if latest is None:
        return {"status": "unavailable", "last_seen_at": None, "processed_count": 0}
    age = (utcnow() - latest.last_seen_at).total_seconds()
    status = "healthy" if age <= settings.automation_worker_healthy_seconds else "delayed" if age <= settings.automation_worker_delayed_seconds else "unavailable"
    return {"status": status, "last_seen_at": latest.last_seen_at, "processed_count": latest.processed_count}


def _claim(db: Session, execution_id: uuid.UUID, worker_id: str) -> AutomationExecution | None:
    now = utcnow()
    stale_before = now - timedelta(seconds=settings.automation_stale_claim_seconds)
    eligible = or_(
        (AutomationExecution.status == AutomationExecutionStatus.QUEUED) & or_(AutomationExecution.next_retry_at.is_(None), AutomationExecution.next_retry_at <= now),
        (AutomationExecution.status == AutomationExecutionStatus.RETRYING) & or_(AutomationExecution.next_retry_at.is_(None), AutomationExecution.next_retry_at <= now),
        (AutomationExecution.status == AutomationExecutionStatus.RUNNING) & or_(AutomationExecution.claimed_at < stale_before, AutomationExecution.claimed_at.is_(None)),
    )
    execution = db.query(AutomationExecution).filter(AutomationExecution.id == execution_id, eligible).with_for_update(skip_locked=True).first()
    if execution is None:
        db.rollback()
        return None
    recovered_stale = execution.status == AutomationExecutionStatus.RUNNING
    if recovered_stale:
        if execution.current_node_id is not None and execution.resume_node_id is None:
            execution.status = AutomationExecutionStatus.COMPLETED
            execution.completed_at = now
            execution.worker_id = None
            execution.claimed_at = None
            execution.next_retry_at = None
            execution.error_summary = None
            db.commit()
            _log(db, execution.id, execution.tenant_id, execution.current_node_id, "success", "Recovered completion checkpoint after worker interruption.")
            return None
        execution.last_error_type = "worker_lost"
        execution.error_summary = "Worker stopped before completing this execution."
        execution.status = AutomationExecutionStatus.RETRYING
        execution.next_retry_at = now
    is_new_work = execution.status == AutomationExecutionStatus.QUEUED and execution.resume_node_id is None
    if is_new_work or execution.status == AutomationExecutionStatus.RETRYING:
        execution.attempt_count += 1
    automation = db.query(Automation).filter(Automation.id == execution.automation_id, Automation.tenant_id == execution.tenant_id).first()
    if automation is None or automation.status != AutomationStatus.ACTIVE:
        execution.status = AutomationExecutionStatus.CANCELLED
        execution.completed_at = now
        execution.claimed_at = None
        execution.worker_id = None
        execution.error_summary = "Automation is no longer active."
        db.commit()
        return None
    execution.status = AutomationExecutionStatus.RUNNING
    execution.worker_id = worker_id
    execution.claimed_at = now
    execution.run_started_at = now
    execution.next_retry_at = None
    execution.started_at = execution.started_at or now
    db.commit()
    if recovered_stale:
        _log(db, execution.id, execution.tenant_id, execution.current_node_id, "warning", "Recovered a stale execution claim.", {"attempt": execution.attempt_count})
    return execution


def _load_actor(db: Session, tenant_id: uuid.UUID, automation: Automation) -> User | None:
    if automation.created_by_user_id is None:
        return None
    return db.query(User).join(TenantMembership, TenantMembership.user_id == User.id).filter(
        User.id == automation.created_by_user_id, User.is_active.is_(True),
        TenantMembership.tenant_id == tenant_id, TenantMembership.status == "active",
    ).first()


def _condition_matches(node_type: str, config: dict[str, Any], text: str, now: datetime) -> bool:
    if node_type == AutomationNodeType.MESSAGE_CONTAINS:
        operator = config.get("operator", "contains")
        left, right = str(text), str(config.get("value", ""))
        if not config.get("case_sensitive", False):
            left, right = left.casefold(), right.casefold()
        return {"contains": lambda: right in left, "equals": lambda: left == right,
                "starts_with": lambda: left.startswith(right), "ends_with": lambda: left.endswith(right)}[operator]()
    if node_type == AutomationNodeType.BUSINESS_HOURS:
        try:
            local = now.astimezone(ZoneInfo(str(config["timezone"])))
            days = config["working_days"]
            start = datetime.strptime(config["start_time"], "%H:%M").time()
            end = datetime.strptime(config["end_time"], "%H:%M").time()
        except (KeyError, ValueError, ZoneInfoNotFoundError):
            return False
        current = local.timetz().replace(tzinfo=None)
        if start < end:
            return local.weekday() in days and start <= current < end
        # Overnight business windows belong to the day on which they start.
        return (local.weekday() in days and current >= start) or ((local.weekday() - 1) % 7 in days and current < end)
    raise ValueError("unsupported condition")


def _next_node(edges_by_source: dict[str, list[dict[str, Any]]], node_id: str, branch: str | None) -> str | None:
    edge = next((item for item in edges_by_source.get(node_id, []) if item.get("branch") == branch), None)
    return str(edge["target_node_id"]) if edge else None


def _execute_action(db: Session, execution: AutomationExecution, automation: Automation, actor: User, conversation: Conversation, node: dict[str, Any]) -> str:
    config = node.get("config") or {}
    tenant_id = execution.tenant_id
    stable_key = uuid.uuid5(uuid.NAMESPACE_URL, f"omniflow:auto:{execution.id}:{node['id']}")
    if node["node_type"] == AutomationNodeType.SEND_TEXT:
        sent = outbound_message_service.send_message(db, tenant_id, actor, conversation.id, TextMessageCreate(type="text", text=config["text"]), idempotency_key=stable_key)
        if sent.status == MessageStatus.PENDING:
            raise MessageSendFailedError("provider outcome is still pending", sent.id)
        if sent.status == MessageStatus.FAILED:
            raise ValueError("provider previously rejected this idempotent message")
        return "Text message accepted by the existing message service."
    if node["node_type"] == AutomationNodeType.SEND_TEMPLATE:
        from app.models import MessageTemplate
        template_id = uuid.UUID(str(config["template_id"]))
        template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.channel_connection_id == conversation.channel_connection_id, MessageTemplate.is_active.is_(True)).first()
        if template is None:
            raise ValueError("template is unavailable for this conversation channel")
        sent = outbound_message_service.send_message(db, tenant_id, actor, conversation.id,
            TemplateMessageCreate(type="template", template_name=template.name, language=template.language, components=config.get("components") or []), idempotency_key=stable_key)
        if sent.status == MessageStatus.PENDING:
            raise MessageSendFailedError("provider outcome is still pending", sent.id)
        if sent.status == MessageStatus.FAILED:
            raise ValueError("provider previously rejected this idempotent message")
        return "Approved template message accepted by the existing message service."
    if node["node_type"] == AutomationNodeType.ASSIGN_CONVERSATION:
        user_id = uuid.UUID(str(config["user_id"]))
        member = db.query(TenantMembership.id).filter_by(tenant_id=tenant_id, user_id=user_id, status="active").first()
        if member is None:
            raise ValueError("assignee is not an active member of this workspace")
        conversation_service.assign_conversation(db, tenant_id, conversation.id, user_id)
        return "Conversation assigned to the configured workspace member."
    if node["node_type"] == AutomationNodeType.CHANGE_CONVERSATION_STATUS:
        conversation_service.change_status(db, tenant_id, conversation.id, ConversationStatus(config["status"]))
        return "Conversation status updated."
    raise ValueError("unsupported action node")


def _retryable(db: Session, tenant_id: uuid.UUID, exc: Exception) -> bool:
    if isinstance(exc, SQLAlchemyError):
        return isinstance(exc, (OperationalError, InterfaceError, SQLAlchemyTimeoutError)) or (isinstance(exc, DBAPIError) and exc.connection_invalidated)
    if isinstance(exc, MessageSendFailedError):
        message = db.query(Message).filter(Message.id == exc.message_id, Message.tenant_id == tenant_id).first()
        return message is not None and message.status == MessageStatus.PENDING
    return False


def _record_failure(db: Session, execution_id: uuid.UUID, exc: Exception, worker_id: str) -> None:
    db.rollback()
    execution = db.query(AutomationExecution).filter_by(id=execution_id, worker_id=worker_id).with_for_update().first()
    if execution is None or execution.status != AutomationExecutionStatus.RUNNING:
        db.rollback()
        return
    retryable = _retryable(db, execution.tenant_id, exc)
    now = utcnow()
    timed_out = execution.run_started_at is not None and (now - execution.run_started_at).total_seconds() >= settings.automation_execution_timeout_seconds
    should_retry = retryable and not timed_out and execution.attempt_count < execution.max_attempts
    safe_limits = {
        "flow exceeds the configured node limit": "Execution failed because the configured node limit was exceeded.",
        "execution exceeded the configured duration limit": "Execution failed because its maximum runtime was exceeded.",
        "execution exceeded the configured retry limit": "Execution failed because its retry limit was exceeded.",
        "execution exceeded the configured step limit": "Execution failed because the configured step limit was exceeded.",
    }
    limit_summary = safe_limits.get(str(exc))
    safe_type = "provider_pending" if isinstance(exc, MessageSendFailedError) and retryable else "database_error" if isinstance(exc, SQLAlchemyError) else "execution_limit" if limit_summary else "execution_error"
    execution.last_error_type = safe_type
    execution.error_summary = "A provider request has an ambiguous outcome; retry safely uses the same message key." if safe_type == "provider_pending" else "A database error interrupted this execution; it will be retried only if the error is transient." if safe_type == "database_error" else limit_summary or "A flow step failed. Check its configuration and workspace permissions."
    execution.worker_id = None
    execution.claimed_at = None
    if should_retry:
        delay = min(300, 2 ** max(0, execution.attempt_count - 1))
        execution.status = AutomationExecutionStatus.RETRYING
        execution.next_retry_at = now + timedelta(seconds=delay)
        execution.completed_at = None
    else:
        execution.status = AutomationExecutionStatus.FAILED
        execution.completed_at = now
        execution.next_retry_at = None
    failed_node = execution.current_node_id
    db.commit()
    summary = "Transient execution error; a retry has been scheduled." if should_retry else execution.error_summary
    _log(db, execution.id, execution.tenant_id, failed_node, "warning" if should_retry else "error", summary, {"error_type": safe_type, "attempt": execution.attempt_count})
    logger.warning("automation_execution_failed", extra={"execution_id": str(execution_id), "worker_id": worker_id, "error_type": safe_type, "retry_scheduled": should_retry})


def process_execution(db: Session, execution_id: uuid.UUID, worker_id: str = "automation-worker") -> bool:
    execution = _claim(db, execution_id, worker_id)
    if execution is None:
        return False
    tenant_id = execution.tenant_id
    try:
        automation = db.query(Automation).filter(Automation.id == execution.automation_id, Automation.tenant_id == tenant_id).first()
        conversation = db.query(Conversation).filter(Conversation.id == execution.conversation_id, Conversation.tenant_id == tenant_id).first()
        trigger_message = db.query(Message).filter(Message.id == execution.trigger_message_id, Message.tenant_id == tenant_id,
            Message.conversation_id == execution.conversation_id, Message.direction == MessageDirection.INBOUND).first()
        actor = _load_actor(db, tenant_id, automation) if automation else None
        if not automation or not conversation or not trigger_message or not actor:
            raise ValueError("tenant-scoped execution data is unavailable")
        snapshot = execution.flow_snapshot or {}
        nodes_list = snapshot.get("nodes", [])
        if len(nodes_list) > settings.automation_max_nodes:
            raise ValueError("flow exceeds the configured node limit")
        nodes = {str(node.get("id")): node for node in nodes_list}
        edges_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in snapshot.get("edges", []):
            edges_by_source[str(edge.get("source_node_id"))].append(edge)
        trigger = next((node for node in nodes.values() if node.get("node_type") == AutomationNodeType.TRIGGER_MESSAGE), None)
        if trigger is None or str((trigger.get("config") or {}).get("channel_connection_id")) != str(conversation.channel_connection_id):
            raise ValueError("inbound trigger channel no longer matches the conversation")
        current_id = str(execution.resume_node_id) if execution.resume_node_id else str(trigger["id"])
        visited: set[str] = set()
        while current_id:
            owned = db.query(AutomationExecution).filter_by(id=execution_id, tenant_id=tenant_id,
                status=AutomationExecutionStatus.RUNNING, worker_id=worker_id).with_for_update().first()
            if owned is None:
                db.rollback()
                return False
            execution = owned
            if (execution.run_started_at and (utcnow() - execution.run_started_at).total_seconds() >= settings.automation_execution_timeout_seconds):
                raise ValueError("execution exceeded the configured duration limit")
            if execution.attempt_count > execution.max_attempts:
                raise ValueError("execution exceeded the configured retry limit")
            if execution.step_count >= settings.automation_max_steps:
                raise ValueError("execution exceeded the configured step limit")
            if current_id in visited or current_id not in nodes:
                raise ValueError("flow is cyclic or references a missing step")
            visited.add(current_id)
            node = nodes[current_id]
            now = utcnow()
            execution.current_node_id = uuid.UUID(current_id)
            execution.resume_node_id = uuid.UUID(current_id)
            execution.claimed_at = now
            execution.step_count += 1
            db.commit()
            branch: str | None = None
            if node["node_type"] == AutomationNodeType.TRIGGER_MESSAGE:
                summary, level, details = "Inbound WhatsApp message trigger matched.", "info", None
            elif node["node_type"] in (AutomationNodeType.MESSAGE_CONTAINS, AutomationNodeType.BUSINESS_HOURS):
                config = node.get("config") or {}
                matched = _condition_matches(node["node_type"], config, trigger_message.text or "", now)
                branch = "true" if matched else "false"
                summary = f"{node['node_type']} condition {'matched' if matched else 'did not match'}."
                level, details = "info", {"matched": matched, "branch": branch}
            elif node["node_type"] == AutomationNodeType.DELAY:
                config = node.get("config") or {}
                duration = int(config["duration"])
                unit = config["unit"]
                seconds = duration * {"seconds": 1, "minutes": 60, "hours": 3600}[unit]
                next_id = _next_node(edges_by_source, current_id, None)
                execution.resume_node_id = uuid.UUID(next_id) if next_id else None
                execution.next_retry_at = now + timedelta(seconds=seconds)
                execution.status = AutomationExecutionStatus.QUEUED if next_id else AutomationExecutionStatus.COMPLETED
                execution.worker_id = None
                execution.claimed_at = None
                execution.current_node_id = uuid.UUID(current_id)
                execution.completed_at = None if next_id else now
                db.commit()
                _log(db, execution.id, tenant_id, uuid.UUID(current_id), "info", f"Execution delayed for {duration} {unit}." if next_id else "Delay was the final step; execution completed.")
                return True
            else:
                summary = _execute_action(db, execution, automation, actor, conversation, node)
                level, details = "success", None
            next_id = _next_node(edges_by_source, current_id, branch)
            execution = db.query(AutomationExecution).filter_by(id=execution_id, tenant_id=tenant_id,
                status=AutomationExecutionStatus.RUNNING, worker_id=worker_id).with_for_update().first()
            if execution is None:
                db.rollback()
                return False
            execution.resume_node_id = uuid.UUID(next_id) if next_id else None
            execution.claimed_at = utcnow()
            db.commit()
            _log(db, execution.id, tenant_id, uuid.UUID(current_id), level, summary, details)
            current_id = next_id
        execution = db.query(AutomationExecution).filter_by(id=execution_id, tenant_id=tenant_id,
            status=AutomationExecutionStatus.RUNNING, worker_id=worker_id).with_for_update().first()
        if execution is None:
            db.rollback()
            return False
        execution.status = AutomationExecutionStatus.COMPLETED
        execution.completed_at = utcnow()
        execution.error_summary = None
        execution.last_error_type = None
        execution.next_retry_at = None
        execution.worker_id = None
        execution.claimed_at = None
        db.commit()
        _log(db, execution_id, tenant_id, None, "success", "Execution completed.")
        return True
    except Exception as exc:  # isolate failures and preserve durable retry state
        _record_failure(db, execution_id, exc, worker_id)
        return True


def process_pending_executions(db: Session, limit: int = 50, worker_id: str = "automation-worker") -> dict[str, int]:
    _worker_heartbeat(db, worker_id, 0)
    now = utcnow()
    stale_before = now - timedelta(seconds=settings.automation_stale_claim_seconds)
    ids = db.scalars(select(AutomationExecution.id).where(or_(
        (AutomationExecution.status == AutomationExecutionStatus.QUEUED) & or_(AutomationExecution.next_retry_at.is_(None), AutomationExecution.next_retry_at <= now),
        (AutomationExecution.status == AutomationExecutionStatus.RETRYING) & or_(AutomationExecution.next_retry_at.is_(None), AutomationExecution.next_retry_at <= now),
        (AutomationExecution.status == AutomationExecutionStatus.RUNNING) & or_(AutomationExecution.claimed_at < stale_before, AutomationExecution.claimed_at.is_(None)),
    )).order_by(AutomationExecution.created_at, AutomationExecution.id).limit(limit)).all()
    db.rollback()
    counts = {"processed": 0, "skipped": 0}
    for execution_id in ids:
        try:
            if process_execution(db, execution_id, worker_id):
                counts["processed"] += 1
                _worker_heartbeat(db, worker_id, 1)
            else:
                counts["skipped"] += 1
                _worker_heartbeat(db, worker_id, 0)
        except Exception as exc:
            db.rollback()
            counts["skipped"] += 1
            logger.error("automation_execution_worker_error", extra={"execution_id": str(execution_id), "worker_id": worker_id, "error_type": type(exc).__name__})
            _worker_heartbeat(db, worker_id, 0)
    return counts
