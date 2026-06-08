from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import get_db
from backend.services.transaction_service import TransactionService
from backend.schemas.transaction import TransactionResponse, TransactionCreateRequest
import json

class TransactionErrorType(str, Enum):
    MULTIPART_PARTIAL_FAIL = "MULTIPART_PARTIAL_FAIL"
    MD5_MISMATCH = "MD5_MISMATCH"
    FILE_MISSING = "FILE_MISSING"


router = APIRouter()

@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    transaction: str = Form(...),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    txn_data = json.loads(transaction)
    request = TransactionCreateRequest(**txn_data)

    file_data_list = []
    uploaded_ids = []
    failed_ids = []
    for idx, f in enumerate(files):
        content = await f.read()
        file_meta = txn_data["attachments_meta"][idx] if idx < len(txn_data["attachments_meta"]) else {}
        attachment_id = f"ATT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx:04d}"
        uploaded_ids.append(attachment_id)
        file_data_list.append((
            {
                "filename": f.filename,
                "content_type": f.content_type,
                "file_type": file_meta.get("file_type", "OTHER"),
                "file_format": file_meta.get("file_format", "JPG"),
                "description": file_meta.get("description"),
            },
            content
        ))

    expected_count = len(txn_data.get("attachments_meta", []))
    if len(files) < expected_count:
        raise HTTPException(
            status_code=422,
            detail={
                "type": TransactionErrorType.FILE_MISSING.value,
                "message": f"Expected {expected_count} files but received {len(files)}",
                "details": {
                    "uploaded": uploaded_ids,
                    "failed": [],
                    "cleanup_status": "is_orphan=true, GC in 24h"
                }
            }
        )

    service = TransactionService(db)
    result = await service.create_transaction(request, file_data_list)
    return result

@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from backend.models.transaction import Transaction
    result = await db.execute(select(Transaction).where(Transaction.transaction_id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "transaction_id": txn.transaction_id,
        "status": txn.status.value,
        "business_type": txn.business_type.value,
    }