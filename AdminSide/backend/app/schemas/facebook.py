from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

META_ID_PATTERN = r"^[0-9]{1,32}$"


class FacebookConnectRequest(BaseModel):
    """
    Connect a Facebook Messenger channel with a Page id and a Page access
    token. Validation is field-level only so a 422 never echoes the token.
    """

    page_id: str = Field(pattern=META_ID_PATTERN)
    access_token: SecretStr = Field(min_length=1, max_length=4096)

    model_config = ConfigDict(extra="forbid")


class FacebookConnectionCheck(BaseModel):
    """
    Result of a read-only connection health check. Carries only safe,
    non-secret diagnostics; tokens are never included.
    """

    healthy: bool
    detail: str
    webhook_subscribed: bool | None = None
    page_name: str | None = None
    last_event_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
