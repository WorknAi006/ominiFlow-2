import uuid
from typing import List, Tuple, Optional, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.campaign import Campaign, CampaignStatus
from app.models.contact import Contact
from app.models.tag import ContactTag
from app.models.channel_connection import ChannelConnection
from app.models.message_template import MessageTemplate
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.models.campaign_recipient import CampaignRecipient, CampaignRecipientStatus

class CampaignService:
    def __init__(self, db: Session):
        self.db = db

    def get_audience_count(self, tenant_id: uuid.UUID, config: dict[str, Any]) -> int:
        tags = config.get("tags", [])
        all_contacts = config.get("all_contacts", False) or not tags
        
        if all_contacts or not tags:
            query = select(func.count(Contact.id)).where(
                Contact.tenant_id == tenant_id,
                Contact.is_blocked.is_(False),
                Contact.phone_number.is_not(None),
            )
            return self.db.scalar(query) or 0

        tag_uuids = []
        for t in tags:
            try:
                tag_uuids.append(uuid.UUID(str(t)))
            except (ValueError, TypeError):
                pass

        if not tag_uuids:
            return 0
        
        # Audience is contacts that have at least one of the tags and a valid phone number
        query = (
            select(func.count(func.distinct(ContactTag.contact_id)))
            .join(Contact, Contact.id == ContactTag.contact_id)
            .where(
                ContactTag.tenant_id == tenant_id,
                ContactTag.tag_id.in_(tag_uuids),
                Contact.is_blocked.is_(False),
                Contact.phone_number.is_not(None),
            )
        )
        return self.db.scalar(query) or 0

    def _validate_template(
        self,
        tenant_id: uuid.UUID,
        channel_id: uuid.UUID,
        template_id: uuid.UUID | None,
    ) -> None:
        if template_id is None:
            return
        template = self.db.scalar(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.tenant_id == tenant_id,
            )
        )
        if template is None:
            raise ValueError("Message template not found")
        if template.channel_connection_id != channel_id:
            raise ValueError("Select a template belonging to the selected WhatsApp channel.")
        if not template.is_active or template.status != "approved":
            raise ValueError("Only active, Meta-approved templates can be used in broadcasts.")

    def create_campaign(self, tenant_id: uuid.UUID, data: CampaignCreate) -> Campaign:
        # Validate channel connection
        channel = self.db.scalar(
            select(ChannelConnection).where(
                ChannelConnection.id == data.channel_connection_id,
                ChannelConnection.tenant_id == tenant_id,
                ChannelConnection.is_deleted.is_(False)
            )
        )
        if not channel:
            raise ValueError("Channel connection not found")

        self._validate_template(tenant_id, channel.id, data.message_template_id)

        # Calculate recipients
        audience_count = 0
        if data.audience_config:
            audience_count = self.get_audience_count(tenant_id, data.audience_config)

        campaign_data = data.model_dump()
        campaign = Campaign(
            **campaign_data, 
            tenant_id=tenant_id, 
            total_recipients=audience_count,
            status=CampaignStatus.DRAFT
        )
        self.db.add(campaign)
        
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get_campaigns(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> Tuple[List[Campaign], int]:
        query = select(Campaign).where(Campaign.tenant_id == tenant_id)
        if search:
            query = query.where(Campaign.name.ilike(f"%{search}%"))
        
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        campaigns = self.db.scalars(
            query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit)
        ).all()
        return list(campaigns), total

    def get_campaign(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Optional[Campaign]:
        return self.db.scalar(select(Campaign).where(Campaign.tenant_id == tenant_id, Campaign.id == campaign_id))

    def update_campaign(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID, data: CampaignUpdate) -> Optional[Campaign]:
        campaign = self.get_campaign(tenant_id, campaign_id)
        if not campaign:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "channel_connection_id" in update_data or "message_template_id" in update_data:
            self._validate_template(
                tenant_id,
                update_data.get("channel_connection_id", campaign.channel_connection_id),
                update_data.get("message_template_id", campaign.message_template_id),
            )
        
        # If audience changed, update count
        if "audience_config" in update_data:
            update_data["total_recipients"] = self.get_audience_count(tenant_id, update_data["audience_config"])
            
        # Optional: check valid status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == CampaignStatus.SENDING or new_status == CampaignStatus.SCHEDULED:
                if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.PAUSED):
                    raise ValueError(f"Cannot transition to {new_status} from {campaign.status}")

        for key, value in update_data.items():
            setattr(campaign, key, value)
            
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def start_campaign(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
        # Lock campaign to prevent concurrent starts
        campaign = self.db.scalar(
            select(Campaign)
            .where(Campaign.tenant_id == tenant_id, Campaign.id == campaign_id)
            .with_for_update()
        )
        if not campaign:
            raise ValueError("Campaign not found")
        
        if campaign.status != CampaignStatus.DRAFT:
            raise ValueError(f"Cannot start a campaign in {campaign.status} status")

        self._validate_template(
            tenant_id, campaign.channel_connection_id, campaign.message_template_id,
        )

        # Resolve audience and populate recipients
        config = campaign.audience_config or {}
        tags = config.get("tags", [])
        all_contacts = config.get("all_contacts", False) or not tags

        if all_contacts or not tags:
            contact_ids = self.db.scalars(
                select(Contact.id).where(
                    Contact.tenant_id == tenant_id,
                    Contact.is_blocked.is_(False),
                    Contact.phone_number.is_not(None),
                )
            ).all()
        else:
            tag_uuids = []
            for t in tags:
                try:
                    tag_uuids.append(uuid.UUID(str(t)))
                except (ValueError, TypeError):
                    pass

            if not tag_uuids:
                contact_ids = self.db.scalars(
                    select(Contact.id).where(
                        Contact.tenant_id == tenant_id,
                        Contact.is_blocked.is_(False),
                        Contact.phone_number.is_not(None),
                    )
                ).all()
            else:
                contact_ids = self.db.scalars(
                    select(func.distinct(ContactTag.contact_id))
                    .join(Contact, Contact.id == ContactTag.contact_id)
                    .where(
                        ContactTag.tenant_id == tenant_id,
                        ContactTag.tag_id.in_(tag_uuids),
                        Contact.is_blocked.is_(False),
                        Contact.phone_number.is_not(None),
                    )
                ).all()

        if not contact_ids:
            if not all_contacts and tags:
                raise ValueError(
                    "No matching contacts with phone numbers found for the selected tags. "
                    "Please assign tags to contacts or broadcast to All Contacts."
                )
            raise ValueError(
                "No matching contacts found with phone numbers for this broadcast. "
                "Please add contacts with phone numbers under Contacts first."
            )

        # Atomically populate campaign_recipients
        recipients = []
        for cid in contact_ids:
            recipients.append(
                CampaignRecipient(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    contact_id=cid,
                    status=CampaignRecipientStatus.PENDING
                )
            )
        
        self.db.add_all(recipients)
        campaign.status = CampaignStatus.SENDING
        campaign.total_recipients = len(recipients)
        self.db.commit()
        
        return campaign
