from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DeviceReadyRequest(BaseModel):
    status: str = Field(pattern="^(READY|BUSY|OFFLINE)$")
    sandbox_clear_failed: Optional[bool] = False


class DeviceReadyResponse(BaseModel):
    device_id: str
    status: str
    last_seen_at: datetime


class DownloadAckFile(BaseModel):
    attachment_id: str = Field(min_length=1)
    local_path: str = Field(min_length=1)
    success: bool
    error_reason: Optional[str] = None


class DeviceDownloadAckRequest(BaseModel):
    transaction_id: str = Field(min_length=1)
    files: List[DownloadAckFile]
    all_success: bool
    sandbox_clear_failed: bool = False


class DeviceDownloadAckResponse(BaseModel):
    transaction_id: str
    next_state: str
