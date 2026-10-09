import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentTenant, DbSession, get_db, require_permission
from app.models.tenant import Tenant
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageDirection
from app.models.channel_connection import ChannelConnection, ChannelStatus
from app.models.automation import Automation, AutomationStatus, AutomationExecution, AutomationExecutionStatus

router = APIRouter(tags=["Analytics"])

@router.get("/analytics/overview")
def get_analytics_overview(
    tenant: CurrentTenant,
    db: DbSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    # Total Contacts
    contacts_q = select(func.count()).select_from(Contact).where(Contact.tenant_id == tenant.id)
    if start_date:
        contacts_q = contacts_q.where(Contact.created_at >= start_date)
    if end_date:
        contacts_q = contacts_q.where(Contact.created_at <= end_date)
    total_contacts = db.scalar(contacts_q) or 0

    # Total Chats
    chats_q = select(func.count()).select_from(Conversation).where(Conversation.tenant_id == tenant.id)
    if start_date:
        chats_q = chats_q.where(Conversation.created_at >= start_date)
    if end_date:
        chats_q = chats_q.where(Conversation.created_at <= end_date)
    total_chats = db.scalar(chats_q) or 0

    # Conversation Status Breakdown
    conv_status_q = select(Conversation.status, func.count()).where(Conversation.tenant_id == tenant.id)
    if start_date:
        conv_status_q = conv_status_q.where(Conversation.created_at >= start_date)
    if end_date:
        conv_status_q = conv_status_q.where(Conversation.created_at <= end_date)
    conv_status_q = conv_status_q.group_by(Conversation.status)
    conv_statuses = dict(db.execute(conv_status_q).all())
    
    open_chats = conv_statuses.get(ConversationStatus.OPEN.value, 0)
    pending_chats = conv_statuses.get(ConversationStatus.PENDING.value, 0)
    resolved_chats = conv_statuses.get(ConversationStatus.RESOLVED.value, 0)
    closed_chats = conv_statuses.get(ConversationStatus.CLOSED.value, 0)

    # Active Flows
    active_flows = db.scalar(
        select(func.count()).select_from(Automation)
        .where(Automation.tenant_id == tenant.id, Automation.status == AutomationStatus.ACTIVE)
    ) or 0

    return {
        "total_contacts": total_contacts,
        "total_chats": total_chats,
        "open_chats": open_chats,
        "pending_chats": pending_chats,
        "resolved_chats": resolved_chats,
        "closed_chats": closed_chats,
        "active_flows": active_flows,
    }

@router.get("/analytics/channels")
def get_analytics_channels(
    tenant: CurrentTenant,
    db: DbSession,
) -> list[dict[str, Any]]:
    channels = db.scalars(
        select(ChannelConnection)
        .where(ChannelConnection.tenant_id == tenant.id, ChannelConnection.is_deleted == False)
    ).all()
    
    result = []
    for c in channels:
        result.append({
            "id": str(c.id),
            "name": c.name,
            "channel_type": c.channel_type,
            "status": c.status,
            "external_account_id": c.external_account_id,
        })
    return result

@router.get("/analytics/time-series")
def get_analytics_time_series(
    tenant: CurrentTenant,
    db: DbSession,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    q = (
        select(
            func.date_trunc('day', Message.created_at).label('date'),
            Message.direction,
            func.count().label('count')
        )
        .where(Message.tenant_id == tenant.id)
        .where(Message.created_at >= start_date)
        .where(Message.created_at <= end_date)
        .group_by(text('date'), Message.direction)
        .order_by(text('date'))
    )
    rows = db.execute(q).all()
    
    data = {}
    for row in rows:
        date_str = row.date.strftime("%Y-%m-%d") if row.date else ""
        if not date_str:
            continue
        if date_str not in data:
            data[date_str] = {"date": date_str, "inbound": 0, "outbound": 0}
        
        if row.direction == MessageDirection.INBOUND.value:
            data[date_str]["inbound"] = row.count
        else:
            data[date_str]["outbound"] = row.count
            
    return sorted(list(data.values()), key=lambda x: x["date"])

@router.get("/analytics/automations")
def get_analytics_automations(
    tenant: CurrentTenant,
    db: DbSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    q = select(AutomationExecution.status, func.count()).where(AutomationExecution.tenant_id == tenant.id)
    if start_date:
        q = q.where(AutomationExecution.created_at >= start_date)
    if end_date:
        q = q.where(AutomationExecution.created_at <= end_date)
    q = q.group_by(AutomationExecution.status)
    
    statuses = dict(db.execute(q).all())
    
    total = sum(statuses.values())
    completed = statuses.get(AutomationExecutionStatus.COMPLETED.value, 0)
    failed = statuses.get(AutomationExecutionStatus.FAILED.value, 0)
    
    return {
        "total_executions": total,
        "completed": completed,
        "failed": failed,
        "success_rate": round(completed / total * 100, 2) if total > 0 else 0.0
    }
