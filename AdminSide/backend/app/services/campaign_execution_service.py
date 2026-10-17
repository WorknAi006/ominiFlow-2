import logging
from datetime import datetime, timezone, timedelta
import uuid

from sqlalchemy import select, update, or_, and_
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_recipient import CampaignRecipient, CampaignRecipientStatus
from app.models.channel_connection import ChannelConnection
from app.models.contact import Contact
from app.models.message_template import MessageTemplate
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.outbound_message_service import (
    send_message,
    MessageSendFailedError,
    RecipientUnavailableError,
    UnsupportedChannelError,
    ChannelNotConnectedError,
    CredentialsUnavailableError,
    ProviderNotConfiguredForSendError
)
from app.schemas.message import TextMessageCreate, TemplateMessageCreate
from app.services import conversation_service

logger = logging.getLogger(__name__)

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def process_pending_recipients(db: Session, limit: int = 50, worker_id: str = "campaign-worker") -> dict[str, int]:
    now = _utcnow()
    
    # Find pending recipients and lock them
    # Ensure their campaign is still in SENDING status
    query = (
        select(CampaignRecipient)
        .join(Campaign)
        .where(
            or_(
                CampaignRecipient.status == CampaignRecipientStatus.PENDING,
                and_(
                    CampaignRecipient.status == CampaignRecipientStatus.PROCESSING,
                    CampaignRecipient.processing_started_at < now - timedelta(minutes=10)
                )
            ),
            Campaign.status == CampaignStatus.SENDING,
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    
    recipients = db.scalars(query).all()
    if not recipients:
        return {"processed": 0, "failed": 0, "sent": 0}

    # Mark as processing
    for r in recipients:
        r.status = CampaignRecipientStatus.PROCESSING
        r.worker_id = worker_id
        r.processing_started_at = now
        r.attempt_count += 1
    
    db.commit()

    processed_count = 0
    sent_count = 0
    failed_count = 0

    for r in recipients:
        try:
            # We process outside the FOR UPDATE lock to avoid blocking other rows
            # during provider network requests.
            _process_single_recipient(db, r)
            if r.status == CampaignRecipientStatus.SENT:
                sent_count += 1
            else:
                failed_count += 1
        except Exception as exc:
            logger.exception("Failed to process campaign recipient %s", r.id)
            failed_count += 1
        processed_count += 1

    return {"processed": processed_count, "sent": sent_count, "failed": failed_count}

def _process_single_recipient(db: Session, r: CampaignRecipient) -> None:
    now = _utcnow()
    
    campaign = db.scalar(select(Campaign).where(Campaign.id == r.campaign_id))
    
    if not campaign or campaign.status != CampaignStatus.SENDING:
        # Campaign was cancelled or paused
        r.status = CampaignRecipientStatus.PENDING
        r.worker_id = None
        db.commit()
        return

    # Send as an active member of the campaign's own tenant (tenant-scoped,
    # never a user from another tenant).
    actor = db.scalar(
        select(User)
        .join(TenantMembership, TenantMembership.user_id == User.id)
        .where(
            TenantMembership.tenant_id == r.tenant_id,
            TenantMembership.status == "active",
            User.is_active.is_(True),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )

    contact = db.scalar(select(Contact).where(Contact.id == r.contact_id))
    
    try:
        if not actor:
            raise RecipientUnavailableError("No active user in this tenant to send as")
        if not contact or contact.is_blocked:
            raise RecipientUnavailableError("Contact not found or blocked")

        channel = db.scalar(select(ChannelConnection).where(ChannelConnection.id == campaign.channel_connection_id))
        if not channel:
            raise ChannelNotConnectedError("Channel not found")

        # Find or create a conversation for this channel and contact
        conversation = conversation_service.get_or_create_conversation(
            db, r.tenant_id, r.contact_id, channel.id, force_channel=True,
        )

        idempotency_key = uuid.uuid5(uuid.NAMESPACE_OID, f"campaign_{campaign.id}_recipient_{r.id}_attempt_{r.attempt_count}")
        
        if campaign.message_template_id:
            template = db.scalar(
                select(MessageTemplate).where(
                    MessageTemplate.id == campaign.message_template_id,
                    MessageTemplate.tenant_id == r.tenant_id,
                )
            )
            if not template:
                raise ValueError("Template not found for campaign")
            data = TemplateMessageCreate(
                type="template",
                template_name=template.name,
                language=template.language,
                components=campaign.template_params or [],
            )
        else:
            data = TextMessageCreate(type="text", text=campaign.text_content or "")

        msg = send_message(db, r.tenant_id, actor, conversation.id, data, idempotency_key=idempotency_key)
        
        r.status = CampaignRecipientStatus.SENT
        r.external_message_id = msg.external_message_id
        r.processed_at = now
        db.execute(update(Campaign).where(Campaign.id == campaign.id).values(delivered_count=Campaign.delivered_count + 1))
        
    except (RecipientUnavailableError, UnsupportedChannelError, ChannelNotConnectedError, CredentialsUnavailableError, ProviderNotConfiguredForSendError, ValueError) as e:
        r.status = CampaignRecipientStatus.SKIPPED
        r.error_summary = str(e)[:500]
        r.processed_at = now
        db.execute(update(Campaign).where(Campaign.id == campaign.id).values(failed_count=Campaign.failed_count + 1))
    except Exception as e:
        if isinstance(e, MessageSendFailedError):
            logger.exception("Failed to send message")
        else:
            logger.exception("Unexpected error sending campaign message")
            
        if r.attempt_count < 3:
            r.status = CampaignRecipientStatus.PENDING
            r.worker_id = None
            r.error_summary = str(e)[:500]
        else:
            r.status = CampaignRecipientStatus.FAILED
            r.error_summary = str(e)[:500]
            r.processed_at = now
            db.execute(update(Campaign).where(Campaign.id == campaign.id).values(failed_count=Campaign.failed_count + 1))

    db.commit()
