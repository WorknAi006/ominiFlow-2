from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.phone import InvalidPhoneNumberError, normalize_phone


def _validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        normalize_phone(value)
    except InvalidPhoneNumberError as exc:
        raise ValueError(str(exc)) from None
    return value


class ContactIdentitySummary(BaseModel):
    channel_type: str
    external_id: str
    display_name: str | None = None


class ContactTagSummary(BaseModel):
    id: UUID
    name: str
    color: str


class ContactFieldValueOut(BaseModel):
    field_id: UUID
    key: str
    label: str
    field_type: str
    value: object | None = None


class ContactResponse(BaseModel):
    id: UUID
    name: str | None
    phone_number: str | None
    normalized_phone_number: str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    display_name: str | None
    profile_name: str | None
    avatar_url: str | None
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    # Enriched only by the Contacts list/detail; empty elsewhere so existing
    # callers (e.g. the inbox) are unaffected.
    identities: list[ContactIdentitySummary] = []
    tags: list[ContactTagSummary] = []
    field_values: list[ContactFieldValueOut] = []


class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    total: int
    page: int
    page_size: int


class _ContactFields(BaseModel):
    phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    email: EmailStr | None = Field(default=None, max_length=320)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, min_length=1, max_length=150)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    _phone = field_validator("phone_number")(_validate_phone)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str | None) -> str | None:
        return value.lower() if value else value


class ContactCreate(_ContactFields):

    @model_validator(mode="after")
    def require_identity(self) -> "ContactCreate":
        if not self.phone_number and not self.email:
            raise ValueError("phone_number or email is required.")
        return self


class ContactUpdate(_ContactFields):
    is_blocked: bool | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "ContactUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        for field in ("phone_number", "is_blocked"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ContactImportRow(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    phone_number: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=320)

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ContactImportRequest(BaseModel):
    rows: list[ContactImportRow] = Field(min_length=1, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class ContactImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = []
