from datetime import datetime, timezone
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.models import ChannelStatus, ChannelType


EXTERNAL_ID_PATTERN = r"^[A-Za-z0-9._:@+-]+$"


class ChannelConnectionResponse(BaseModel):
    id: UUID
    name: str
    channel_type: ChannelType
    status: ChannelStatus
    external_account_id: str | None
    external_business_id: str | None
    # Whether encrypted credentials are stored. Credentials themselves
    # are never returned.
    has_credentials: bool
    token_expires_at: datetime | None
    is_active: bool
    last_connected_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChannelConnectionListResponse(BaseModel):
    items: list[ChannelConnectionResponse]
    total: int
    page: int
    page_size: int


class ChannelConnectionCreate(BaseModel):
    channel_type: ChannelType
    name: str = Field(min_length=2, max_length=150)
    external_account_id: str | None = Field(
        default=None, min_length=1, max_length=255, pattern=EXTERNAL_ID_PATTERN,
    )
    external_business_id: str | None = Field(
        default=None, min_length=1, max_length=255, pattern=EXTERNAL_ID_PATTERN,
    )
    # Optional provider credentials. Encrypted before storage and never
    # returned. Provider OAuth flows will replace manual entry later.
    access_token: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096,
    )
    refresh_token: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096,
    )
    token_expires_at: datetime | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # Field-level validators (not a model validator) so a validation
    # error never echoes the whole body, including tokens, back in a 422.

    @field_validator("refresh_token")
    @classmethod
    def refresh_requires_access(
        cls,
        value: SecretStr | None,
        info: ValidationInfo,
    ) -> SecretStr | None:
        if value is not None and info.data.get("access_token") is None:
            raise ValueError("refresh_token requires access_token.")

        return value

    @field_validator("token_expires_at")
    @classmethod
    def validate_expiry(
        cls,
        value: datetime | None,
        info: ValidationInfo,
    ) -> datetime | None:
        if value is None:
            return None

        if info.data.get("access_token") is None:
            raise ValueError("token_expires_at requires access_token.")

        if value.tzinfo is None:
            raise ValueError("token_expires_at must include a timezone.")

        if value <= datetime.now(timezone.utc):
            raise ValueError("token_expires_at must be in the future.")

        return value


class ChannelConnectionUpdate(BaseModel):
    # Credentials are intentionally not editable here; they will change
    # only through provider-specific connect/reconnect flows.
    name: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool | None = None

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @model_validator(mode="after")
    def validate_fields(self) -> "ChannelConnectionUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")

        return self
