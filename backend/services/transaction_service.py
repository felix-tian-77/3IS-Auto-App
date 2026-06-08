import uuid
import hashlib
from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.attachment import Attachment, FileType, FileFormat, StorageBackendType
from backend.schemas.transaction import TransactionCreateRequest, AttachmentResponse
from backend.storage.local import LocalStorageBackend

class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = LocalStorageBackend()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

    async def create_transaction(self, request: TransactionCreateRequest,
                                 files: List[tuple], customer_id: str = "default") -> dict:
        transaction_id = self._generate_id("TXN")
        business_type = BusinessType(request.business_type)

        transaction = Transaction(
            transaction_id=transaction_id,
            external_id=request.external_id,
            business_type=business_type,
            status=TransactionStatus.PENDING,
            customer_phone_encrypted=request.customer_phone,
            customer_id_no_encrypted=request.customer_id_no,
            submitted_by=customer_id,
        )
        self.db.add(transaction)

        attachments = []
        for idx, (file_meta, file_data) in enumerate(files):
            attachment_id = self._generate_id("ATT")
            file_md5 = hashlib.sha256(file_data).hexdigest()
            filename = f"{attachment_id}_{file_meta['filename']}"
            storage_key = f"{customer_id}/{attachment_id}/{filename}"

            await self.storage.put(storage_key, file_data, file_meta["content_type"])

            attachment = Attachment(
                attachment_id=attachment_id,
                transaction_id=transaction_id,
                customer_id=customer_id,
                file_type=FileType(file_meta["file_type"]),
                description=file_meta.get("description"),
                file_format=FileFormat(file_meta["file_format"]),
                file_size=len(file_data),
                storage_backend=StorageBackendType.LOCAL,
                storage_path=storage_key,
                md5=file_md5,
                uploaded_at=datetime.utcnow(),
            )
            self.db.add(attachment)
            attachments.append(attachment)

        await self.db.commit()

        pending_result = await self.db.execute(select(Transaction).where(Transaction.status == TransactionStatus.PENDING))
        pending_count = len(pending_result.scalars().all())
        estimated_wait = pending_count * 30

        return {
            "transaction_id": transaction_id,
            "status": "PENDING",
            "submitted_at": datetime.utcnow().isoformat(),
            "estimated_wait": estimated_wait,
            "attachments": [
                {
                    "attachment_id": a.attachment_id,
                    "file_type": a.file_type.value,
                    "description": a.description,
                    "file_size": a.file_size,
                    "md5": a.md5,
                    "storage_backend": a.storage_backend.value,
                    "storage_path": a.storage_path,
                }
                for a in attachments
            ]
        }