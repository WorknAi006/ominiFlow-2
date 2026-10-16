import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TEMPLATE_NAME_PATTERN = r"^[a-z0-9_]{1,512}$"
LANGUAGE_PATTERN = r"^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?$"


class LocalTemplateCreate(BaseModel):
    """Create a local (draft) template. WhatsApp requires Meta approval before
    it becomes usable, so drafts are stored with status ``draft`` and are not
    sendable until synced as approved."""

    channel_connection_id: UUID
    name: str = Field(pattern=TEMPLATE_NAME_PATTERN)
    language: str = Field(pattern=LANGUAGE_PATTERN)
    category: str | None = Field(default=None, max_length=30)
    header_format: Literal["NONE", "TEXT", "IMAGE", "VIDEO", "DOCUMENT"] = "NONE"
    header_text: str | None = Field(default=None, max_length=60)
    body_text: str = Field(min_length=1, max_length=1024)
    footer_text: str | None = Field(default=None, max_length=60)
    buttons: list[str] = Field(default_factory=list, max_length=11)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LocalTemplateSubmission(BaseModel):
    channel_connection_id: UUID
    name: str = Field(pattern=TEMPLATE_NAME_PATTERN)
    language: str = Field(pattern=LANGUAGE_PATTERN)
    category: Literal["MARKETING", "UTILITY", "AUTHENTICATION"]
    header_format: Literal["NONE", "TEXT", "IMAGE", "VIDEO", "DOCUMENT"] = "NONE"
    header_text: str | None = Field(default=None, max_length=60)
    body_text: str = Field(min_length=1, max_length=1024)
    footer_text: str | None = Field(default=None, max_length=60)
    buttons: list[str] = Field(default_factory=list, max_length=3)
    body_examples: list[str] = Field(default_factory=list, max_length=10)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def valid_examples_and_header(self) -> "LocalTemplateSubmission":
        placeholders = list(dict.fromkeys(re.findall(r"\{\{\s*(\d+)\s*\}\}", self.body_text)))
        if len(placeholders) > 10 or placeholders != [str(i) for i in range(1, len(placeholders) + 1)]:
            raise ValueError("Use numbered body placeholders in order, from {{1}}, with at most 10.")
        if len(self.body_examples) != len(placeholders) or any(not value.strip() for value in self.body_examples):
            raise ValueError("Provide one non-empty example value for each body placeholder.")
        if self.header_format == "TEXT" and not (self.header_text or "").strip():
            raise ValueError("Text headers require header text.")
        if self.header_format != "TEXT" and self.header_text:
            raise ValueError("Header text can only be set for a text header.")
        if any(not button.strip() or len(button) > 25 for button in self.buttons):
            raise ValueError("Quick-reply button labels must be between 1 and 25 characters.")
        return self


class TemplateResponse(BaseModel):
    id: UUID
    channel_connection_id: UUID
    external_template_id: str | None
    name: str
    language: str
    category: str | None
    status: str
    is_active: bool
    is_usable: bool
    components: list[dict[str, Any]]
    parameter_format: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int


class TemplateSyncResponse(BaseModel):
    received: int
    created: int
    updated: int
    deactivated: int
    skipped: int


# ---------- send-time parameters ----------

class TemplateParameter(BaseModel):
    """
    One template variable value. Supported: text, media header link
    (image/video/document) and quick-reply payload.
    """

    type: Literal["text", "image", "video", "document", "payload"]
    text: str | None = Field(default=None, min_length=1, max_length=1024)
    parameter_name: str | None = Field(default=None, pattern=r"^[a-z_][a-z0-9_]{0,63}$")
    link: str | None = Field(default=None, max_length=2000)
    id: str | None = Field(default=None, min_length=1, max_length=255)
    filename: str | None = Field(default=None, min_length=1, max_length=240)
    payload: str | None = Field(default=None, min_length=1, max_length=256)

    model_config = ConfigDict(extra="forbid")

    @field_validator("link")
    @classmethod
    def https_link(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(value)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("link must be a public https URL without credentials.")
        return value

    @model_validator(mode="after")
    def fields_match_type(self) -> "TemplateParameter":
        if self.type in ("text", "payload"):
            required = self.type
            if getattr(self, required) is None:
                raise ValueError(f"{self.type} parameters require '{required}'.")
            media_fields: set[str] = set()
        else:
            if (self.link is None) == (self.id is None):
                raise ValueError(f"{self.type} parameters require exactly one of 'link' or 'id'.")
            required = None
            media_fields = {"link", "id"}
        allowed = ({required} if required else media_fields) | {"parameter_name"} | (
            {"filename"} if self.type == "document" else set()
        )
        extra = [
            name for name in ("text", "link", "id", "filename", "payload", "parameter_name")
            if getattr(self, name) is not None and name not in allowed
        ]
        if extra:
            raise ValueError(f"Unexpected fields for {self.type}: {', '.join(extra)}.")
        return self


class TemplateComponentInput(BaseModel):
    type: Literal["header", "body", "button"]
    sub_type: Literal["url", "quick_reply"] | None = None
    index: int | None = Field(default=None, ge=0, le=9)
    parameters: list[TemplateParameter] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def button_fields(self) -> "TemplateComponentInput":
        is_button = self.type == "button"
        if is_button != (self.sub_type is not None) or is_button != (self.index is not None):
            raise ValueError("sub_type and index are required for buttons only.")
        return self


# ---------- AI template generation ----------

class AiTemplateGenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    count: int = Field(default=10, ge=1, le=10)
    category: str | None = Field(default=None, max_length=30)
    language: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AiTemplateDraft(BaseModel):
    name: str
    category: str
    language: str
    # none | text | image | video | document
    header_type: str = "none"
    header_text: str | None = None
    body_text: str
    footer_text: str | None = None
    buttons: list[str] = Field(default_factory=list)


class AiTemplateGenerateResponse(BaseModel):
    items: list[AiTemplateDraft]
    credits_used: float
    balance: float
