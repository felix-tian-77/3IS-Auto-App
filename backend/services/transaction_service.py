import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.transaction import Transaction, TransactionStatus
from backend.models.attachment import Attachment
from backend.schemas.transaction import TransactionCreateRequest
from backend.storage.local import LocalStorageBackend


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = LocalStorageBackend()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

    async def create_transaction(self, request: TransactionCreateRequest,
                                 files: List[tuple], customer_id: str = "default") -> dict:
        now = datetime.utcnow()
        transaction_id = self._generate_id("TXN")

        transaction = Transaction(
            transaction_id=transaction_id,
            external_id=request.external_id,
            business_type=request.business_type,
            status=TransactionStatus.PENDING.value,
            customer_phone_encrypted=request.customer_phone,
            customer_phone_search=request.customer_phone,
            customer_id_no_encrypted=request.customer_id_no,
            submitted_by=customer_id,
        )
        self.db.add(transaction)

        attachments = []
        date_str = now.strftime("%Y-%m-%d")
        for idx, (file_meta, file_data) in enumerate(files):
            attachment_id = self._generate_id("ATT")
            file_md5 = hashlib.md5(file_data).hexdigest()
            file_sha256 = hashlib.sha256(file_data).hexdigest()
            ext = Path(file_meta["filename"]).suffix.lower()
            filename = f"{transaction_id}_{idx + 1:03d}{ext}"
            storage_key = f"{date_str}/{transaction_id}/{filename}"

            await self.storage.put(storage_key, file_data, file_meta["content_type"])

            attachment = Attachment(
                attachment_id=attachment_id,
                transaction_id=transaction_id,
                customer_id=customer_id,
                file_type=file_meta["file_type"],
                description=file_meta.get("description"),
                file_format=file_meta["file_format"],
                file_size=len(file_data),
                storage_backend="local",
                storage_path=storage_key,
                md5=file_md5,
                sha256=file_sha256,
                uploaded_at=now,
            )
            self.db.add(attachment)
            attachments.append(attachment)

        await self.db.commit()

        return {
            "transaction_id": transaction_id,
            "status": TransactionStatus.PENDING.value,
            "submitted_at": now.isoformat(),
            "estimated_wait": 0,
            "attachments": [
                {
                    "attachment_id": a.attachment_id,
                    "file_type": a.file_type,
                    "description": a.description,
                    "file_size": a.file_size,
                    "md5": a.md5,
                    "sha256": a.sha256,
                    "storage_backend": a.storage_backend,
                    "storage_path": a.storage_path,
                }
                for a in attachments
            ]
        }
