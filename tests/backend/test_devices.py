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
