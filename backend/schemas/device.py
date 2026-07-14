from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DeviceReadyRequest(BaseModel):
    status: str = Field(pattern="^(READY|BUSY|OFFLINE)$")
    sandbox_clear_failed: Optional[bool] = False


class DeviceReadyResponse(BaseModel):
    device_id: str
    status: str
    last_seen_at: datetime
