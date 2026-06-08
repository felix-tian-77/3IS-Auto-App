from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from backend.db.database import get_db
from backend.models.worker import Worker, WorkerStatus
from backend.models.device import Device, DeviceStatus, ADBStatus
from backend.schemas.worker import WorkerRegisterRequest, WorkerRegisterResponse, WorkerHeartbeatRequest

router = APIRouter()

def generate_worker_id() -> str:
    return f"WKR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

@router.post("/workers/register", response_model=WorkerRegisterResponse)
async def register_worker(request: WorkerRegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Device).where(Device.adb_serial == request.adb_serial)
    )
    device = result.scalar_one_or_none()

    if not device:
        device_id = f"DEV-{uuid.uuid4().hex[:8]}"
        device = Device(
            device_id=device_id,
            adb_serial=request.adb_serial,
            status=DeviceStatus.ONLINE,
            adb_status=ADBStatus.CONNECTED,
        )
        db.add(device)
    else:
        device_id = device.device_id
        device.status = DeviceStatus.ONLINE
        device.adb_status = ADBStatus.CONNECTED

    worker_id = generate_worker_id()
    token = uuid.uuid4().hex

    worker = Worker(
        worker_id=worker_id,
        fingerprint=request.fingerprint,
        hostname=request.hostname,
        ip_address=request.ip_address,
        version=request.version,
        tags=str(request.tags),
        bound_device_id=device_id,
        port=request.port,
        status=WorkerStatus.ONLINE,
        registered_at=datetime.utcnow(),
        last_heartbeat_at=datetime.utcnow(),
    )
    db.add(worker)

    device.worker_id = worker_id
    await db.commit()

    return WorkerRegisterResponse(
        worker_id=worker_id,
        token=token,
        bound_device_id=device_id,
        port=request.port,
    )

@router.post("/workers/heartbeat")
async def worker_heartbeat(
    worker_id: str,
    request: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Worker).where(Worker.worker_id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.cpu_usage = request.cpu_usage
    worker.memory_usage = request.memory_usage
    worker.last_heartbeat_at = datetime.utcnow()
    worker.status = WorkerStatus.ONLINE

    if worker.bound_device_id:
        device_result = await db.execute(
            select(Device).where(Device.device_id == worker.bound_device_id)
        )
        device = device_result.scalar_one_or_none()
        if device:
            if request.battery_level is not None:
                device.battery_level = request.battery_level
            if request.storage_free_mb is not None:
                device.storage_free_mb = request.storage_free_mb
            if request.screen_locked is not None:
                device.screen_locked = request.screen_locked
            if request.adb_status:
                device.adb_status = ADBStatus(request.adb_status)
            device.last_seen_at = datetime.utcnow()

    await db.commit()
    return {"status": "ok"}