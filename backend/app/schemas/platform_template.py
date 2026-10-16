import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.template import TemplateResponse


TEMPLATE_NAME_PATTERN = r"^[a-z0-9_]{1,512}$"
LANGUAGE_PATTERN = r"^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?$"
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(\d+)\s*\}\}")


class PlatformTemplateCreate(BaseModel):
    name: str = Field(pattern=TEMPLATE_NAME_PATTERN)
    label: str = Field(min_length=2, max_length=150)
    language: str = Field(pattern=LANGUAGE_PATTERN)
    category: Literal["marketing", "utility"]
    body_text: str = Field(min_length=1, max_length=1024)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("body_text")
    @classmethod
    def placeholders_are_sequential(cls, value: str) -> str:
        numbers = list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(value)))
        if len(numbers) > 10 or numbers != [str(i) for i in range(1, len(numbers) + 1)]:
            raise ValueError("Use numbered placeholders in order, from {{1}}, with at most 10.")
        return value


class PlatformTemplateResponse(BaseModel):
    id: UUID
    name: str
    label: str
    language: str
    category: str
    body_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformTemplateListResponse(BaseModel):
    items: list[PlatformTemplateResponse]
    total: int


class PlatformTemplateAdminStatus(BaseModel):
    is_platform_super_admin: bool


class PlatformTemplateSubmitRequest(BaseModel):
    channel_connection_id: UUID
    body_text: str = Field(min_length=1, max_length=1024)
    examples: list[Annotated[str, Field(min_length=1, max_length=1024)]] = Field(
        default_factory=list,
        max_length=10,
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("body_text")
    @classmethod
    def placeholders_are_sequential(cls, value: str) -> str:
        numbers = list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(value)))
        if len(numbers) > 10 or numbers != [str(i) for i in range(1, len(numbers) + 1)]:
            raise ValueError("Use numbered placeholders in order, from {{1}}, with at most 10.")
        return value


class PlatformTemplateSubmitResponse(BaseModel):
    template: TemplateResponse
    message: str
