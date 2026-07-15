import pytest
import datetime
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.database import get_db
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.worker import Worker, WorkerStatus


@pytest.mark.asyncio
async def test_poll_task_includes_tax_exempt_is_transfer_holder_phone(
    db_engine, db_session
):
    db_session.add(Worker(
        worker_id='WKR-poll-1',
        hostname='poll-host',
        ip_address='10.0.0.1',
        cpu_usage=0.0,
        memory_usage=0.0,
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=datetime.datetime.utcnow(),
    ))
    db_session.add(Transaction(
        transaction_id='T-POLL-0001',
        business_type=BusinessType.NEW_VEHICLE,
        status=TransactionStatus.DISPATCHED,
        worker_id='WKR-poll-1',
        tax_exempt=True,
        is_transfer=True,
        holder_phone='13800138000',
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
            resp = await ac.get('/api/v1/tasks/poll', params={'worker_id': 'WKR-poll-1'})
        assert resp.status_code == 200
        task = resp.json()['task']
        assert task['transaction_id'] == 'T-POLL-0001'
        assert task['tax_exempt'] is True
        assert task['is_transfer'] is True
        assert task['holder_phone'] == '13800138000'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_poll_task_null_holder_phone_is_returned_as_null(
    db_engine, db_session
):
    db_session.add(Worker(
        worker_id='WKR-poll-2',
        hostname='poll-host-2',
        ip_address='10.0.0.2',
        cpu_usage=0.0,
        memory_usage=0.0,
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=datetime.datetime.utcnow(),
    ))
    db_session.add(Transaction(
        transaction_id='T-POLL-0002',
        business_type=BusinessType.OLD_VEHICLE,
        status=TransactionStatus.DISPATCHED,
        worker_id='WKR-poll-2',
        tax_exempt=False,
        is_transfer=False,
        holder_phone=None,
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
            resp = await ac.get('/api/v1/tasks/poll', params={'worker_id': 'WKR-poll-2'})
        assert resp.status_code == 200
        task = resp.json()['task']
        assert task['tax_exempt'] is False
        assert task['is_transfer'] is False
        assert task['holder_phone'] is None
    finally:
        app.dependency_overrides.clear()
