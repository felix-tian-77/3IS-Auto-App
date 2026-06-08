from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WorkerRegisterRequest(BaseModel):
    fingerprint: str = Field(min_length=1)
    hostname: str = Field(min_length=1)
    ip_address: str = Field(min_length=1)
    version: str
    tags: Optional[dict] = {}
    adb_serial: str = Field(min_length=1)
    port: int = 8765

class WorkerRegisterResponse(BaseModel):
    worker_id: str
    token: str
    bound_device_id: str
    port: int

class WorkerHeartbeatRequest(BaseModel):
    cpu_usage: float
    memory_usage: float
    battery_level: Optional[int] = None
    storage_free_mb: Optional[int] = None
    screen_locked: Optional[bool] = None
    adb_status: Optional[str] = None