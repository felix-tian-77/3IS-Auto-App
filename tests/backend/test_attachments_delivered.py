import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.database import get_db
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.attachment import Attachment, FileType, FileFormat


@pytest.mark.asyncio
async def test_attachments_delivered_persists_local_path_and_sets_ready(
    db_engine, db_session
):
    db_session.add(Transaction(
        transaction_id="TXN-DELIVERED-0001",
        business_type=BusinessType.NEW_VEHICLE,
        status=TransactionStatus.DOWNLOADING,
    ))
    db_session.add(Attachment(
        attachment_id="att_delivered_01",
        transaction_id="TXN-DELIVERED-0001",
        file_type=FileType.ID_CARD_FRONT.value,
        file_format=FileFormat.JPG.value,
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/transactions/TXN-DELIVERED-0001/attachments-delivered",
                json={
                    "device_id": "DEV-test-01",
                    "files": [
                        {
                            "attachment_id": "att_delivered_01",
                            "local_path": "/sdcard/3is/TXN-DELIVERED-0001/att_delivered_01.jpg",
                        }
                    ],
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["transaction_id"] == "TXN-DELIVERED-0001"
        assert body["next_state"] == "READY"

        async with SessionLocal() as verify:
            att = (await verify.execute(
                select(Attachment).where(Attachment.attachment_id == "att_delivered_01")
            )).scalar_one()
            assert att.local_path == "/sdcard/3is/TXN-DELIVERED-0001/att_delivered_01.jpg"

            txn = (await verify.execute(
                select(Transaction).where(Transaction.transaction_id == "TXN-DELIVERED-0001")
            )).scalar_one()
            assert txn.status == TransactionStatus.READY.value
            assert txn.finished_at is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_attachments_delivered_returns_404_for_unknown_transaction(db_engine):
    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/transactions/TXN-NONEXISTENT/attachments-delivered",
                json={
                    "device_id": "DEV-test-01",
                    "files": [],
                },
            )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
