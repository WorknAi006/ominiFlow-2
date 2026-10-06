from app.integrations.base import UnimplementedChannelProvider
from app.models import ChannelType


class FacebookProvider(UnimplementedChannelProvider):
    """
    Facebook Messenger provider (not implemented yet).

    Planned mapping:
    - external_account_id  -> Facebook page id
    - external_business_id -> Meta business id
    - access_token         -> page access token
    """

    channel_type = ChannelType.FACEBOOK
    display_name = "Facebook"
