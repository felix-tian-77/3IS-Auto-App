from pydantic_settings import BaseSettings
from functools import lru_cache
import os

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
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# When a .env file exists in the backend dir, treat it as the source of
# truth. Stale os.environ values (e.g. inherited from a previous debugpy
# launch that injected STORAGE_LOCAL_PATH at startup) would otherwise win
# over .env, since pydantic-settings reads os.environ first.
_ENV_FILE_KEYS = (
    "APP_NAME", "DATABASE_URL", "REDIS_URL", "STORAGE_BACKEND",
    "STORAGE_LOCAL_PATH", "JWT_SECRET", "JWT_ALGORITHM",
    "JWT_EXPIRE_HOURS", "DOWNLOAD_URL_TTL_SECONDS", "HMAC_SECRET_KEY",
    "PENDING_TIMEOUT_SECONDS", "TRANSACTION_TIMEOUT_SECONDS",
)

@lru_cache()
def get_settings() -> Settings:
    env_file = Settings.Config.env_file
    if os.path.exists(env_file):
        for key in _ENV_FILE_KEYS:
            os.environ.pop(key, None)
    return Settings()