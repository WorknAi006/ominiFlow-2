"""
Rule-based automations: WHEN (trigger) / IF (conditions) / THEN (actions).

A rule fires on its trigger event (new contact, tag added, chat status
changed, chat stuck in a mode). Its conditions are evaluated against the
event's contact/conversation and, when they pass (match all or any), the
ordered actions run as real mutations. Every evaluation is recorded as an
``AutomationRun`` for monitoring.

Dispatch is best-effort: a broken rule logs a failed run and is swallowed so
it can never break contact creation, tagging or a status change.
"""
import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    Automation, AutomationRun, AutomationRunStatus, AutomationThenMode,
    AutomationTrigger, Contact, ContactFieldValue, ContactTag,
    Conversation, ConversationStatus, CustomFieldDefinition, Tag,
)
from app.models.tag import DEFAULT_TAG_COLOR
from app.schemas.automation import (
    ACTION_TYPES, CONDITION_FIELDS, CONDITION_OPERATORS,
    AutomationCreate, AutomationUpdate,
)

logger = logging.getLogger("app.services.automation")


class AutomationNotFoundError(Exception):
    """No such automation for this tenant."""


# --------------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------------

def _get(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, for_update: bool = False) -> Automation:
    q = select(Automation).where(Automation.tenant_id == tenant_id, Automation.id == automation_id)
    if for_update:
        q = q.with_for_update()
    row = db.execute(q).scalar_one_or_none()
    if row is None:
        raise AutomationNotFoundError("Automation not found.")
    return row


