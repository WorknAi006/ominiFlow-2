from app.integrations.base import UnimplementedChannelProvider
from app.models import ChannelType


class InstagramProvider(UnimplementedChannelProvider):
    """
    Instagram Messaging provider (not implemented yet).

    Planned mapping:
    - external_account_id  -> Instagram professional account id
    - external_business_id -> linked Facebook page id
    - access_token         -> page / Instagram user access token
    """

    channel_type = ChannelType.INSTAGRAM
    display_name = "Instagram"
