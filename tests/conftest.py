import pytest
import asyncio
from httpx import AsyncClient

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    # For MVP, tests are structural - full integration tests need DB
    pass