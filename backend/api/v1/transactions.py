from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from backend.db.database import get_db
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.attachment import Attachment
from backend.services.transaction_service import TransactionService
from backend.schemas.transaction import (
    TransactionResponse,
    TransactionCreateRequest,
    AttachmentsDeliveredRequest,
    AttachmentsDeliveredResponse,
)
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
        attachment_id = f"A-{datetime.now().strftime('%Y%m%d')}-{idx:04d}"
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
    try:
        result = await service.create_transaction(request, file_data_list)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result

@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    business_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Transaction)
    count_query = select(func.count(Transaction.transaction_id))

    conditions = []
    if search:
        search_filter = or_(
            Transaction.customer_phone_search.contains(search),
            Transaction.transaction_id.contains(search),
        )
        conditions.append(search_filter)
    if status:
        conditions.append(Transaction.status == status)
    if business_type:
        conditions.append(Transaction.business_type == business_type)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    txns = result.scalars().all()

    items = []
    for t in txns:
        items.append({
            "transaction_id": t.transaction_id,
            "business_type": t.business_type,
            "status": t.status,
            "customer_phone_encrypted": t.customer_phone_encrypted,
            "retry_count": t.retry_count,
            "tax_exempt": t.tax_exempt,
            "is_transfer": t.is_transfer,
            "holder_phone": t.holder_phone,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

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
        "status": txn.status,
        "business_type": txn.business_type,
        "tax_exempt": txn.tax_exempt,
        "is_transfer": txn.is_transfer,
        "holder_phone": txn.holder_phone,
    }


@router.post(
    "/transactions/{transaction_id}/attachments-delivered",
    response_model=AttachmentsDeliveredResponse,
)
async def attachments_delivered(
    transaction_id: str,
    req: AttachmentsDeliveredRequest,
    db: AsyncSession = Depends(get_db),
):
    txn_result = await db.execute(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    )
    txn = txn_result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=404, detail="transaction not found")

    for f in req.files:
        att_result = await db.execute(
            select(Attachment).where(Attachment.attachment_id == f.attachment_id)
        )
        att = att_result.scalar_one_or_none()
        if att is not None:
            att.local_path = f.local_path

    txn.status = TransactionStatus.READY.value
    await db.commit()

    return AttachmentsDeliveredResponse(
        transaction_id=transaction_id,
        next_state="READY",
    )
