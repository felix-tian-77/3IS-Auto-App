import os
import hashlib
import aiofiles
from datetime import datetime
from pathlib import Path
from backend.storage.base import StorageBackend
from backend.config import get_settings

class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str = None):
        settings = get_settings()
        self.base_path = base_path or settings.storage_local_path
        Path(self.base_path).mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, customer_id: str, attachment_id: str, filename: str) -> Path:
        return Path(self.base_path) / customer_id / attachment_id / filename

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """key format: {customer_id}/{attachment_id}/{filename}"""
        full_path = Path(self.base_path) / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(data)
        return f"local://{key}"

    async def get(self, key: str) -> bytes:
        full_path = Path(self.base_path) / key
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()

    async def generate_signed_url(self, key: str, ttl_seconds: int) -> str:
        return f"/api/v1/downloads/{key}"

    async def delete(self, key: str) -> None:
        full_path = Path(self.base_path) / key
        if full_path.exists():
            full_path.unlink()

    async def exists(self, key: str) -> bool:
        return (Path(self.base_path) / key).exists()
