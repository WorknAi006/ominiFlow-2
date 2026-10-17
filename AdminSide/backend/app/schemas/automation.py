from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.automation import AutomationExecutionStatus, AutomationNodeType, AutomationStatus, AutomationTrigger


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    trigger_type: AutomationTrigger = AutomationTrigger.INBOUND_MESSAGE
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AutomationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class AutomationNodeInput(BaseModel):
    id: UUID
    node_type: AutomationNodeType
    name: str = Field(min_length=1, max_length=150)
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = Field(ge=0, le=49)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AutomationNodeCreate(BaseModel):
    node_type: AutomationNodeType
    name: str = Field(min_length=1, max_length=150)
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0, le=49)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AutomationNodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    config: dict[str, Any] | None = None
    sort_order: int | None = Field(default=None, ge=0, le=49)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class AutomationEdgeInput(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    branch: str | None = Field(default=None, pattern=r"^(true|false)$")
    model_config = ConfigDict(extra="forbid")


class AutomationFlowSave(BaseModel):
    nodes: list[AutomationNodeInput] = Field(min_length=1, max_length=50)
    edges: list[AutomationEdgeInput] = Field(max_length=100)
    model_config = ConfigDict(extra="forbid")


class AutomationNodeResponse(BaseModel):
    id: UUID
    node_type: AutomationNodeType
    name: str
    config: dict[str, Any]
    sort_order: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AutomationEdgeResponse(BaseModel):
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    branch: str | None
    model_config = ConfigDict(from_attributes=True)


class AutomationResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: AutomationStatus
    trigger_type: AutomationTrigger
    version: int
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AutomationDetailResponse(AutomationResponse):
    nodes: list[AutomationNodeResponse]
    edges: list[AutomationEdgeResponse]


class AutomationListResponse(BaseModel):
    items: list[AutomationResponse]
    total: int
    page: int
    page_size: int


class ValidationIssue(BaseModel):
    code: str
    message: str
    node_id: UUID | None = None


class AutomationValidationResponse(BaseModel):
    valid: bool
    issues: list[ValidationIssue]


class SimulationInput(BaseModel):
    message: str = Field(min_length=1, max_length=4096)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SimulationStep(BaseModel):
    node_id: UUID
    node_type: AutomationNodeType
    result: str
    detail: str


class SimulationResponse(BaseModel):
    valid: bool
    trigger_matched: bool
    steps: list[SimulationStep]
    final_result: str


class AutomationExecutionResponse(BaseModel):
    id: UUID
    automation_id: UUID
    automation_name: str
    conversation_id: UUID
    contact_id: UUID
    trigger_message_id: UUID
    automation_version: int
    status: AutomationExecutionStatus
    current_node_id: UUID | None
    attempt_count: int
    max_attempts: int
    step_count: int
    next_retry_at: datetime | None
    last_error_type: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_summary: str | None
    created_at: datetime


class AutomationExecutionListResponse(BaseModel):
    items: list[AutomationExecutionResponse]
    total: int
    page: int
    page_size: int


class AutomationExecutionMetrics(BaseModel):
    total: int
    completed: int
    failed: int
    running: int
    retrying: int
    queued: int
    last_execution_at: datetime | None
    last_failure: str | None


class AutomationWorkerHealth(BaseModel):
    status: str
    last_seen_at: datetime | None
    processed_count: int


class AutomationExecutionLogResponse(BaseModel):
    id: UUID
    node_id: UUID | None
    level: str
    summary: str
    details: dict[str, Any] | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
