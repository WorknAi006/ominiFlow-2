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


class TenantDetailResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    email: EmailStr | None
    phone: str | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUpdateRequest(BaseModel):
    # Only these fields can be changed. Any other field (id, slug,
    # is_active, is_deleted, ...) is rejected with 422.
    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = Field(default=None, max_length=320)
    phone: str | None = Field(
        default=None,
        max_length=20,
        pattern=r"^\+?[0-9 ()-]{7,20}$",
    )
    description: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.lower() if value else value

    @field_validator("description")
    @classmethod
    def empty_description_to_none(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_fields(self) -> "TenantUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Workspace name cannot be null.")

        return self
