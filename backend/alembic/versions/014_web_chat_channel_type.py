"""allow web_chat channel type

Revision ID: 014
Revises: 013

Widens the channel_connections.channel_type CHECK constraint to include
'web_chat'. No new tables: Web Chat reuses channels, contacts,
contact_identities, conversations and messages.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, Sequence[str], None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD = "channel_type IN ('whatsapp', 'instagram', 'facebook')"
_NEW = "channel_type IN ('whatsapp', 'instagram', 'facebook', 'web_chat')"
_NAME = "ck_channel_connections_channel_type"


def upgrade() -> None:
    op.drop_constraint(_NAME, "channel_connections", type_="check")
    op.create_check_constraint(_NAME, "channel_connections", _NEW)


def downgrade() -> None:
    op.drop_constraint(_NAME, "channel_connections", type_="check")
    op.create_check_constraint(_NAME, "channel_connections", _OLD)
