from abc import ABC, abstractmethod
from typing import Optional

class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store data and return storage path"""
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve data by key"""
        pass

    @abstractmethod
    async def generate_signed_url(self, key: str, ttl_seconds: int) -> str:
        """Generate signed URL for download"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data by key"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass
