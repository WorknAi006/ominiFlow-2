from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class AiConfigUpdate(BaseModel):
    provider: Literal["platform", "openai"] = Field(..., description="The AI provider to use")
    model: str = Field(..., description="The AI model selection")
    api_key: str | None = Field(None, description="The custom API key if providing one")

class AiConfigResponse(BaseModel):
    provider: str
    model: str
    has_api_key: bool
    is_verified: bool = False
    
    model_config = ConfigDict(from_attributes=True)
