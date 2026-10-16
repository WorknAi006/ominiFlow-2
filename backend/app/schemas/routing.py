from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoutingConfigResponse(BaseModel):
    fallback_action: Literal["none", "flow", "ai"]
    fallback_flow_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class RoutingConfigUpdate(BaseModel):
    fallback_action: Literal["none", "flow", "ai"]
    fallback_flow_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")