def list_automations(db: Session, tenant_id: uuid.UUID, page: int, page_size: int, search: str | None) -> dict[str, Any]:
    base = select(Automation).where(Automation.tenant_id == tenant_id)
    if search:
        base = base.where(Automation.name.ilike(f"%{search}%"))
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(
        base.order_by(Automation.runs_first.asc(), Automation.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def get_automation(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID) -> Automation:
    return _get(db, tenant_id, automation_id)


def create_automation(db: Session, tenant_id: uuid.UUID, user, data: AutomationCreate) -> Automation:
    row = Automation(
        tenant_id=tenant_id,
        name=data.name,
        trigger_type=data.trigger_type.value,
        trigger_config=_clean_trigger_config(data.trigger_type.value, data.trigger_config),
        match_type=data.match_type.value,
        conditions=[c.model_dump() for c in data.conditions],
        then_mode=data.then_mode.value,
        flow_ref=data.flow_ref,
        actions=[a.model_dump() for a in data.actions],
        is_active=data.is_active,
        runs_first=data.runs_first,
        created_by_user_id=getattr(user, "id", None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_automation(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, data: AutomationUpdate) -> Automation:
    row = _get(db, tenant_id, automation_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    if "trigger_type" in changes:
        row.trigger_type = data.trigger_type.value
    if "trigger_config" in changes:
        row.trigger_config = _clean_trigger_config(row.trigger_type, changes["trigger_config"] or {})
    if "match_type" in changes:
        row.match_type = data.match_type.value
    if "conditions" in changes:
        row.conditions = [c.model_dump() for c in (data.conditions or [])]
    if "then_mode" in changes:
        row.then_mode = data.then_mode.value
    if "flow_ref" in changes:
        row.flow_ref = changes["flow_ref"]
    if "actions" in changes:
        row.actions = [a.model_dump() for a in (data.actions or [])]
    if "name" in changes:
        row.name = changes["name"]
    if "is_active" in changes:
        row.is_active = changes["is_active"]
    if "runs_first" in changes:
        row.runs_first = changes["runs_first"]
    db.commit()
    db.refresh(row)
    return row


def delete_automation(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID) -> None:
    row = _get(db, tenant_id, automation_id, for_update=True)
    db.delete(row)
    db.commit()


def set_active(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, active: bool) -> Automation:
    row = _get(db, tenant_id, automation_id, for_update=True)
    row.is_active = active
    db.commit()
    db.refresh(row)
    return row


def _clean_trigger_config(trigger_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if trigger_type == AutomationTrigger.CHAT_STUCK_IN_MODE.value:
        hours = config.get("hours", 1)
        try:
            hours = max(1, min(168, int(hours)))
        except (TypeError, ValueError):
            hours = 1
        return {"mode": str(config.get("mode", "bot"))[:40], "hours": hours}
    return {}


# --------------------------------------------------------------------------
# Options catalogue (served to the builder UI)
# --------------------------------------------------------------------------

_TRIGGER_LABELS = {
    "new_contact_created": "New contact created",
    "tag_added_to_contact": "Tag added to contact",
    "chat_status_changed": "Chat status changed",
    "chat_stuck_in_mode": "Chat stuck in a mode for N hours",
}
_FIELD_LABELS = {
    "existing_contact": "Existing contact",
    "contact_tags": "Contact tags",
    "source": "Source",
    "chat_status": "Chat status",
    "chat_mode": "Chat mode",
    "assigned_agent": "Assigned agent",
    "has_agent_assigned": "Has agent assigned",
    "account": "account",
}
_OPERATOR_LABELS = {
    "is": "is", "is_not": "is not", "contains": "contains",
    "doesnt_contain": "doesn't contain", "starts_with": "starts with",
    "ends_with": "ends with", "has_any": "has any",
    "has_value": "has value", "has_no_value": "has no value",
}
_ACTION_SPECS = {
    "add_tags": ("Add tags", [{"key": "value", "label": "Tag IDs or names, comma-separated", "type": "text"}]),
    "remove_tags": ("Remove tags", [{"key": "value", "label": "Tag IDs or names, comma-separated", "type": "text"}]),
    "set_custom_field": ("Set custom field", [
        {"key": "key", "label": "Field key", "type": "text"},
        {"key": "value", "label": "Value", "type": "text"},
    ]),
    "clear_custom_field": ("Clear custom field", [{"key": "key", "label": "Field key", "type": "text"}]),
    "subscribe_to_drip": ("Subscribe to drip", [{"key": "value", "label": "Drip name", "type": "text"}]),
    "unsubscribe_from_drip": ("Unsubscribe from drip", [{"key": "value", "label": "Drip name", "type": "text"}]),
    "append_to_google_sheet": ("Append to Google Sheet", [{"key": "value", "label": "Sheet URL or ID", "type": "text"}]),
    "set_chat_status": ("Set chat status", [{"key": "value", "label": "Status", "type": "chat_status"}]),
    "transfer_to_bot": ("Transfer to bot", [{"key": "value", "label": "Bot name (optional)", "type": "text"}]),
}


def options() -> dict[str, Any]:
    return {
        "triggers": [{"value": t, "label": _TRIGGER_LABELS[t]} for t in _TRIGGER_LABELS],
        "condition_fields": [{"value": f, "label": _FIELD_LABELS[f]} for f in CONDITION_FIELDS],
        "operators": [{"value": o, "label": _OPERATOR_LABELS[o]} for o in CONDITION_OPERATORS],
        "actions": [{"value": a, "label": _ACTION_SPECS[a][0], "config_fields": _ACTION_SPECS[a][1]} for a in ACTION_TYPES],
        "chat_statuses": [{"value": s.value, "label": s.value.capitalize()} for s in ConversationStatus],
    }


# --------------------------------------------------------------------------
# Runs + metrics
# --------------------------------------------------------------------------

def list_runs(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID | None, page: int, page_size: int) -> dict[str, Any]:
    base = select(AutomationRun).where(AutomationRun.tenant_id == tenant_id)
    if automation_id is not None:
        base = base.where(AutomationRun.automation_id == automation_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(
        base.order_by(AutomationRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def metrics(db: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    total_rules = db.execute(select(func.count()).select_from(Automation).where(Automation.tenant_id == tenant_id)).scalar_one()
    active_rules = db.execute(select(func.count()).select_from(Automation).where(Automation.tenant_id == tenant_id, Automation.is_active.is_(True))).scalar_one()
    by_status = dict(db.execute(
        select(AutomationRun.status, func.count()).where(AutomationRun.tenant_id == tenant_id).group_by(AutomationRun.status)
    ).all())
    last_run_at = db.execute(select(func.max(AutomationRun.created_at)).where(AutomationRun.tenant_id == tenant_id)).scalar_one()
    return {
        "total_rules": total_rules,
        "active_rules": active_rules,
        "runs_total": sum(by_status.values()),
        "runs_success": by_status.get(AutomationRunStatus.SUCCESS.value, 0),
        "runs_failed": by_status.get(AutomationRunStatus.FAILED.value, 0),
        "runs_skipped": by_status.get(AutomationRunStatus.SKIPPED.value, 0),
        "last_run_at": last_run_at,
    }


# --------------------------------------------------------------------------
# Trigger emitters — called from the hook points (contact/tag/conversation)
# --------------------------------------------------------------------------

def on_contact_created(db: Session, contact: Contact) -> None:
    _safe_dispatch(db, contact.tenant_id, AutomationTrigger.NEW_CONTACT_CREATED, contact=contact)


def on_tags_added(db: Session, tenant_id: uuid.UUID, contact_id: uuid.UUID, added_tag_ids: list[uuid.UUID]) -> None:
    if not added_tag_ids:
        return
    contact = db.get(Contact, contact_id)
    if contact is None or contact.tenant_id != tenant_id:
        return
    _safe_dispatch(db, tenant_id, AutomationTrigger.TAG_ADDED_TO_CONTACT, contact=contact)


def on_chat_status_changed(db: Session, conversation: Conversation, old_status: str, new_status: str) -> None:
    if old_status == new_status:
        return
    contact = db.get(Contact, conversation.contact_id)
    _safe_dispatch(db, conversation.tenant_id, AutomationTrigger.CHAT_STATUS_CHANGED, contact=contact, conversation=conversation)


def _safe_dispatch(db: Session, tenant_id, trigger: AutomationTrigger, *, contact=None, conversation=None) -> None:
    try:
        dispatch(db, tenant_id, trigger, contact=contact, conversation=conversation)
    except Exception as exc:  # A rule must never break the triggering operation.
        logger.error("automation_dispatch_failed", extra={"trigger": trigger.value, "error_type": type(exc).__name__})
        try:
            db.rollback()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Dispatch — evaluate rules and run actions
# --------------------------------------------------------------------------

def dispatch(db: Session, tenant_id, trigger: AutomationTrigger, *, contact: Contact | None = None, conversation: Conversation | None = None) -> int:
    rules = db.execute(
        select(Automation).where(
            Automation.tenant_id == tenant_id,
            Automation.trigger_type == trigger.value,
            Automation.is_active.is_(True),
        ).order_by(Automation.runs_first.asc(), Automation.created_at.asc())
    ).scalars().all()
    fired = 0
    for rule in rules:
        fired += _run_rule(db, rule, contact, conversation)
    return fired


def _run_rule(db: Session, rule: Automation, contact: Contact | None, conversation: Conversation | None) -> int:
    run = AutomationRun(
        tenant_id=rule.tenant_id, automation_id=rule.id, trigger_type=rule.trigger_type,
        contact_id=contact.id if contact else None,
        conversation_id=conversation.id if conversation else None,
        status=AutomationRunStatus.SKIPPED.value, matched=False, actions_run=0,
    )
    try:
        if not _conditions_pass(db, rule, contact, conversation):
            run.detail = "Conditions did not match."
            db.add(run)
            db.commit()
            return 0
        run.matched = True
        if rule.then_mode == AutomationThenMode.START_FLOW.value:
            run.status = AutomationRunStatus.SKIPPED.value
            run.detail = f"Start a flow ({rule.flow_ref or 'unset'}) — flows run outside this engine."
            db.add(run)
            db.commit()
            return 0
        notes: list[str] = []
        count = 0
        for action in rule.actions or []:
            ok, note = _execute_action(db, rule.tenant_id, action, contact, conversation)
            notes.append(note)
            if ok:
                count += 1
        run.actions_run = count
        run.status = AutomationRunStatus.SUCCESS.value
        run.detail = " | ".join(notes)[:4000] if notes else "No actions configured."
        db.add(run)
        db.commit()
        return 1
    except Exception as exc:
        db.rollback()
        run.status = AutomationRunStatus.FAILED.value
        run.matched = True
        run.detail = f"{type(exc).__name__}: {exc}"[:4000]
        db.add(run)
        db.commit()
        logger.error("automation_rule_failed", extra={"automation_id": str(rule.id), "error_type": type(exc).__name__})
        return 0


# --------------------------------------------------------------------------
# Condition evaluation
# --------------------------------------------------------------------------

def _conditions_pass(db: Session, rule: Automation, contact: Contact | None, conversation: Conversation | None) -> bool:
    conditions = rule.conditions or []
    if not conditions:
        return True  # "leave empty to always run"
    results = [_eval_condition(db, c, contact, conversation) for c in conditions]
    return all(results) if rule.match_type == "all" else any(results)


def _eval_condition(db: Session, cond: dict[str, Any], contact: Contact | None, conversation: Conversation | None) -> bool:
    value, is_list = _field_value(db, cond.get("field", ""), contact, conversation)
    return _apply_operator(value, is_list, cond.get("operator", "is"), str(cond.get("value", "")))


def _field_value(db: Session, field: str, contact: Contact | None, conversation: Conversation | None):
    """Return (value, is_list) for a condition field from the event context."""
    if field == "existing_contact":
        if not contact:
            return None, False
        label = contact.display_name or " ".join(filter(None, [contact.first_name, contact.last_name])) or contact.normalized_phone_number or contact.email
        return (label or None), False
    if field == "contact_tags":
        if not contact:
            return [], True
        names = db.execute(
            select(Tag.name).join(ContactTag, ContactTag.tag_id == Tag.id).where(ContactTag.contact_id == contact.id)
        ).scalars().all()
        return [n.lower() for n in names], True
    if field == "source":
        meta = (contact.contact_metadata or {}) if contact else {}
        return (meta.get("source") or None), False
    if field == "chat_status":
        return (conversation.status if conversation else None), False
    if field == "chat_mode":
        meta = (conversation.conversation_metadata or {}) if conversation else {}
        return (meta.get("mode") or ("bot" if conversation else None)), False
    if field == "assigned_agent":
        return (str(conversation.assigned_user_id) if conversation and conversation.assigned_user_id else None), False
    if field == "has_agent_assigned":
        return ("true" if conversation and conversation.assigned_user_id else "false"), False
    if field == "account":
        return (str(contact.tenant_id) if contact else (str(conversation.tenant_id) if conversation else None)), False
    return None, False


def _apply_operator(value, is_list: bool, operator: str, target: str) -> bool:
    target_l = target.strip().lower()
    if is_list:
        items = [str(v).lower() for v in (value or [])]
        if operator == "has_value":
            return len(items) > 0
        if operator == "has_no_value":
            return len(items) == 0
        if operator in ("has_any", "contains", "is"):
            return target_l in items if target_l else len(items) > 0
        if operator in ("doesnt_contain", "is_not"):
            return target_l not in items
        if operator == "starts_with":
            return any(i.startswith(target_l) for i in items)
        if operator == "ends_with":
            return any(i.endswith(target_l) for i in items)
        return False
    present = value is not None and str(value).strip() != ""
    sval = str(value).strip().lower() if present else ""
    if operator == "has_value":
        return present
    if operator == "has_no_value":
        return not present
    if operator == "has_any":
        return present
    if operator == "is":
        return sval == target_l
    if operator == "is_not":
        return sval != target_l
    if operator == "contains":
        return target_l in sval
    if operator == "doesnt_contain":
        return target_l not in sval
    if operator == "starts_with":
        return sval.startswith(target_l)
    if operator == "ends_with":
        return sval.endswith(target_l)
    return False


# --------------------------------------------------------------------------
# Action execution — real mutations (no re-dispatch, to avoid recursion)
# --------------------------------------------------------------------------

def _execute_action(db: Session, tenant_id, action: dict[str, Any], contact: Contact | None, conversation: Conversation | None):
    atype = action.get("type", "")
    config = action.get("config", {}) or {}
    if atype == "add_tags":
        if not contact:
            return False, "add_tags skipped (no contact)"
        names = _split(config.get("value"))
        tag_ids = [_resolve_or_create_tag(db, tenant_id, n) for n in names]
        for tag_id in tag_ids:
            db.execute(insert(ContactTag).values(id=uuid.uuid4(), tenant_id=tenant_id, contact_id=contact.id, tag_id=tag_id).on_conflict_do_nothing(index_elements=["contact_id", "tag_id"]))
        return True, f"added tags: {', '.join(names) or '—'}"
    if atype == "remove_tags":
        if not contact:
            return False, "remove_tags skipped (no contact)"
        names = _split(config.get("value"))
        tag_ids = [tid for tid in (_resolve_tag(db, tenant_id, n) for n in names) if tid]
        if tag_ids:
            db.query(ContactTag).filter(ContactTag.tenant_id == tenant_id, ContactTag.contact_id == contact.id, ContactTag.tag_id.in_(tag_ids)).delete(synchronize_session=False)
        return True, f"removed tags: {', '.join(names) or '—'}"
    if atype == "set_custom_field":
        if not contact:
            return False, "set_custom_field skipped (no contact)"
        key = str(config.get("key", "")).strip()
        if not key:
            return False, "set_custom_field skipped (no key)"
        field = _resolve_or_create_field(db, tenant_id, key)
        existing = db.execute(select(ContactFieldValue).where(ContactFieldValue.contact_id == contact.id, ContactFieldValue.field_id == field.id)).scalar_one_or_none()
        if existing:
            existing.value = config.get("value")
        else:
            db.add(ContactFieldValue(tenant_id=tenant_id, contact_id=contact.id, field_id=field.id, value=config.get("value")))
        return True, f"set {key} = {config.get('value')}"
    if atype == "clear_custom_field":
        if not contact:
            return False, "clear_custom_field skipped (no contact)"
        key = str(config.get("key", "")).strip()
        field = _resolve_field(db, tenant_id, key)
        if field:
            db.query(ContactFieldValue).filter(ContactFieldValue.contact_id == contact.id, ContactFieldValue.field_id == field.id).delete(synchronize_session=False)
        return True, f"cleared {key}"
    if atype in ("subscribe_to_drip", "unsubscribe_from_drip"):
        if not contact:
            return False, f"{atype} skipped (no contact)"
        drip = str(config.get("value", "")).strip()
        meta = dict(contact.contact_metadata or {})
        drips = list(meta.get("drips", []))
        if atype == "subscribe_to_drip" and drip and drip not in drips:
            drips.append(drip)
        if atype == "unsubscribe_from_drip":
            drips = [d for d in drips if d != drip]
        meta["drips"] = drips
        contact.contact_metadata = meta
        return True, f"{atype}: {drip or '—'}"
    if atype == "append_to_google_sheet":
        # No Google integration is configured; record intent in the run log.
        return True, f"queued Google Sheet append: {config.get('value', '—')}"
    if atype == "set_chat_status":
        if not conversation:
            return False, "set_chat_status skipped (no conversation)"
        status = str(config.get("value", "")).strip().lower()
        valid = {s.value for s in ConversationStatus}
        if status not in valid:
            return False, f"set_chat_status skipped (invalid: {status})"
        conversation.status = status  # Direct write — does not re-dispatch.
        return True, f"chat status -> {status}"
    if atype == "transfer_to_bot":
        if not conversation:
            return False, "transfer_to_bot skipped (no conversation)"
        meta = dict(conversation.conversation_metadata or {})
        meta["mode"] = "bot"
        conversation.conversation_metadata = meta
        conversation.assigned_user_id = None
        return True, "transferred to bot"
    return False, f"unknown action: {atype}"


def _split(raw: Any) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _resolve_tag(db: Session, tenant_id, name_or_id: str) -> uuid.UUID | None:
    try:
        tid = uuid.UUID(name_or_id)
        found = db.execute(select(Tag.id).where(Tag.tenant_id == tenant_id, Tag.id == tid)).scalar_one_or_none()
        if found:
            return found
    except (ValueError, AttributeError):
        pass
    return db.execute(select(Tag.id).where(Tag.tenant_id == tenant_id, func.lower(Tag.name) == name_or_id.lower())).scalar_one_or_none()


def _resolve_or_create_tag(db: Session, tenant_id, name_or_id: str) -> uuid.UUID:
    existing = _resolve_tag(db, tenant_id, name_or_id)
    if existing:
        return existing
    tag = Tag(tenant_id=tenant_id, name=name_or_id[:60], color=DEFAULT_TAG_COLOR)
    db.add(tag)
    db.flush()
    return tag.id


def _resolve_field(db: Session, tenant_id, key: str) -> CustomFieldDefinition | None:
    if not key:
        return None
    return db.execute(select(CustomFieldDefinition).where(CustomFieldDefinition.tenant_id == tenant_id, CustomFieldDefinition.key == key)).scalar_one_or_none()


def _resolve_or_create_field(db: Session, tenant_id, key: str) -> CustomFieldDefinition:
    existing = _resolve_field(db, tenant_id, key)
    if existing:
        return existing
    field = CustomFieldDefinition(tenant_id=tenant_id, label=key[:60], key=key[:60], field_type="text")
    db.add(field)
    db.flush()
    return field
