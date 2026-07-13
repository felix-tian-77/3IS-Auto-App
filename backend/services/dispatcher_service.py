from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.models.transaction import Transaction, TransactionStatus
from backend.models.worker import Worker, WorkerStatus
from backend.models.device import Device, DeviceStatus
from datetime import datetime

class DispatcherService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_transaction(self, transaction_id: str) -> dict:
        txn_result = await self.db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        transaction = txn_result.scalar_one_or_none()
        if not transaction:
            return {"assigned": False, "reason": "Transaction not found"}

        # Idempotent: if this transaction was already dispatched (e.g. auto-dispatched
        # in create_transaction, then the Worker re-asks via /download-urls), return
        # the existing assignment instead of stealing another worker.
        if transaction.status == TransactionStatus.DISPATCHED and transaction.worker_id:
            return {
                "assigned": True,
                "worker_id": transaction.worker_id,
                "device_id": transaction.device_id,
            }

        result = await self.db.execute(
            select(Worker).where(
                and_(
                    Worker.status == WorkerStatus.ONLINE,
                    Worker.bound_device_id.isnot(None)
                )
            )
        )
        worker = result.scalar_one_or_none()

        if not worker:
            return {"assigned": False, "reason": "No available worker"}

        transaction.status = TransactionStatus.DISPATCHED
        transaction.worker_id = worker.worker_id
        transaction.device_id = worker.bound_device_id

        await self.db.commit()
        return {
            "assigned": True,
            "worker_id": worker.worker_id,
            "device_id": worker.bound_device_id,
        }
