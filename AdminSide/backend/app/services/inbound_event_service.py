"""
Channel-neutral inbound processing boundary.

Consumes a NormalizedInboundEvent (already parsed by the owning provider)
and turns it into inbox data, identically for every channel:

    NormalizedInboundEvent
        -> ContactIdentity -> Contact
        -> Conversation
        -> Message
        -> Automation enqueue
        -> Realtime events

There is NO provider-specific parsing here: all WhatsApp (or future
Instagram/Facebook/Web Chat) payload knowledge stays in that provider's
normalizer. The caller runs this inside its durable event transaction and
publishes the returned realtime events only after it commits.
"""
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.base import NormalizedInboundEvent
from app.models import ChannelConnection
from app.services import (
    contact_service,
    conversation_service,
    media_service,
    message_service,
    realtime_service,
)


def process_inbound_event(
    db: Session,
    event: NormalizedInboundEvent,
) -> list[dict[str, Any]]:
    """
    Persist one normalized inbound message. Returns the realtime events to
    publish after commit (message.created then conversation.updated), or an
    empty list when the message was already stored (idempotent replay).

    Tenant and channel come from the normalized event, which the caller
    derived from trusted routing — never from the provider payload.
    """
    # Already stored (event replayed): leave contact/conversation untouched.
    if message_service.find_by_external_id(
        db, event.tenant_id, event.channel_connection_id, event.external_message_id,
    ):
        return []

    channel = db.get(ChannelConnection, event.channel_connection_id)

    contact = contact_service.resolve_inbound_contact(
        db,
        event.tenant_id,
        event.channel_type,
        event.external_sender_id,
        phone_hint=event.phone_hint,
        display_name=event.sender_display_name,
    )

    conversation = conversation_service.get_or_create_conversation(
        db, event.tenant_id, contact.id, event.channel_connection_id,
    )

    reply_to_id = None
    if event.reply_to_external_id:
        replied = message_service.find_by_external_id(
            db, event.tenant_id, event.channel_connection_id, event.reply_to_external_id,
        )
        reply_to_id = replied.id if replied else None

    created = message_service.create_inbound_message(
        db,
        conversation=conversation,
        contact=contact,
        channel=channel,
        external_message_id=event.external_message_id,
        message_type=event.message_type,
        sender_identifier=event.external_sender_id,
        recipient_identifier=channel.external_account_id if channel else None,
        sent_at=event.occurred_at,
        text=event.text,
        media_type=event.media_type,
        media_metadata=event.media_metadata,
        metadata=event.metadata,
        reply_to_message_id=reply_to_id,
    )

    if created is None:
        return []

    conversation_service.record_activity(db, conversation, event.occurred_at, inbound=True)

    # Automation is enqueued in the same durable transaction; workers act
    # later, outside the webhook request. Imported lazily to avoid a cycle.
    from app.services.automation_service import enqueue_for_inbound_message
    enqueue_for_inbound_message(
        db,
        tenant_id=event.tenant_id,
        channel_id=event.channel_connection_id,
        conversation_id=conversation.id,
        contact_id=contact.id,
        message_id=created.id,
    )

    media = event.media_metadata or {}
    if media.get("id"):
        # Queue the download; the media worker fetches it later (no HTTP
        # inside this transaction).
        media_service.register_pending(
            db,
            created,
            provider_media_id=str(media["id"]),
            media_kind=event.message_type.value,
            declared_mime=media.get("mime_type"),
            declared_filename=media.get("filename"),
            declared_sha256=media.get("sha256"),
        )

    message_created = realtime_service.build_message_created_event(
        tenant_id=event.tenant_id,
        conversation_id=conversation.id,
        message_id=created.id,
        direction=created.direction,
        message_type=created.message_type,
        text=created.text,
        created_at=created.created_at,
        contact_id=contact.id,
        contact_name=contact_service.contact_name(contact),
        contact_phone=contact.normalized_phone_number,
    )
    conversation_updated = realtime_service.build_conversation_updated_event(
        tenant_id=event.tenant_id,
        conversation_id=conversation.id,
        **conversation_service.get_update_snapshot(db, conversation),
    )
    return [message_created, conversation_updated]
