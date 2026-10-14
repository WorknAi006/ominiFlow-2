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
    header_text: str | None = Field(default=None, max_length=60)
    body_text: str = Field(min_length=1, max_length=1024)
    footer_text: str | None = Field(default=None, max_length=60)
    buttons: list[str] = Field(default_factory=list, max_length=11)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


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
        required = {"text": "text", "payload": "payload"}.get(self.type, "link")
        if getattr(self, required) is None:
            raise ValueError(f"{self.type} parameters require '{required}'.")

        allowed = {required, "parameter_name"} | ({"filename"} if self.type == "document" else set())
        extra = [
            name for name in ("text", "link", "filename", "payload", "parameter_name")
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
