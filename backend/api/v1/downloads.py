from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time
import uuid
from backend.db.database import get_db
from backend.models.download_url import DownloadUrl
from backend.models.attachment import Attachment
from backend.storage.local import LocalStorageBackend
from backend.services.url_signature_service import URLSignatureService
from backend.services.dispatcher_service import DispatcherService

router = APIRouter()
storage = LocalStorageBackend()
url_service = URLSignatureService()

@router.post("/transactions/{transaction_id}/download-urls")
async def generate_download_urls(transaction_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    dispatcher = DispatcherService(db)
    assignment = await dispatcher.assign_transaction(transaction_id)

    result = await db.execute(
        select(Attachment).where(Attachment.transaction_id == transaction_id)
    )
    attachments = result.scalars().all()

    base = f"{request.url.scheme}://{request.url.netloc}"
    download_urls = []
    expires_at = int(time.time()) + 300

    for att in attachments:
        url_id = f"DURL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        url_path = f"/api/v1/downloads/{url_id}"
        customer_id = att.customer_id or "default"

        token = url_service.generate_token(
            url_path=url_path,
            expires_at=expires_at,
            device_id=assignment.get("device_id", ""),
            attachment_id=att.attachment_id,
            customer_id=customer_id,
        )

        signed_url = f"{base}{url_path}?token={token}&expires={expires_at}&device_id={assignment.get('device_id', '')}&attachment_id={att.attachment_id}&customer_id={customer_id}"

        download_url = DownloadUrl(
            url_id=url_id,
            transaction_id=transaction_id,
            attachment_id=att.attachment_id,
            signed_url=signed_url,
            expires_at=datetime.fromtimestamp(expires_at),
            storage_backend="local",
        )
        db.add(download_url)
        download_urls.append({
            "url_id": url_id,
            "attachment_id": att.attachment_id,
            "url": signed_url,
            "md5": att.md5,
            "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
            "storage_backend": "local",
        })

    await db.commit()
    return {"transaction_id": transaction_id, "download_urls": download_urls}

@router.get("/downloads/{url_id}")
async def download_file(
    url_id: str,
    token: str = Query(...),
    expires: int = Query(...),
    device_id: str = Query(...),
    attachment_id: str = Query(...),
    customer_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    url_path = f"/api/v1/downloads/{url_id}"
    if not url_service.verify_token(token, url_path, expires, device_id, attachment_id, customer_id):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(DownloadUrl).where(DownloadUrl.url_id == url_id))
    download_url = result.scalar_one_or_none()
    if not download_url:
        raise HTTPException(status_code=404, detail="URL not found")

    if download_url.consumed_at:
        raise HTTPException(status_code=410, detail="URL already consumed")

    att_result = await db.execute(
        select(Attachment).where(Attachment.attachment_id == attachment_id)
    )
    attachment = att_result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        file_data = await storage.get(attachment.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

    download_url.consumed_at = datetime.utcnow()
    await db.commit()

    return StreamingResponse(
        iter([file_data]),
        media_type="application/octet-stream",
        headers={"Content-MD5": attachment.md5 or ""}
    )
