"""Verify dispatcher behavior when no worker is available.

Two scenarios are tested:
1. No worker row at all -> transaction should stay PENDING
2. Stale worker row (status=ONLINE but no recent heartbeat) -> does
   the dispatcher still match it?
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.database import Base
from backend.models.device import Device, DeviceStatus, ADBStatus
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.worker import Worker, WorkerStatus
from backend.schemas.transaction import TransactionCreateRequest
from backend.services.transaction_service import TransactionService


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _build_request(business_type: BusinessType = BusinessType.OLD_VEHICLE) -> TransactionCreateRequest:
    """Use OLD_VEHICLE which needs no files (4 files for NEW_VEHICLE)."""
    return TransactionCreateRequest(
        business_type=business_type,
        customer_phone="13800000000",
        attachments_meta=[],
    )


@pytest.mark.asyncio
async def test_no_worker_status_stays_pending(session_factory):
    """Scenario 1: workers table is empty -> transaction must not be DISPATCHED."""
    async with session_factory() as session:
        service = TransactionService(session)
        req = _build_request()
        # OLD_VEHICLE needs ID_CARD_FRONT/BACK + DRIVING_LICENSE_FRONT/BACK but we
        # pass empty files -> should fail validation. Use NEW_VEHICLE with skipped
        # validation? Easier: temporarily monkeypatch the validator. Simplest fix:
        # patch REQUIRED_FILES to empty.
        from backend.services import transaction_service as ts_module

        orig = ts_module.REQUIRED_FILES
        ts_module.REQUIRED_FILES = {bt: [] for bt in [BusinessType.NEW_VEHICLE, BusinessType.OLD_VEHICLE]}
        ts_module.ADDITIONAL_FILES = {}
        try:
            result = await service.create_transaction(
                req,
                files=[],
            )
        finally:
            ts_module.REQUIRED_FILES = orig
            ts_module.ADDITIONAL_FILES = {
                "tax_exempt": [],
                "is_transfer": [],
            }

        assert result["status"] == TransactionStatus.PENDING.value, (
            f"Expected PENDING, got {result['status']}"
        )
        assert result.get("worker_id") is None

    async with session_factory() as verify_session:
        txn = (
            await verify_session.execute(
                select(Transaction).where(
                    Transaction.transaction_id == result["transaction_id"]
                )
            )
        ).scalar_one()
        assert txn.status == TransactionStatus.PENDING.value
        assert txn.worker_id is None


@pytest.mark.asyncio
async def test_stale_worker_with_old_heartbeat_dispatches(session_factory):
    """Scenario 2: A worker row with status=ONLINE but heartbeat 1h ago.

    Documents the current behavior: the dispatcher only checks status==ONLINE
    and bound_device_id IS NOT NULL, never heartbeat recency, so it will
    dispatch to a worker that is no longer heartbeating.
    """
    async with session_factory() as session:
        device = Device(
            device_id="DEV-stale0001",
            adb_serial="adb-stale-001",
            status=DeviceStatus.ONLINE,
            adb_status=ADBStatus.CONNECTED,
        )
        session.add(device)

        worker = Worker(
            worker_id="WKR-stale0001",
            fingerprint="fp-stale-001",
            hostname="stale-host",
            status=WorkerStatus.ONLINE,
            bound_device_id="DEV-stale0001",
            last_heartbeat_at=datetime.now(timezone.utc) - timedelta(hours=1),
            registered_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        session.add(worker)
        await session.commit()

    async with session_factory() as session:
        service = TransactionService(session)
        req = _build_request()
        from backend.services import transaction_service as ts_module

        orig = ts_module.REQUIRED_FILES
        ts_module.REQUIRED_FILES = {bt: [] for bt in [BusinessType.NEW_VEHICLE, BusinessType.OLD_VEHICLE]}
        ts_module.ADDITIONAL_FILES = {}
        try:
            result = await service.create_transaction(req, files=[])
        finally:
            ts_module.REQUIRED_FILES = orig
            ts_module.ADDITIONAL_FILES = {
                "tax_exempt": [],
                "is_transfer": [],
            }

        assert result["status"] == TransactionStatus.DISPATCHED.value, (
            "Current bug: dispatcher matched a worker that has not heartbeated "
            "for 1 hour. Transaction was auto-dispatched to a dead worker."
        )
        assert result.get("worker_id") == "WKR-stale0001"
