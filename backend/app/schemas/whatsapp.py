from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


META_ID_PATTERN = r"^[0-9]{1,32}$"


class WhatsAppConnectRequest(BaseModel):
    """
    Connect a WhatsApp channel. Provide exactly one of:
    - access_token: a system user / business integration token, or
    - code: an Embedded Signup authorization code (exchanged server-side).

    Validation is field-level only so a 422 never echoes the whole body.
    The "exactly one" rule is enforced in the service.
    """

    phone_number_id: str | None = Field(default=None, pattern=META_ID_PATTERN)
    waba_id: str | None = Field(default=None, pattern=META_ID_PATTERN)
    access_token: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096,
    )
    code: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096,
    )

    model_config = ConfigDict(extra="forbid")


class WhatsAppConnectionCheck(BaseModel):
    """
    Result of a read-only connection health check. Carries only safe,
    non-secret diagnostics; tokens are never included.
    """

    healthy: bool
    detail: str
    webhook_subscribed: bool | None = None
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    last_event_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WhatsAppEmbeddedSignupConfig(BaseModel):
    app_id: str = Field(pattern=META_ID_PATTERN)
    config_id: str = Field(min_length=1, max_length=100)
    graph_api_version: str = Field(pattern=r"^v[0-9]{1,3}\.[0-9]{1,2}$")
