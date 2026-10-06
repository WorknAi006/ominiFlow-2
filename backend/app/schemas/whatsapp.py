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

    phone_number_id: str = Field(pattern=META_ID_PATTERN)
    waba_id: str = Field(pattern=META_ID_PATTERN)
    access_token: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096,
    )
    code: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096,
    )

    model_config = ConfigDict(extra="forbid")
