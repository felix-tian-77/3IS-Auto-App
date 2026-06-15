from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.device import Device, DeviceStatus
from backend.models.attachment import Attachment
from backend.models.transaction import Transaction
from backend.schemas.device import (
    DeviceReadyRequest,
    DeviceReadyResponse,
    DeviceDownloadAckRequest,
    DeviceDownloadAckResponse,
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
        # First-ever ready from this device: create a minimal record
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


@router.post(
    "/devices/{device_id}/download-ack",
    response_model=DeviceDownloadAckResponse,
)
async def device_download_ack(
    device_id: str,
    req: DeviceDownloadAckRequest,
    db: AsyncSession = Depends(get_db),
):
    # Mark device busy → idle based on the ack outcome
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    device.last_seen_at = datetime.now(timezone.utc)
    if req.all_success and not req.sandbox_clear_failed:
        device.status = DeviceStatus.ONLINE
        next_state = "READY"
    else:
        device.status = DeviceStatus.BUSY
        next_state = "RETRY_REQUIRED"

    # Stamp the transaction's finish time when the full download set succeeded.
    # Spec §3.2.2 mandates `completed_at` in the ack body; `Transaction` tracks
    # this as `finished_at` (see backend/models/transaction.py).
    if req.all_success:
        txn_result = await db.execute(
            select(Transaction).where(Transaction.transaction_id == req.transaction_id)
        )
        txn = txn_result.scalar_one_or_none()
        if txn is not None:
            txn.finished_at = req.completed_at

    # Persist local_path back to the matching attachment rows
    for f in req.files:
        att_result = await db.execute(
            select(Attachment).where(Attachment.attachment_id == f.attachment_id)
        )
        att = att_result.scalar_one_or_none()
        if att is not None and f.success:
            att.local_path = f.local_path

    await db.commit()
    return DeviceDownloadAckResponse(transaction_id=req.transaction_id, next_state=next_state)
