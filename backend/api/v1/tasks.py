from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from backend.db.database import get_db
from backend.models.transaction import Transaction, TransactionStatus
from backend.models.worker import Worker
from backend.models.attachment import Attachment

router = APIRouter()


@router.get("/tasks/poll")
async def poll_task(worker_id: str, db: AsyncSession = Depends(get_db)):
    worker_result = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = worker_result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    txn_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.worker_id == worker_id,
            Transaction.status == TransactionStatus.DISPATCHED.value,
        )
        .order_by(Transaction.created_at.asc())
        .limit(1)
    )
    txn = txn_result.scalar_one_or_none()
    if not txn:
        return {"task": None}

    txn.status = TransactionStatus.ADB_CONNECTING.value
    txn.started_at = datetime.now(timezone.utc)
    await db.commit()

    attachments_result = await db.execute(
        select(Attachment).where(Attachment.transaction_id == txn.transaction_id)
    )
    attachments = [
        {
            "attachment_id": a.attachment_id,
            "file_type": a.file_type,
            "file_format": a.file_format,
            "storage_backend": a.storage_backend,
            "storage_path": a.storage_path,
            "md5": a.md5,
        }
        for a in attachments_result.scalars().all()
    ]

    return {
        "task": {
            "transaction_id": txn.transaction_id,
            "business_type": txn.business_type,
            "flow_id": txn.flow_id,
            "device_id": txn.device_id,
            "customer_phone_encrypted": txn.customer_phone_encrypted,
            "customer_id_no_encrypted": txn.customer_id_no_encrypted,
            "retry_count": txn.retry_count,
            "attachments": attachments,
        }
    }
