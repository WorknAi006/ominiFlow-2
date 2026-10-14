import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSessionResponse(BaseModel):
    id: uuid.UUID
    device_info: str | None = None
    ip_address: str | None = None
    last_active_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)
