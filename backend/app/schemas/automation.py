from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.automation import (
    AutomationMatchType,
    AutomationRunStatus,
    AutomationThenMode,
    AutomationTrigger,
)

# Allowed condition fields, operators and action types. Kept here so the API
# can serve them to the builder UI and validate incoming rules against them.
CONDITION_FIELDS = (
    "existing_contact", "contact_tags", "source", "chat_status",
    "chat_mode", "assigned_agent", "has_agent_assigned", "account",
)
CONDITION_OPERATORS = (
    "is", "is_not", "contains", "doesnt_contain", "starts_with",
    "ends_with", "has_any", "has_value", "has_no_value",
)
ACTION_TYPES = (
    "add_tags", "remove_tags", "set_custom_field", "clear_custom_field",
    "subscribe_to_drip", "unsubscribe_from_drip", "append_to_google_sheet",
    "set_chat_status", "transfer_to_bot",
)


class Condition(BaseModel):
    field: str = Field(min_length=1, max_length=40)
    operator: str = Field(min_length=1, max_length=20)
    value: str = Field(default="", max_length=500)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def check(self):
        if self.field not in CONDITION_FIELDS:
            raise ValueError(f"Unknown condition field: {self.field}")
        if self.operator not in CONDITION_OPERATORS:
            raise ValueError(f"Unknown operator: {self.operator}")
        return self


class Action(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    config: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def check(self):
        if self.type not in ACTION_TYPES:
            raise ValueError(f"Unknown action type: {self.type}")
        return self


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    trigger_type: AutomationTrigger
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    match_type: AutomationMatchType = AutomationMatchType.ALL
    conditions: list[Condition] = Field(default_factory=list, max_length=25)
    then_mode: AutomationThenMode = AutomationThenMode.RUN_ACTIONS
    flow_ref: str | None = Field(default=None, max_length=150)
    actions: list[Action] = Field(default_factory=list, max_length=25)
    is_active: bool = True
    runs_first: int = Field(default=0, ge=0, le=9999)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AutomationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    trigger_type: AutomationTrigger | None = None
    trigger_config: dict[str, Any] | None = None
    match_type: AutomationMatchType | None = None
    conditions: list[Condition] | None = Field(default=None, max_length=25)
    then_mode: AutomationThenMode | None = None
    flow_ref: str | None = Field(default=None, max_length=150)
    actions: list[Action] | None = Field(default=None, max_length=25)
    is_active: bool | None = None
    runs_first: int | None = Field(default=None, ge=0, le=9999)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class AutomationResponse(BaseModel):
    id: UUID
    name: str
    trigger_type: AutomationTrigger
    trigger_config: dict[str, Any]
    match_type: AutomationMatchType
    conditions: list[dict[str, Any]]
    then_mode: AutomationThenMode
    flow_ref: str | None
    actions: list[dict[str, Any]]
    is_active: bool
    runs_first: int
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AutomationListResponse(BaseModel):
    items: list[AutomationResponse]
    total: int
    page: int
    page_size: int


class AutomationRunResponse(BaseModel):
    id: UUID
    automation_id: UUID
    trigger_type: AutomationTrigger
    contact_id: UUID | None
    conversation_id: UUID | None
    status: AutomationRunStatus
    matched: bool
    actions_run: int
    detail: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AutomationRunListResponse(BaseModel):
    items: list[AutomationRunResponse]
    total: int
    page: int
    page_size: int


class AutomationMetrics(BaseModel):
    total_rules: int
    active_rules: int
    runs_total: int
    runs_success: int
    runs_failed: int
    runs_skipped: int
    last_run_at: datetime | None


class OptionItem(BaseModel):
    value: str
    label: str


class ActionOption(OptionItem):
    config_fields: list[dict[str, Any]] = Field(default_factory=list)


class AutomationOptions(BaseModel):
    """Catalogue the builder UI renders — triggers, condition fields, operators, actions."""

    triggers: list[OptionItem]
    condition_fields: list[OptionItem]
    operators: list[OptionItem]
    actions: list[ActionOption]
    chat_statuses: list[OptionItem]
