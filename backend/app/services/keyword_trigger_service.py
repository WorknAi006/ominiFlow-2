"""
Keyword → flow triggering on inbound messages.

Called once per newly-stored inbound message from the channel-neutral
``inbound_event_service`` (so it covers WhatsApp, Facebook Messenger,
Instagram and Web Chat identically). On a match it records a durable
``KeywordTrigger`` inside the same transaction the caller commits.

Idempotency: the unique (tenant_id, message_id) constraint — plus the
caller's "already stored" short-circuit — guarantees a replayed webhook or
re-processed message never triggers twice.

Match policy for overlapping keywords: the oldest active keyword that
matches wins (deterministic first-match by created_at ascending). Exactly
one flow is triggered per message.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact, Conversation, Keyword, KeywordTrigger
from app.models.keyword_trigger import KeywordTriggerAction, KeywordTriggerStatus
from app.models.message import Message, MessageDirection

logger = logging.getLogger("app.services.keyword_trigger")


def _normalize(text: str) -> str:
    """Collapse whitespace and lower-case for case/space-insensitive matching."""
    return " ".join(text.split()).strip().lower()


def text_matches(message_text: str, keyword_text: str, match_type: str) -> bool:
    m = _normalize(message_text)
    k = _normalize(keyword_text)
    if not k or not m:
        return False
    if match_type == "exact":
        return m == k
    if match_type == "contains":
        return k in m
    if match_type == "starts_with":
        return m.startswith(k)
    if match_type == "ends_with":
        return m.endswith(k)
    return False


def find_matching_keyword(session: Session, tenant_id: uuid.UUID, text: str) -> Keyword | None:
    """First active keyword (oldest first) whose rule matches the text."""
    keywords = session.execute(
        select(Keyword)
        .where(Keyword.tenant_id == tenant_id, Keyword.is_active.is_(True))
        .order_by(Keyword.created_at.asc(), Keyword.id.asc())
    ).scalars().all()
    for kw in keywords:
        if text_matches(text, kw.keyword_text, kw.match_type):
            return kw
    return None


def handle_inbound(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    channel_type: str,
    conversation: Conversation,
    contact: Contact,
    message: Message,
) -> KeywordTrigger | None:
    """
    Evaluate keyword rules for one inbound message and record the trigger.

    Runs inside the caller's inbound transaction (the caller commits). Never
    raises into the inbound path — a keyword fault must not drop a customer
    message.
    """
    try:
        text = (message.text or "").strip()
        if not text or message.direction != MessageDirection.INBOUND.value:
            return None

        # Priority: an in-progress flow consumes this message. A waiting-reply
        # session captures the reply (the worker resumes it); any other live
        # session means a flow is already running, so we do not keyword-match.
        from app.services import flow_engine
        active = flow_engine.active_session_for(session, tenant_id, conversation.id)
        if active is not None:
            if active.status == "waiting" and active.wait_kind == "reply":
                flow_engine.capture_reply(session, active, text)
            return None

        # Idempotency guard (belt-and-braces with the unique constraint).
        existing = session.execute(
            select(KeywordTrigger).where(
                KeywordTrigger.tenant_id == tenant_id,
                KeywordTrigger.message_id == message.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        keyword = find_matching_keyword(session, tenant_id, text)
        if keyword is None:
            return None

        if keyword.flow_id is not None:
            action, detail = KeywordTriggerAction.RUN_FLOW, f"Triggered flow {keyword.flow_id}"
            status = KeywordTriggerStatus.MATCHED
        elif keyword.reply_text:
            action, detail = KeywordTriggerAction.SEND_TEXT, "Queued reply text"
            status = KeywordTriggerStatus.MATCHED
        else:
            action, detail = KeywordTriggerAction.NONE, "Matched but no flow or reply configured"
            status = KeywordTriggerStatus.SKIPPED

        trigger = KeywordTrigger(
            tenant_id=tenant_id,
            keyword_id=keyword.id,
            flow_id=keyword.flow_id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            message_id=message.id,
            channel_type=channel_type,
            action=action.value,
            status=status.value,
            detail=detail,
        )
        session.add(trigger)
        session.flush()
        logger.info(
            "keyword_triggered",
            extra={"tenant_id": str(tenant_id), "keyword_id": str(keyword.id), "flow_id": str(keyword.flow_id) if keyword.flow_id else None, "action": action.value},
        )
        return trigger
    except Exception as exc:  # Never break inbound persistence over a keyword fault.
        logger.error("keyword_trigger_failed", extra={"error_type": type(exc).__name__})
        return None
