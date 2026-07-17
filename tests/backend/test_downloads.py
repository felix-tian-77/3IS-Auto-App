import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.db.database import get_db
from backend.models.attachment import Attachment, FileFormat, FileType
from backend.models.transaction import Transaction, TransactionStatus, BusinessType


@pytest.mark.asyncio
async def test_download_urls_include_attachment_basename(
    db_engine, db_session
):
    transaction_id = "TXN-DOWNLOAD-0001"
    db_session.add(Transaction(
        transaction_id=transaction_id,
        business_type=BusinessType.NEW_VEHICLE,
        status=TransactionStatus.DISPATCHED,
        worker_id="WKR-DOWNLOAD-0001",
        device_id="DEV-DOWNLOAD-0001",
    ))
    db_session.add(Attachment(
        attachment_id="ATT-DOWNLOAD-0001",
        transaction_id=transaction_id,
        file_type=FileType.ID_CARD_FRONT.value,
        file_format=FileFormat.JPG.value,
        storage_path=f"{transaction_id}/ID_CARD_FRONT.JpG",
    ))
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/transactions/{transaction_id}/download-urls"
            )

        assert response.status_code == 200
        items = response.json()["download_urls"]
        assert len(items) == 1
        assert items[0]["filename"] == "ID_CARD_FRONT.JpG"
        assert "/" not in items[0]["filename"]
        assert "\\" not in items[0]["filename"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_download_urls_reject_attachment_without_storage_path(
    db_engine, db_session
):
    transaction_id = "TXN-DOWNLOAD-0002"
    db_session.add(Transaction(
        transaction_id=transaction_id,
        business_type=BusinessType.NEW_VEHICLE,
        status=TransactionStatus.DISPATCHED,
        worker_id="WKR-DOWNLOAD-0002",
        device_id="DEV-DOWNLOAD-0002",
    ))
    db_session.add(Attachment(
        attachment_id="ATT-DOWNLOAD-0002",
        transaction_id=transaction_id,
        file_type=FileType.ID_CARD_BACK.value,
        file_format=FileFormat.JPG.value,
        storage_path=None,
    ))
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/transactions/{transaction_id}/download-urls"
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
