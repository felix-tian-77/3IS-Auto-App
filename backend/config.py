from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "3IS-Auto-App"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/3is_auto"
    redis_url: str = "redis://localhost:6379/0"
    storage_backend: str = "local"
    storage_local_path: str = "/data/attachments"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    download_url_ttl_seconds: int = 300  # 5 min
    hmac_secret_key: str = "change-me-in-production"
    pending_timeout_seconds: int = 600   # 10 min
    transaction_timeout_seconds: int = 1800  # 30 min

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()