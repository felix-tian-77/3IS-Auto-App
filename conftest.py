"""Root conftest: sets env vars and exposes fixtures to all test files."""
import os
import sys
import pytest
import pytest_asyncio
import datetime
from typing import AsyncGenerator

# Set env vars BEFORE any backend import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("STORAGE_LOCAL_PATH", "/tmp/test-attachments")
os.environ.setdefault("HMAC_SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("DOWNLOAD_URL_TTL_SECONDS", "300")
os.environ.setdefault("PENDING_TIMEOUT_SECONDS", "600")
os.environ.setdefault("TRANSACTION_TIMEOUT_SECONDS", "1800")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests")
os.environ.setdefault("STORAGE_BACKEND", "local")

# Make backend importable from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.db.database import Base

from backend.models.worker import Worker, WorkerStatus
from backend.models.device import Device, DeviceStatus


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    SessionLocal = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def seed_devices(db_session):
    device_online = Device(
        device_id="DEV-online-1",
        adb_serial="adb-online-1",
        model="Xiaomi 13",
        android_version="14",
        battery_level=80,
        storage_free_mb=32000,
        status=DeviceStatus.ONLINE,
    )
    device_low = Device(
        device_id="DEV-low-1",
        adb_serial="adb-low-1",
        model="OPPO Find X6",
        android_version="13",
        battery_level=20,
        storage_free_mb=8000,
        status=DeviceStatus.ONLINE,
    )
    db_session.add_all([device_online, device_low])
    await db_session.flush()

    now = datetime.datetime.utcnow()
    worker_online = Worker(
        worker_id="WKR-online-1",
        hostname="worker-online-1",
        ip_address="192.168.1.101",
        cpu_usage=23.0,
        memory_usage=45.0,
        bound_device_id="DEV-online-1",
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=now,
    )
    worker_low = Worker(
        worker_id="WKR-low-1",
        hostname="worker-low-1",
        ip_address="192.168.1.102",
        cpu_usage=10.0,
        memory_usage=20.0,
        bound_device_id="DEV-low-1",
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=now,
    )
    db_session.add_all([worker_online, worker_low])
    await db_session.commit()
    return {"device_online": device_online, "device_low": device_low,
            "worker_online": worker_online, "worker_low": worker_low}
