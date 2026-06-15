import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.database import get_db


@pytest.mark.asyncio
async def test_device_ready_updates_status_and_last_seen_at(db_engine):
    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/devices/device-001/ready",
                json={"status": "READY"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["device_id"] == "device-001"
        assert body["status"] == "READY"
        assert "last_seen_at" in body
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_device_download_ack_marks_busy_on_partial_failure(db_engine):
    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/api/v1/devices/device-002/ready", json={"status": "READY"})

            resp = await ac.post(
                "/api/v1/devices/device-002/download-ack",
                json={
                    "transaction_id": "TXN-TEST-0001",
                    "files": [
                        {
                            "attachment_id": "att_test01",
                            "local_path": "/sdcard/3is/att_test01.jpg",
                            "success": True,
                        }
                    ],
                    "all_success": False,
                    "sandbox_clear_failed": True,
                    "completed_at": "2026-06-13T10:00:00Z",
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["transaction_id"] == "TXN-TEST-0001"
        assert body["next_state"] == "RETRY_REQUIRED"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_device_download_ack_persists_local_path_and_finished_at_on_success(
    db_engine, db_session
):
    """Spec §3.2.2 + §3.6.3: on all_success=True the backend must (a) persist
    each file's local_path back to the matching Attachment row keyed by
    attachment_id, and (b) stamp Transaction.finished_at = req.completed_at."""
    from datetime import datetime, timezone
    from backend.models.transaction import Transaction, BusinessType, TransactionStatus
    from backend.models.attachment import Attachment, FileType, FileFormat

    db_session.add(Transaction(
        transaction_id="TXN-TEST-0002",
        business_type=BusinessType.NEW,
        status=TransactionStatus.DOWNLOADING,
    ))
    db_session.add(Attachment(
        attachment_id="att_test02",
        transaction_id="TXN-TEST-0002",
        file_type=FileType.ID_CARD.value,
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
            await ac.post("/api/v1/devices/device-003/ready", json={"status": "READY"})

            resp = await ac.post(
                "/api/v1/devices/device-003/download-ack",
                json={
                    "transaction_id": "TXN-TEST-0002",
                    "files": [
                        {
                            "attachment_id": "att_test02",
                            "local_path": "/sdcard/3is/att_test02.jpg",
                            "success": True,
                        }
                    ],
                    "all_success": True,
                    "sandbox_clear_failed": False,
                    "completed_at": "2026-06-13T10:00:00Z",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["next_state"] == "READY"

        async with SessionLocal() as verify:
            att = (await verify.execute(
                select(Attachment).where(Attachment.attachment_id == "att_test02")
            )).scalar_one()
            assert att.local_path == "/sdcard/3is/att_test02.jpg"

            txn = (await verify.execute(
                select(Transaction).where(Transaction.transaction_id == "TXN-TEST-0002")
            )).scalar_one()
            # SQLite strips tzinfo on DateTime(timezone=True) round-trip; compare
            # the wall-clock value via UTC normalisation.
            assert txn.finished_at is not None
            stored = txn.finished_at.replace(tzinfo=timezone.utc) if txn.finished_at.tzinfo is None else txn.finished_at
            assert stored == datetime(2026, 6, 13, 10, 0, 0, tzinfo=timezone.utc)
    finally:
        app.dependency_overrides.clear()

