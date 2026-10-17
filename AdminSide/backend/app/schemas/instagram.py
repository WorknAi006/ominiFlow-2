from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

META_ID_PATTERN = r"^[0-9]{1,32}$"


class InstagramConnectRequest(BaseModel):
    """
    Connect an Instagram channel with the Instagram Professional account id,
    the linked Facebook Page id, and a Page access token. Validation is
    field-level only so a 422 never echoes the token.
    """

    instagram_id: str = Field(pattern=META_ID_PATTERN)
    page_id: str = Field(pattern=META_ID_PATTERN)
    access_token: SecretStr = Field(min_length=1, max_length=4096)

    model_config = ConfigDict(extra="forbid")


class InstagramConnectionCheck(BaseModel):
    """
    Result of a read-only connection health check. Carries only safe,
    non-secret diagnostics; tokens are never included.
    """

    healthy: bool
    detail: str
    webhook_subscribed: bool | None = None
    username: str | None = None
    account_id: str | None = None
    last_event_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
