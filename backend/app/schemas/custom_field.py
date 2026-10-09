from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FIELD_TYPES = {"text", "number", "date", "select", "multiselect", "boolean"}


class CustomFieldResponse(BaseModel):
    id: UUID
    label: str
    key: str
    field_type: str
    options: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomFieldListResponse(BaseModel):
    items: list[CustomFieldResponse]
    total: int


class CustomFieldCreate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    field_type: str = Field(pattern=r"^(text|number|date|select|multiselect|boolean)$")
    options: list[str] | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomFieldUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=60)
    options: list[str] | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContactFieldsUpdate(BaseModel):
    """Set one or more custom-field values on a contact. A null value clears."""

    values: dict[UUID, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
