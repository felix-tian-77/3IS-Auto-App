import pytest
import datetime


@pytest.mark.asyncio
async def test_list_workers_basic(db_engine, seed_devices):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/workers")
        assert resp.status_code == 200
        body = resp.json()
        assert "workers" in body
        assert "stats" in body
        assert len(body["workers"]) == 2
        assert body["stats"]["online"] == 2
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_workers_includes_device_info(db_engine, seed_devices):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/workers")
        body = resp.json()
        online_worker = next(w for w in body["workers"] if w["worker_id"] == "WKR-online-1")
        assert online_worker["device"] is not None
        assert online_worker["device"]["model"] == "Xiaomi 13"
        assert online_worker["device"]["android_version"] == "14"
        assert online_worker["device"]["battery_level"] == 80
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_workers_marks_offline_after_timeout(db_engine, db_session):
    from backend.models.worker import Worker, WorkerStatus
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    stale = datetime.datetime.utcnow() - datetime.timedelta(seconds=120)
    db_session.add(Worker(
        worker_id="WKR-stale",
        hostname="worker-stale",
        ip_address="192.168.1.200",
        cpu_usage=0.0,
        memory_usage=0.0,
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=stale,
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/workers")
        body = resp.json()
        stale_worker = next(w for w in body["workers"] if w["worker_id"] == "WKR-stale")
        assert stale_worker["status"] == "OFFLINE"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_workers_stats_counters(db_engine, seed_devices, db_session):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    db_session.add_all([
        Transaction(transaction_id="TXN-pending-1", business_type=BusinessType.NEW,
                    status=TransactionStatus.PENDING, created_at=now),
        Transaction(transaction_id="TXN-pending-2", business_type=BusinessType.NEW,
                    status=TransactionStatus.PENDING, created_at=now),
        Transaction(transaction_id="TXN-running-1", business_type=BusinessType.NEW,
                    status=TransactionStatus.RUNNING, created_at=now),
    ])
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/workers")
        body = resp.json()
        assert body["stats"]["queued"] == 2
        assert body["stats"]["processing"] == 1
        assert body["stats"]["online"] == 2
        assert body["stats"]["offline"] == 0
    app.dependency_overrides.clear()
