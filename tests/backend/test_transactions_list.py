import pytest
import datetime


@pytest.mark.asyncio
async def test_list_transactions_pagination(db_engine, db_session):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    for i in range(5):
        db_session.add(Transaction(
            transaction_id=f"TXN-test-{i:03d}",
            business_type=BusinessType.NEW,
            status=TransactionStatus.PENDING,
            customer_phone="13800000000",
            created_at=now,
        ))
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transactions", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert body["total"] == 5
        assert len(body["items"]) == 2

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_transactions_phone_search(db_engine, db_session):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    db_session.add_all([
        Transaction(
            transaction_id="TXN-phone-a",
            business_type=BusinessType.NEW,
            status=TransactionStatus.PENDING,
            customer_phone="13812345678",
            created_at=now,
        ),
        Transaction(
            transaction_id="TXN-phone-b",
            business_type=BusinessType.NEW,
            status=TransactionStatus.PENDING,
            customer_phone="13987654321",
            created_at=now,
        ),
    ])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/transactions", params={"search": "1381"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["transaction_id"] == "TXN-phone-a"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_transactions_id_search(db_engine, db_session):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    db_session.add_all([
        Transaction(
            transaction_id="TXN-20260609-001",
            business_type=BusinessType.NEW,
            status=TransactionStatus.PENDING,
            customer_phone="13800000001",
            created_at=now,
        ),
        Transaction(
            transaction_id="TXN-20260609-002",
            business_type=BusinessType.NEW,
            status=TransactionStatus.PENDING,
            customer_phone="13800000002",
            created_at=now,
        ),
    ])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/transactions", params={"search": "TXN-20260609-001"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["transaction_id"] == "TXN-20260609-001"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_transactions_status_filter(db_engine, db_session):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.db.database import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    from backend.models.transaction import Transaction, TransactionStatus, BusinessType

    now = datetime.datetime.utcnow()
    db_session.add_all([
        Transaction(transaction_id="TXN-a", business_type=BusinessType.NEW,
                    status=TransactionStatus.PENDING, created_at=now),
        Transaction(transaction_id="TXN-b", business_type=BusinessType.NEW,
                    status=TransactionStatus.SUCCESS, created_at=now),
    ])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/transactions", params={"status": "SUCCESS"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "SUCCESS"

    app.dependency_overrides.clear()
