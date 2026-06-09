import pytest
import datetime


@pytest.mark.asyncio
async def test_dashboard_stats_empty_data(db_engine):
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
        resp = await client.get("/api/v1/statistics/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["today_count"] == 0
        assert body["yesterday_count"] == 0
        assert body["success_rate"] == 0.0
        assert body["recent_transactions"] == []
        # hourly_trend has 11 zero-count buckets even when no data
        assert len(body["hourly_trend"]) == 11
        assert all(b["count"] == 0 for b in body["hourly_trend"])
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_stats_status_distribution_chinese_labels(db_engine, db_session):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    db_session.add_all([
        Transaction(transaction_id="TXN-s1", business_type=BusinessType.NEW,
                    status=TransactionStatus.SUCCESS, created_at=now),
        Transaction(transaction_id="TXN-p1", business_type=BusinessType.NEW,
                    status=TransactionStatus.PENDING, created_at=now),
    ])
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/statistics/dashboard")
        body = resp.json()
        labels = {item["status"] for item in body["status_distribution"]}
        assert labels == {"成功", "处理中", "待处理", "失败"}
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_stats_hourly_trend_has_11_buckets(db_engine):
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
        resp = await client.get("/api/v1/statistics/dashboard")
        body = resp.json()
        assert len(body["hourly_trend"]) == 11
        assert body["hourly_trend"][0]["hour"] == 8
        assert body["hourly_trend"][-1]["hour"] == 18
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_stats_recent_transactions(db_engine, db_session, seed_devices):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    db_session.add(Transaction(
        transaction_id="TXN-recent-1",
        business_type=BusinessType.NEW,
        status=TransactionStatus.RUNNING,
        worker_id="WKR-online-1",
        created_at=now,
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/statistics/dashboard")
        body = resp.json()
        assert len(body["recent_transactions"]) == 1
        txn = body["recent_transactions"][0]
        assert txn["transaction_id"] == "TXN-recent-1"
        assert txn["worker"]["hostname"] == "worker-online-1"
    app.dependency_overrides.clear()
