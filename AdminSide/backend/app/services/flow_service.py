"""CRUD for visual chat-flows, plus duplicate (copy)."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Flow, FlowStatus
from app.schemas.flow import FlowCreate, FlowUpdate


class FlowNotFoundError(Exception):
    """No such flow for this tenant."""


def _get(db: Session, tenant_id: uuid.UUID, flow_id: uuid.UUID, for_update: bool = False) -> Flow:
    q = select(Flow).where(Flow.tenant_id == tenant_id, Flow.id == flow_id)
    if for_update:
        q = q.with_for_update()
    row = db.execute(q).scalar_one_or_none()
    if row is None:
        raise FlowNotFoundError("Flow not found.")
    return row


def list_flows(db: Session, tenant_id: uuid.UUID, skip: int, limit: int, search: str | None):
    base = select(Flow).where(Flow.tenant_id == tenant_id)
    if search:
        base = base.where(Flow.name.ilike(f"%{search}%"))
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(
        base.order_by(Flow.created_at.desc()).offset(skip).limit(limit)
    ).scalars().all()
    return rows, total


def get_flow(db: Session, tenant_id: uuid.UUID, flow_id: uuid.UUID) -> Flow:
    return _get(db, tenant_id, flow_id)


def create_flow(db: Session, tenant_id: uuid.UUID, user, data: FlowCreate) -> Flow:
    # A fresh flow starts with a Start node so the canvas is never empty.
    start_node = {
        "id": "start",
        "type": "message",
        "position": {"x": 320, "y": 120},
        "data": {"label": "Text Message", "channel": _default_channel(data.channels), "messageType": "text", "message": "", "isStart": True},
    }
    flow = Flow(
        tenant_id=tenant_id,
        name=data.name,
        status=FlowStatus.DRAFT.value,
        channels=data.channels,
        nodes=[start_node],
        edges=[],
        created_by_user_id=getattr(user, "id", None),
    )
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


def update_flow(db: Session, tenant_id: uuid.UUID, flow_id: uuid.UUID, data: FlowUpdate) -> Flow:
    flow = _get(db, tenant_id, flow_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        flow.name = changes["name"]
    if "status" in changes and changes["status"] is not None:
        flow.status = data.status.value
    if "channels" in changes and changes["channels"] is not None:
        flow.channels = changes["channels"]
    if "nodes" in changes and changes["nodes"] is not None:
        flow.nodes = changes["nodes"]
    if "edges" in changes and changes["edges"] is not None:
        flow.edges = changes["edges"]
    db.commit()
    db.refresh(flow)
    return flow


def delete_flow(db: Session, tenant_id: uuid.UUID, flow_id: uuid.UUID) -> None:
    flow = _get(db, tenant_id, flow_id, for_update=True)
    db.delete(flow)
    db.commit()


def copy_flow(db: Session, tenant_id: uuid.UUID, flow_id: uuid.UUID, user) -> Flow:
    src = _get(db, tenant_id, flow_id)
    clone = Flow(
        tenant_id=tenant_id,
        name=_copy_name(db, tenant_id, src.name),
        status=FlowStatus.DRAFT.value,
        channels=list(src.channels or []),
        nodes=list(src.nodes or []),
        edges=list(src.edges or []),
        created_by_user_id=getattr(user, "id", None),
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


def _copy_name(db: Session, tenant_id: uuid.UUID, name: str) -> str:
    candidate = f"{name} (copy)"[:150]
    exists = db.execute(select(Flow.id).where(Flow.tenant_id == tenant_id, Flow.name == candidate)).scalar_one_or_none()
    if not exists:
        return candidate
    return f"{name} (copy {uuid.uuid4().hex[:4]})"[:150]


def _default_channel(channels: list[str]) -> str:
    if not channels or "omnichannel" in channels:
        return "whatsapp"
    return channels[0]
