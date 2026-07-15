import os
import json
import logging

logger = logging.getLogger(__name__)

def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value

_load_env_file()

class Config:
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    WORKER_ID = os.getenv("WORKER_ID")
    TOKEN = os.getenv("WORKER_TOKEN")
    ADB_SERIAL = os.getenv("ADB_SERIAL")
    HEARTBEAT_INTERVAL = 30  # seconds
    DEVICE_SANDBOX_ROOT = os.getenv("DEVICE_SANDBOX_ROOT", "/sdcard/3is/")
    WORKER_TMP_DIR = os.getenv("WORKER_TMP_DIR", os.path.join(os.path.expanduser("~"), ".3is-auto", "tmp"))
    URL_REFRESH_MAX_RETRIES = int(os.getenv("URL_REFRESH_MAX_RETRIES", "2"))

    @staticmethod
    def _parse_script_map():
        raw = os.getenv("SCRIPT_MAP", "{}")
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("SCRIPT_MAP is not valid JSON (%s); falling back to {}", e)
            return {}
        if not isinstance(parsed, dict):
            logger.warning("SCRIPT_MAP must be a JSON object; got %s; falling back to {}", type(parsed).__name__)
            return {}
        return {str(k): str(v) for k, v in parsed.items()}

    SCRIPT_MAP = _parse_script_map()

config = Config()
