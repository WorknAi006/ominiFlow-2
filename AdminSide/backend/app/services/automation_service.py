"""Tenant-scoped automation definitions and safe flow validation."""
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

from app.core.config import settings
from app.models import ChannelConnection, ChannelStatus, ChannelType, ConversationStatus, MessageTemplate, TenantMembership, User
from app.models.automation import (
    Automation, AutomationEdge, AutomationExecution, AutomationExecutionLog,
    AutomationExecutionStatus, AutomationNode, AutomationNodeType, AutomationStatus, AutomationTrigger,
)
from app.schemas.automation import (
    AutomationCreate, AutomationEdgeInput, AutomationFlowSave, AutomationNodeCreate,
    AutomationNodeUpdate, AutomationUpdate, ValidationIssue,
)
from app.services import template_service
from app.services.template_service import is_usable
from app.services.automation_execution_service import worker_health
from app.schemas.message import TemplateMessageCreate


class AutomationError(Exception):
    pass


class AutomationNotFoundError(AutomationError):
    pass


class AutomationConflictError(AutomationError):
    pass


class AutomationFlowLockedError(AutomationError):
    pass


class AutomationInvalidFlowError(AutomationError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("Flow validation failed.")


def get_model(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, *, for_update: bool = False) -> Automation:
    query = db.query(Automation).filter(Automation.id == automation_id, Automation.tenant_id == tenant_id)
    if for_update:
        query = query.with_for_update()
    value = query.first()
    if value is None:
        raise AutomationNotFoundError("Automation not found.")
    return value


def _editable(value: Automation) -> None:
    if value.status == AutomationStatus.ACTIVE:
        raise AutomationFlowLockedError("Pause this automation before changing its flow.")
    if value.status == AutomationStatus.ARCHIVED:
        raise AutomationFlowLockedError("Archived automations cannot be changed.")


def list_automations(db: Session, tenant_id: uuid.UUID, page: int, page_size: int, status: str | None, search: str | None):
    query = db.query(Automation).filter(Automation.tenant_id == tenant_id)
    if status:
        query = query.filter(Automation.status == status)
    if search:
        escaped = search.replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        query = query.filter(or_(Automation.name.ilike(pattern, escape="\\"), Automation.description.ilike(pattern, escape="\\")))
    total = query.count()
    items = query.order_by(Automation.updated_at.desc(), Automation.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _nodes_edges(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID):
    nodes = db.query(AutomationNode).filter_by(tenant_id=tenant_id, automation_id=automation_id).order_by(AutomationNode.sort_order, AutomationNode.id).all()
    edges = db.query(AutomationEdge).filter_by(tenant_id=tenant_id, automation_id=automation_id).order_by(AutomationEdge.id).all()
    return nodes, edges


def get_detail(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID):
    automation = get_model(db, tenant_id, automation_id)
    nodes, edges = _nodes_edges(db, tenant_id, automation_id)
    return {"automation": automation, "nodes": nodes, "edges": edges}


def create_automation(db: Session, tenant_id: uuid.UUID, actor: User, data: AutomationCreate) -> Automation:
    automation = Automation(tenant_id=tenant_id, name=data.name, description=data.description, trigger_type=data.trigger_type, created_by_user_id=actor.id)
    db.add(automation)
    db.flush()
    db.add(AutomationNode(
        tenant_id=tenant_id, automation_id=automation.id, node_type=AutomationNodeType.TRIGGER_MESSAGE,
        name="Inbound WhatsApp Message", config={}, sort_order=0,
    ))
    db.commit()
    db.refresh(automation)
    return automation


def update_automation(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, data: AutomationUpdate) -> Automation:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    _editable(automation)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(automation, key, value)
    db.commit()
    db.refresh(automation)
    return automation


def archive_automation(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID) -> Automation:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    automation.status = AutomationStatus.ARCHIVED
    db.commit()
    db.refresh(automation)
    return automation


def _node_config_issues(db: Session, tenant_id: uuid.UUID, nodes: list[AutomationNode], automation: Automation) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    trigger = next((n for n in nodes if n.node_type == AutomationNodeType.TRIGGER_MESSAGE), None)
    trigger_channel_id = (trigger.config or {}).get("channel_connection_id") if trigger else None
    channel = None
    if trigger_channel_id:
        try:
            channel_uuid = uuid.UUID(str(trigger_channel_id))
        except ValueError:
            channel_uuid = None
        if channel_uuid:
            # Any connected channel can trigger an inbound-message flow
            # (WhatsApp, Web Chat, ...); channel-specific action nodes still
            # validate their own requirements below.
            channel = db.query(ChannelConnection).filter(
                ChannelConnection.id == channel_uuid, ChannelConnection.tenant_id == tenant_id,
                ChannelConnection.is_deleted.is_(False),
                ChannelConnection.is_active.is_(True), ChannelConnection.status == ChannelStatus.CONNECTED,
            ).first()
    if trigger and not channel:
        issues.append(ValidationIssue(code="trigger_channel_required", message="Choose a connected channel for the inbound message trigger.", node_id=trigger.id))

    for node in nodes:
        config = node.config or {}
        if node.node_type == AutomationNodeType.MESSAGE_CONTAINS:
            value = config.get("value")
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                issues.append(ValidationIssue(code="condition_value_required", message="Message Contains needs a value up to 500 characters.", node_id=node.id))
            if "case_sensitive" in config and not isinstance(config["case_sensitive"], bool):
                issues.append(ValidationIssue(code="condition_case_invalid", message="Case sensitivity must be true or false.", node_id=node.id))
            operator = config.get("operator", "contains")
            if not isinstance(operator, str) or operator not in {"contains", "equals", "starts_with", "ends_with"}:
                issues.append(ValidationIssue(code="condition_operator_invalid", message="Choose a supported text comparison.", node_id=node.id))
        elif node.node_type == AutomationNodeType.SEND_TEXT:
            value = config.get("text")
            if not isinstance(value, str) or not value.strip() or len(value) > 4096:
                issues.append(ValidationIssue(code="send_text_required", message="Send Text needs a message from 1 to 4096 characters.", node_id=node.id))
        elif node.node_type == AutomationNodeType.SEND_TEMPLATE:
            try:
                template_id = uuid.UUID(str(config.get("template_id", "")))
            except ValueError:
                template_id = None
            template = db.query(MessageTemplate).filter(
                MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id,
                MessageTemplate.is_active.is_(True),
            ).first() if template_id else None
            if template is None or not is_usable(template):
                issues.append(ValidationIssue(code="template_invalid", message="Select an active, approved WhatsApp template from this workspace.", node_id=node.id))
            elif channel and template.channel_connection_id != channel.id:
                issues.append(ValidationIssue(code="template_channel_mismatch", message="The selected template must belong to the trigger channel.", node_id=node.id))
            elif template is not None:
                try:
                    send_data = TemplateMessageCreate(
                        type="template", template_name=template.name, language=template.language,
                        components=config.get("components", []),
                    )
                    template_service.build_send_components(template, send_data.components)
                except Exception:
                    issues.append(ValidationIssue(code="template_variables_invalid", message="Provide valid values for all required template variables.", node_id=node.id))
            if not isinstance(config.get("components", []), list):
                issues.append(ValidationIssue(code="template_variables_invalid", message="Template variable configuration is invalid.", node_id=node.id))
        elif node.node_type == AutomationNodeType.ASSIGN_CONVERSATION:
            try:
                user_id = uuid.UUID(str(config.get("user_id", "")))
            except ValueError:
                user_id = None
            member = db.query(TenantMembership.id).join(User, User.id == TenantMembership.user_id).filter(
                TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user_id,
                TenantMembership.status == "active", User.is_active.is_(True),
            ).first() if user_id else None
            if not member:
                issues.append(ValidationIssue(code="assignee_invalid", message="Select an active member of this workspace.", node_id=node.id))
        elif node.node_type == AutomationNodeType.CHANGE_CONVERSATION_STATUS:
            if not isinstance(config.get("status"), str) or config.get("status") not in {item.value for item in ConversationStatus}:
                issues.append(ValidationIssue(code="conversation_status_invalid", message="Choose a supported conversation status.", node_id=node.id))
        elif node.node_type == AutomationNodeType.DELAY:
            duration, unit = config.get("duration"), config.get("unit")
            if not isinstance(duration, int) or isinstance(duration, bool) or duration < 1 or duration > 720:
                issues.append(ValidationIssue(code="delay_duration_invalid", message="Delay must be between 1 and 720 units.", node_id=node.id))
            if not isinstance(unit, str) or unit not in {"seconds", "minutes", "hours"}:
                issues.append(ValidationIssue(code="delay_unit_invalid", message="Choose seconds, minutes, or hours.", node_id=node.id))
        elif node.node_type == AutomationNodeType.BUSINESS_HOURS:
            try:
                ZoneInfo(str(config.get("timezone", "")))
            except (ZoneInfoNotFoundError, ValueError):
                issues.append(ValidationIssue(code="business_timezone_invalid", message="Choose a valid IANA timezone.", node_id=node.id))
            days = config.get("working_days")
            if not isinstance(days, list) or not days or any(not isinstance(day, int) or isinstance(day, bool) or day < 0 or day > 6 for day in days) or len(set(days)) != len(days):
                issues.append(ValidationIssue(code="business_days_invalid", message="Select one or more unique working days.", node_id=node.id))
            try:
                start = datetime.strptime(str(config.get("start_time", "")), "%H:%M").time()
                end = datetime.strptime(str(config.get("end_time", "")), "%H:%M").time()
                if start == end:
                    raise ValueError
            except ValueError:
                issues.append(ValidationIssue(code="business_time_invalid", message="Set valid, different start and end times in 24-hour format.", node_id=node.id))
    return issues


def validate_flow(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID) -> list[ValidationIssue]:
    automation = get_model(db, tenant_id, automation_id)
    nodes, edges = _nodes_edges(db, tenant_id, automation_id)
    issues: list[ValidationIssue] = []
    if len(nodes) > settings.automation_max_nodes:
        issues.append(ValidationIssue(code="node_limit", message=f"A flow may contain at most {settings.automation_max_nodes} steps."))
    triggers = [node for node in nodes if node.node_type == AutomationNodeType.TRIGGER_MESSAGE]
    if len(triggers) != 1:
        issues.append(ValidationIssue(code="trigger_count", message="A valid flow must have exactly one trigger."))
    if not any(node.node_type in {
        AutomationNodeType.SEND_TEXT, AutomationNodeType.SEND_TEMPLATE,
        AutomationNodeType.ASSIGN_CONVERSATION, AutomationNodeType.CHANGE_CONVERSATION_STATUS,
    } for node in nodes):
        issues.append(ValidationIssue(code="action_required", message="Add at least one action."))
    issues.extend(_node_config_issues(db, tenant_id, nodes, automation))

    ids = {node.id for node in nodes}
    outgoing: dict[uuid.UUID, list[AutomationEdge]] = defaultdict(list)
    incoming: dict[uuid.UUID, list[AutomationEdge]] = defaultdict(list)
    for edge in edges:
        if edge.source_node_id not in ids or edge.target_node_id not in ids:
            issues.append(ValidationIssue(code="edge_invalid", message="Every connection must point to a node in this flow."))
            continue
        outgoing[edge.source_node_id].append(edge)
        incoming[edge.target_node_id].append(edge)
        source = next((node for node in nodes if node.id == edge.source_node_id), None)
        if edge.branch and (source is None or source.node_type not in (AutomationNodeType.MESSAGE_CONTAINS, AutomationNodeType.BUSINESS_HOURS)):
            issues.append(ValidationIssue(code="edge_branch_invalid", message="Only a condition can have true/false branches.", node_id=edge.source_node_id))
    for node_id, rows in outgoing.items():
        node = next((item for item in nodes if item.id == node_id), None)
        if node and node.node_type in (AutomationNodeType.MESSAGE_CONTAINS, AutomationNodeType.BUSINESS_HOURS):
            if any(edge.branch not in ("true", "false") for edge in rows):
                issues.append(ValidationIssue(code="condition_branch_required", message="Condition connections must be labeled true or false.", node_id=node_id))
        elif len(rows) > 1:
            issues.append(ValidationIssue(code="multiple_outputs", message="Connect this step to at most one next step.", node_id=node_id))

    if len(triggers) == 1:
        start = triggers[0].id
        reachable: set[uuid.UUID] = set()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            queue.extend(edge.target_node_id for edge in outgoing[current])
        for node in nodes:
            if node.id != start and node.id not in reachable:
                issues.append(ValidationIssue(code="node_unreachable", message="Every flow step must be connected to the trigger.", node_id=node.id))

        indegree = {node.id: 0 for node in nodes}
        for edge in edges:
            if edge.source_node_id in ids and edge.target_node_id in ids:
                indegree[edge.target_node_id] += 1
        ready = deque(node_id for node_id, count in indegree.items() if count == 0)
        visited = 0
        while ready:
            node_id = ready.popleft()
            visited += 1
            for edge in outgoing[node_id]:
                indegree[edge.target_node_id] -= 1
                if indegree[edge.target_node_id] == 0:
                    ready.append(edge.target_node_id)
        if visited != len(nodes):
            issues.append(ValidationIssue(code="flow_cycle", message="Flow connections cannot contain a cycle."))
    return issues


def save_flow(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, data: AutomationFlowSave) -> None:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    _editable(automation)
    supplied_ids = [node.id for node in data.nodes]
    if len(set(supplied_ids)) != len(supplied_ids):
        raise AutomationConflictError("Each flow step must have a unique id.")
    valid_ids = set(supplied_ids)
    for edge in data.edges:
        if edge.source_node_id not in valid_ids or edge.target_node_id not in valid_ids or edge.source_node_id == edge.target_node_id:
            raise AutomationConflictError("A connection references a missing or identical flow step.")

    try:
        existing = {node.id: node for node in db.query(AutomationNode).filter_by(tenant_id=tenant_id, automation_id=automation_id).all()}
        db.query(AutomationEdge).filter_by(tenant_id=tenant_id, automation_id=automation_id).delete(synchronize_session=False)
        for node_id in set(existing) - valid_ids:
            db.query(AutomationNode).filter_by(id=node_id, tenant_id=tenant_id, automation_id=automation_id).delete(synchronize_session=False)
        for item in data.nodes:
            node = existing.get(item.id)
            if node is None:
                node = AutomationNode(id=item.id, tenant_id=tenant_id, automation_id=automation_id)
                db.add(node)
            node.node_type = item.node_type
            node.name = item.name
            node.config = item.config
            node.sort_order = item.sort_order
        db.flush()
        for edge in data.edges:
            db.add(AutomationEdge(
                tenant_id=tenant_id, automation_id=automation_id,
                source_node_id=edge.source_node_id, target_node_id=edge.target_node_id, branch=edge.branch,
            ))
        automation.version += 1
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        raise AutomationConflictError("The flow could not be saved. Check its connections and try again.") from None


def create_node(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, data: AutomationNodeCreate) -> AutomationNode:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    _editable(automation)
    node = AutomationNode(tenant_id=tenant_id, automation_id=automation_id, **data.model_dump())
    db.add(node)
    automation.version += 1
    db.commit()
    db.refresh(node)
    return node


def update_node(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, node_id: uuid.UUID, data: AutomationNodeUpdate) -> AutomationNode:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    _editable(automation)
    node = db.query(AutomationNode).filter_by(id=node_id, automation_id=automation_id, tenant_id=tenant_id).first()
    if node is None:
        raise AutomationNotFoundError("Flow step not found.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(node, key, value)
    automation.version += 1
    db.commit()
    db.refresh(node)
    return node


def delete_node(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, node_id: uuid.UUID) -> None:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    _editable(automation)
    node = db.query(AutomationNode).filter_by(id=node_id, automation_id=automation_id, tenant_id=tenant_id).first()
    if node is None:
        raise AutomationNotFoundError("Flow step not found.")
    db.delete(node)
    automation.version += 1
    db.commit()


def activate(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID) -> Automation:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    if automation.status == AutomationStatus.ARCHIVED:
        raise AutomationFlowLockedError("Archived automations cannot be activated.")
    issues = validate_flow(db, tenant_id, automation_id)
    if issues:
        raise AutomationInvalidFlowError(issues)
    if automation.status != AutomationStatus.ACTIVE:
        automation.version += 1
    automation.status = AutomationStatus.ACTIVE
    db.commit()
    db.refresh(automation)
    return automation


def pause(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID) -> Automation:
    automation = get_model(db, tenant_id, automation_id, for_update=True)
    if automation.status != AutomationStatus.ACTIVE:
        raise AutomationFlowLockedError("Only an active automation can be paused.")
    automation.status = AutomationStatus.PAUSED
    db.commit()
    db.refresh(automation)
    return automation


def flow_snapshot(db: Session, automation: Automation) -> dict[str, Any]:
    nodes, edges = _nodes_edges(db, automation.tenant_id, automation.id)
    return {
        "nodes": [{"id": str(n.id), "node_type": n.node_type, "name": n.name, "config": n.config, "sort_order": n.sort_order} for n in nodes],
        "edges": [{"source_node_id": str(e.source_node_id), "target_node_id": str(e.target_node_id), "branch": e.branch} for e in edges],
    }


def enqueue_for_inbound_message(
    db: Session, *, tenant_id: uuid.UUID, channel_id: uuid.UUID,
    conversation_id: uuid.UUID, contact_id: uuid.UUID, message_id: uuid.UUID,
) -> int:
    """Insert one durable execution per active matching automation/message.

    Called from the existing database-backed WhatsApp event worker while its
    event transaction is open. It does no network I/O and commits nowhere.
    """
    automations = db.query(Automation).join(
        AutomationNode,
        (AutomationNode.automation_id == Automation.id) & (AutomationNode.tenant_id == Automation.tenant_id),
    ).filter(
        Automation.tenant_id == tenant_id, Automation.status == AutomationStatus.ACTIVE,
        Automation.trigger_type == AutomationTrigger.INBOUND_MESSAGE,
        AutomationNode.node_type == AutomationNodeType.TRIGGER_MESSAGE,
        AutomationNode.config["channel_connection_id"].astext == str(channel_id),
    ).with_for_update(of=Automation).all()
    automation_ids = [automation.id for automation in automations]
    nodes_by_automation: dict[uuid.UUID, list[AutomationNode]] = defaultdict(list)
    edges_by_automation: dict[uuid.UUID, list[AutomationEdge]] = defaultdict(list)
    if automation_ids:
        for node in db.query(AutomationNode).filter(
            AutomationNode.tenant_id == tenant_id, AutomationNode.automation_id.in_(automation_ids),
        ).order_by(AutomationNode.sort_order, AutomationNode.id).all():
            nodes_by_automation[node.automation_id].append(node)
        for edge in db.query(AutomationEdge).filter(
            AutomationEdge.tenant_id == tenant_id, AutomationEdge.automation_id.in_(automation_ids),
        ).all():
            edges_by_automation[edge.automation_id].append(edge)
    created = 0
    for automation in automations:
        nodes = nodes_by_automation[automation.id]
        trigger = next((node for node in nodes if node.node_type == AutomationNodeType.TRIGGER_MESSAGE), None)
        if trigger is None:
            continue
        key = f"{automation.id}:{message_id}"
        snapshot = {
            "nodes": [{"id": str(n.id), "node_type": n.node_type, "name": n.name, "config": n.config, "sort_order": n.sort_order} for n in nodes],
            "edges": [{"source_node_id": str(e.source_node_id), "target_node_id": str(e.target_node_id), "branch": e.branch} for e in edges_by_automation[automation.id]],
        }
        inserted = db.execute(
            insert(AutomationExecution).values(
                tenant_id=tenant_id, automation_id=automation.id,
                automation_version=automation.version, conversation_id=conversation_id,
                contact_id=contact_id, trigger_message_id=message_id,
                idempotency_key=key, status=AutomationExecutionStatus.QUEUED,
                flow_snapshot=snapshot, max_attempts=settings.automation_max_attempts,
            ).on_conflict_do_nothing(
                index_elements=["tenant_id", "automation_id", "trigger_message_id"],
            ).returning(AutomationExecution.id)
        ).scalar_one_or_none()
        if inserted:
            created += 1
    return created


def simulate_flow(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID, message: str) -> dict[str, Any]:
    issues = validate_flow(db, tenant_id, automation_id)
    if issues:
        return {"valid": False, "trigger_matched": False, "steps": [], "final_result": "Fix the validation issues before simulation."}
    nodes, edges = _nodes_edges(db, tenant_id, automation_id)
    node_map = {str(node.id): node for node in nodes}
    outgoing: dict[str, list[AutomationEdge]] = defaultdict(list)
    for edge in edges:
        outgoing[str(edge.source_node_id)].append(edge)
    current = next(node for node in nodes if node.node_type == AutomationNodeType.TRIGGER_MESSAGE)
    steps: list[dict[str, Any]] = []
    trigger_matched = False
    final = "Simulation completed without sending a real message."
    for _ in range(50):
        config = current.config or {}
        branch = None
        if current.node_type == AutomationNodeType.TRIGGER_MESSAGE:
            trigger_matched = True
            detail = "Inbound WhatsApp message trigger matched."
            result = "matched"
        elif current.node_type == AutomationNodeType.MESSAGE_CONTAINS:
            operator = config.get("operator", "contains")
            needle, haystack = str(config.get("value", "")), message
            if not config.get("case_sensitive", False):
                needle, haystack = needle.casefold(), haystack.casefold()
            matched = {"contains": lambda: needle in haystack, "equals": lambda: needle == haystack,
                       "starts_with": lambda: haystack.startswith(needle), "ends_with": lambda: haystack.endswith(needle)}[operator]()
            branch = "true" if matched else "false"
            result, detail = ("matched", f"Message {operator.replace('_', ' ')} the configured value.") if matched else ("not_matched", f"Message does not {operator.replace('_', ' ')} the configured value.")
        elif current.node_type == AutomationNodeType.BUSINESS_HOURS:
            from app.services.automation_execution_service import _condition_matches
            matched = _condition_matches(current.node_type, config, message, datetime.now(timezone.utc))
            branch = "true" if matched else "false"
            result, detail = ("matched", "Current time is inside business hours.") if matched else ("not_matched", "Current time is outside business hours.")
        elif current.node_type == AutomationNodeType.DELAY:
            result = "would_wait"
            detail = f"Would wait {config.get('duration')} {config.get('unit')}."
        else:
            result = "would_execute"
            detail = {
                AutomationNodeType.SEND_TEXT: "Would send the configured text message.",
                AutomationNodeType.SEND_TEMPLATE: "Would send the approved WhatsApp template.",
                AutomationNodeType.ASSIGN_CONVERSATION: "Would assign the conversation to the selected member.",
                AutomationNodeType.CHANGE_CONVERSATION_STATUS: "Would change the conversation status.",
                AutomationNodeType.DELAY: f"Would wait {config.get('duration')} {config.get('unit')}.",
            }.get(current.node_type, "Would process this step.")
        steps.append({"node_id": current.id, "node_type": current.node_type, "result": result, "detail": detail})
        next_edge = next((edge for edge in outgoing[str(current.id)] if edge.branch == branch), None)
        if next_edge is None:
            if current.node_type == AutomationNodeType.MESSAGE_CONTAINS and branch == "false":
                final = "Condition did not match; no action would run."
            break
        current = node_map[str(next_edge.target_node_id)]
    else:
        final = "Simulation stopped at the 50-step safety limit."
    return {"valid": True, "trigger_matched": trigger_matched, "steps": steps, "final_result": final}


def list_executions(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID | None, page: int, page_size: int):
    query = db.query(AutomationExecution, Automation.name).join(Automation, Automation.id == AutomationExecution.automation_id).filter(AutomationExecution.tenant_id == tenant_id)
    if automation_id is not None:
        get_model(db, tenant_id, automation_id)
        query = query.filter(AutomationExecution.automation_id == automation_id)
    total = query.count()
    rows = query.order_by(AutomationExecution.created_at.desc(), AutomationExecution.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"execution": row[0], "automation_name": row[1]} for row in rows], "total": total, "page": page, "page_size": page_size}


def list_execution_logs(db: Session, tenant_id: uuid.UUID, execution_id: uuid.UUID):
    execution = db.query(AutomationExecution.id).filter_by(id=execution_id, tenant_id=tenant_id).first()
    if execution is None:
        raise AutomationNotFoundError("Execution not found.")
    return db.query(AutomationExecutionLog).filter_by(tenant_id=tenant_id, execution_id=execution_id).order_by(AutomationExecutionLog.created_at, AutomationExecutionLog.id).all()


def execution_metrics(db: Session, tenant_id: uuid.UUID, automation_id: uuid.UUID):
    get_model(db, tenant_id, automation_id)
    counts = dict(db.query(AutomationExecution.status, func.count(AutomationExecution.id)).filter(
        AutomationExecution.tenant_id == tenant_id, AutomationExecution.automation_id == automation_id,
    ).group_by(AutomationExecution.status).all())
    latest = db.query(AutomationExecution.created_at).filter_by(tenant_id=tenant_id, automation_id=automation_id).order_by(AutomationExecution.created_at.desc()).first()
    failure = db.query(AutomationExecution.error_summary).filter(
        AutomationExecution.tenant_id == tenant_id, AutomationExecution.automation_id == automation_id,
        AutomationExecution.status == AutomationExecutionStatus.FAILED,
    ).order_by(AutomationExecution.completed_at.desc()).first()
    return {
        "total": sum(counts.values()), "completed": counts.get("completed", 0), "failed": counts.get("failed", 0),
        "running": counts.get("running", 0), "retrying": counts.get("retrying", 0), "queued": counts.get("queued", 0),
        "last_execution_at": latest[0] if latest else None, "last_failure": failure[0] if failure else None,
    }
