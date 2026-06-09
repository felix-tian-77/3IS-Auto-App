from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List
import uuid
from backend.db.database import get_db
from backend.models.worker import Worker, WorkerStatus
from backend.models.device import Device, DeviceStatus, ADBStatus
from backend.models.transaction import Transaction, TransactionStatus
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
        token=token,
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

@router.get("/workers")
async def list_workers(db: AsyncSession = Depends(get_db)):
    HEARTBEAT_TIMEOUT = 60

    result = await db.execute(select(Worker))
    workers = result.scalars().all()

    device_ids = [w.bound_device_id for w in workers if w.bound_device_id]
    devices_by_id: dict = {}
    if device_ids:
        dev_result = await db.execute(
            select(Device).where(Device.device_id.in_(device_ids))
        )
        for d in dev_result.scalars().all():
            devices_by_id[d.device_id] = d

    now = datetime.utcnow()
    worker_list = []

    for w in workers:
        is_online = False
        if w.last_heartbeat_at and w.status == WorkerStatus.ONLINE:
            elapsed = (now - w.last_heartbeat_at).total_seconds()
            is_online = elapsed < HEARTBEAT_TIMEOUT

        device_data = None
        if w.bound_device_id and w.bound_device_id in devices_by_id:
            device = devices_by_id[w.bound_device_id]
            device_data = {
                "device_id": device.device_id,
                "model": device.model,
                "android_version": device.android_version,
                "battery_level": device.battery_level,
                "storage_free_mb": device.storage_free_mb,
                "status": device.status.value,
            }

        worker_list.append({
            "worker_id": w.worker_id,
            "hostname": w.hostname,
            "ip_address": w.ip_address,
            "version": w.version,
            "cpu_usage": w.cpu_usage,
            "memory_usage": w.memory_usage,
            "status": "ONLINE" if is_online else "OFFLINE",
            "last_heartbeat_at": w.last_heartbeat_at.isoformat() if w.last_heartbeat_at else None,
            "device": device_data,
        })

    processing_result = await db.execute(
        select(func.count(Transaction.transaction_id)).where(
            Transaction.status.in_([
                TransactionStatus.DISPATCHED,
                TransactionStatus.ADB_CONNECTING,
                TransactionStatus.DOWNLOADING,
                TransactionStatus.READY,
                TransactionStatus.RUNNING,
            ])
        )
    )
    processing = processing_result.scalar() or 0

    queued_result = await db.execute(
        select(func.count(Transaction.transaction_id)).where(
            Transaction.status == TransactionStatus.PENDING
        )
    )
    queued = queued_result.scalar() or 0

    online_count = sum(1 for w in worker_list if w["status"] == "ONLINE")
    offline_count = len(worker_list) - online_count

    return {
        "workers": worker_list,
        "stats": {
            "online": online_count,
            "offline": offline_count,
            "processing": processing,
            "queued": queued,
        },
    }