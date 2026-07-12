import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.attachment import Attachment, FileType
from backend.schemas.transaction import TransactionCreateRequest
from backend.storage.local import LocalStorageBackend


REQUIRED_FILES = {
    BusinessType.NEW_VEHICLE: [
        FileType.ID_CARD_FRONT,
        FileType.ID_CARD_BACK,
        FileType.ELECTRONIC_INVOICE,
        FileType.CERTIFICATE,
    ],
    BusinessType.OLD_VEHICLE: [
        FileType.ID_CARD_FRONT,
        FileType.ID_CARD_BACK,
        FileType.DRIVING_LICENSE_FRONT,
        FileType.DRIVING_LICENSE_BACK,
    ],
}

ADDITIONAL_FILES = {
    "tax_exempt": [FileType.TAX_EXEMPT_CERT],
    "is_transfer": [FileType.INSURER_ID_CARD_FRONT, FileType.INSURER_ID_CARD_BACK],
}


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = LocalStorageBackend()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

    def _validate_required_files(self, request: TransactionCreateRequest, file_types: List[str]) -> None:
        required: set[str] = set()

        base_files = REQUIRED_FILES.get(request.business_type, [])
        for ft in base_files:
            required.add(ft.value)

        if request.tax_exempt:
            required.add(FileType.TAX_EXEMPT_CERT.value)
        if request.is_transfer:
            required.add(FileType.INSURER_ID_CARD_FRONT.value)
            required.add(FileType.INSURER_ID_CARD_BACK.value)

        uploaded_types = set(file_types)
        missing = required - uploaded_types
        if missing:
            raise ValueError(f"Missing required files: {', '.join(missing)}")

    async def create_transaction(self, request: TransactionCreateRequest,
                                 files: List[tuple], customer_id: str = "default") -> dict:
        now = datetime.utcnow()
        transaction_id = self._generate_id("TXN")

        file_types = [fm[0].get("file_type") for fm in files]
        self._validate_required_files(request, file_types)

        transaction = Transaction(
            transaction_id=transaction_id,
            external_id=request.external_id,
            business_type=request.business_type,
            status=TransactionStatus.PENDING.value,
            customer_phone_encrypted=request.customer_phone,
            customer_phone_search=request.customer_phone,
            customer_id_no_encrypted=request.customer_id_no,
            submitted_by=customer_id,
            tax_exempt=request.tax_exempt,
            is_transfer=request.is_transfer,
            holder_phone=request.holder_phone,
        )
        self.db.add(transaction)

        attachments = []
        for idx, (file_meta, file_data) in enumerate(files):
            attachment_id = self._generate_id("ATT")
            file_md5 = hashlib.md5(file_data).hexdigest()
            file_sha256 = hashlib.sha256(file_data).hexdigest()
            ext = Path(file_meta["filename"]).suffix.lower()
            file_type = file_meta["file_type"]
            filename = f"{file_type}{ext}"
            storage_key = f"{transaction_id}/{filename}"

            await self.storage.put(storage_key, file_data, file_meta["content_type"])

            attachment = Attachment(
                attachment_id=attachment_id,
                transaction_id=transaction_id,
                customer_id=customer_id,
                file_type=file_type,
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
            "tax_exempt": request.tax_exempt,
            "is_transfer": request.is_transfer,
            "holder_phone": request.holder_phone,
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
