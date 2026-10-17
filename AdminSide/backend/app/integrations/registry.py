from app.integrations.base import ChannelProvider
from app.integrations.facebook.provider import FacebookProvider
from app.integrations.instagram.provider import InstagramProvider
from app.integrations.web_chat.provider import WebChatProvider
from app.integrations.whatsapp.provider import WhatsAppProvider
from app.models import ChannelType


_PROVIDERS: dict[ChannelType, ChannelProvider] = {
    provider.channel_type: provider
    for provider in (
        WhatsAppProvider(),
        InstagramProvider(),
        FacebookProvider(),
        WebChatProvider(),
    )
}


def get_provider(channel_type: ChannelType | str) -> ChannelProvider:
    return _PROVIDERS[ChannelType(channel_type)]
