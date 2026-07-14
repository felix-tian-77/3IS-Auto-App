from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.device import Device, DeviceStatus
from backend.schemas.device import (
    DeviceReadyRequest,
    DeviceReadyResponse,
)

router = APIRouter()


@router.post("/devices/{device_id}/ready", response_model=DeviceReadyResponse)
async def device_ready(
    device_id: str,
    req: DeviceReadyRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        device = Device(
            device_id=device_id,
            status=DeviceStatus(req.status) if req.status in DeviceStatus.__members__ else DeviceStatus.ONLINE,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(device)
    else:
        device.status = DeviceStatus(req.status) if req.status in DeviceStatus.__members__ else device.status
        device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(device)
    return DeviceReadyResponse(
        device_id=device.device_id,
        status=req.status,
        last_seen_at=device.last_seen_at,
    )
