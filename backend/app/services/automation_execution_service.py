"""
Time-based automation trigger: "chat stuck in a mode for N hours".

The other triggers (new contact, tag added, chat status changed) fire inline
from their service hooks. This one has no inbound event, so a worker scans
periodically for conversations that have sat idle in a mode past the rule's
threshold and runs the matching rules once per idle window.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Automation, AutomationRun, AutomationTrigger, Contact, Conversation,
)
from app.models.conversation import ACTIVE_CONVERSATION_STATUSES
from app.services import automation_service

logger = logging.getLogger("app.services.automation_execution")


def run_stuck_scan(db: Session, limit: int = 200) -> dict[str, int]:
    """Fire chat_stuck_in_mode rules for conversations idle past their threshold."""
    now = datetime.now(timezone.utc)
    rules = db.execute(
        select(Automation).where(
            Automation.trigger_type == AutomationTrigger.CHAT_STUCK_IN_MODE.value,
            Automation.is_active.is_(True),
        )
    ).scalars().all()

    scanned = 0
    fired = 0
    for rule in rules:
        cfg = rule.trigger_config or {}
        mode = str(cfg.get("mode", "bot"))
        hours = int(cfg.get("hours", 1) or 1)
        cutoff = now - timedelta(hours=hours)
        active = [s.value for s in ACTIVE_CONVERSATION_STATUSES]
        convos = db.execute(
            select(Conversation).where(
                Conversation.tenant_id == rule.tenant_id,
                Conversation.status.in_(active),
                Conversation.last_message_at.isnot(None),
                Conversation.last_message_at < cutoff,
            ).order_by(Conversation.last_message_at.asc()).limit(limit)
        ).scalars().all()
        for convo in convos:
            scanned += 1
            convo_mode = (convo.conversation_metadata or {}).get("mode") or "bot"
            if convo_mode != mode:
                continue
            if _already_fired(db, rule.id, convo.id, convo.last_message_at):
                continue
            contact = db.get(Contact, convo.contact_id)
            try:
                fired += automation_service._run_rule(db, rule, contact, convo)
            except Exception as exc:
                db.rollback()
                logger.error("stuck_scan_rule_failed", extra={"automation_id": str(rule.id), "error_type": type(exc).__name__})
    return {"processed": fired, "scanned": scanned, "rules": len(rules)}


def _already_fired(db: Session, automation_id: uuid.UUID, conversation_id: uuid.UUID, since: datetime | None) -> bool:
    """True if this rule already ran for this conversation in the current idle window."""
    q = select(AutomationRun.id).where(
        AutomationRun.automation_id == automation_id,
        AutomationRun.conversation_id == conversation_id,
    )
    if since is not None:
        q = q.where(AutomationRun.created_at >= since)
    return db.execute(q.limit(1)).scalar_one_or_none() is not None
