"""Merge WhatsApp conversations per tenant contact across connected lines.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
"""
from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("channel_type", sa.String(length=20), nullable=True))
    op.add_column("conversations", sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True))

    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE conversations AS conversation
        SET channel_type = channel.channel_type
        FROM channel_connections AS channel
        WHERE channel.id = conversation.channel_connection_id
    """))
    connection.execute(sa.text("""
        UPDATE conversations AS conversation
        SET last_inbound_at = (
            SELECT max(coalesce(message.sent_at, message.created_at))
            FROM messages AS message
            WHERE message.conversation_id = conversation.id
              AND message.direction = 'inbound'
        )
        WHERE conversation.channel_type = 'whatsapp'
    """))

    groups = connection.execute(sa.text("""
        SELECT tenant_id, contact_id
        FROM conversations
        WHERE channel_type = 'whatsapp'
        GROUP BY tenant_id, contact_id
        HAVING count(*) > 1
    """)).all()

    for tenant_id, contact_id in groups:
        conversations = connection.execute(sa.text("""
            SELECT id, channel_connection_id, status, subject, assigned_user_id,
                   unread_count, last_message_at, last_inbound_at, created_at,
                   updated_at, metadata
            FROM conversations
            WHERE tenant_id = :tenant_id
              AND contact_id = :contact_id
              AND channel_type = 'whatsapp'
            ORDER BY
                (status IN ('open', 'pending')) DESC,
                coalesce(last_message_at, created_at) DESC,
                created_at DESC,
                id ASC
        """), {"tenant_id": tenant_id, "contact_id": contact_id}).mappings().all()

        primary = conversations[0]
        duplicates = conversations[1:]
        primary_id = primary["id"]
        duplicate_ids = [row["id"] for row in duplicates]
        all_ids = [primary_id, *duplicate_ids]

        latest_inbound = connection.execute(sa.text("""
            SELECT conversation.channel_connection_id,
                   coalesce(message.sent_at, message.created_at) AS inbound_at
            FROM messages AS message
            JOIN conversations AS conversation ON conversation.id = message.conversation_id
            WHERE conversation.id IN :conversation_ids
              AND message.direction = 'inbound'
            ORDER BY coalesce(message.sent_at, message.created_at) DESC,
                     message.created_at DESC
            LIMIT 1
        """).bindparams(sa.bindparam("conversation_ids", expanding=True)),
            {"conversation_ids": all_ids}).mappings().first()

        latest_inbound_at = max(
            (row["last_inbound_at"] for row in conversations if row["last_inbound_at"] is not None),
            default=None,
        )
        last_message_at = max(
            (row["last_message_at"] for row in conversations if row["last_message_at"] is not None),
            default=None,
        )
        assigned_user_id = primary["assigned_user_id"] or next(
            (row["assigned_user_id"] for row in duplicates if row["assigned_user_id"] is not None),
            None,
        )
        subject = primary["subject"] or next(
            (row["subject"] for row in duplicates if row["subject"] is not None),
            None,
        )
        metadata = primary["metadata"] or next(
            (row["metadata"] for row in duplicates if row["metadata"] is not None),
            None,
        )

        has_active_flow = connection.execute(sa.text("""
            SELECT id
            FROM flow_sessions
            WHERE conversation_id = :conversation_id
              AND status IN ('active', 'waiting')
            ORDER BY updated_at DESC, id
            LIMIT 1
        """), {"conversation_id": primary_id}).scalar_one_or_none()

        for duplicate_id in duplicate_ids:
            duplicate_active_flow = connection.execute(sa.text("""
                SELECT id
                FROM flow_sessions
                WHERE conversation_id = :conversation_id
                  AND status IN ('active', 'waiting')
                ORDER BY updated_at DESC, id
                LIMIT 1
            """), {"conversation_id": duplicate_id}).scalar_one_or_none()

            if has_active_flow is not None and duplicate_active_flow is not None:
                connection.execute(sa.text("""
                    UPDATE flow_sessions
                    SET status = 'failed',
                        detail = left(concat_ws(' ', detail,
                            'Stopped because its WhatsApp conversation was merged.'), 500)
                    WHERE conversation_id = :conversation_id
                      AND status IN ('active', 'waiting')
                """), {"conversation_id": duplicate_id})
            elif duplicate_active_flow is not None:
                has_active_flow = duplicate_active_flow

            for table in ("messages", "flow_sessions", "automation_runs", "keyword_triggers", "credit_usages"):
                connection.execute(sa.text(
                    f"UPDATE {table} SET conversation_id = :primary_id "
                    "WHERE conversation_id = :duplicate_id"
                ), {"primary_id": primary_id, "duplicate_id": duplicate_id})

        connection.execute(sa.text("""
            UPDATE conversations
            SET channel_connection_id = :channel_connection_id,
                status = :status,
                subject = :subject,
                assigned_user_id = :assigned_user_id,
                unread_count = :unread_count,
                last_message_at = :last_message_at,
                last_inbound_at = :last_inbound_at,
                metadata = :metadata
            WHERE id = :primary_id
        """), {
            "channel_connection_id": latest_inbound["channel_connection_id"] if latest_inbound else primary["channel_connection_id"],
            "status": primary["status"],
            "subject": subject,
            "assigned_user_id": assigned_user_id,
            "unread_count": sum(row["unread_count"] for row in conversations),
            "last_message_at": last_message_at,
            "last_inbound_at": latest_inbound_at,
            "metadata": metadata,
            "primary_id": primary_id,
        })
        connection.execute(sa.text("""
            DELETE FROM conversations
            WHERE id IN :duplicate_ids
        """).bindparams(sa.bindparam("duplicate_ids", expanding=True)),
            {"duplicate_ids": duplicate_ids})

    op.create_index(
        "uq_conversations_whatsapp_contact",
        "conversations",
        ["tenant_id", "contact_id"],
        unique=True,
        postgresql_where=sa.text("channel_type = 'whatsapp'"),
    )


def downgrade() -> None:
    op.drop_index("uq_conversations_whatsapp_contact", table_name="conversations")
    op.drop_column("conversations", "last_inbound_at")
    op.drop_column("conversations", "channel_type")
