import os

def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
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
    # The Worker listens on this port for inbound connections from the Android
    # Device Agent. This is the same value reported to the backend in
    # /workers/register (see main.py:register) and the same value the Device
    # Agent dials (see android/app/build.gradle.kts BuildConfig.WORKER_PORT).
    # Default 8765 matches `adb reverse tcp:8765 tcp:8765` (see android/README).
    WORKER_LISTEN_HOST = os.getenv("WORKER_LISTEN_HOST", "0.0.0.0")
    PORT = int(os.getenv("WORKER_PORT", "8765"))
    HEARTBEAT_INTERVAL = 30  # seconds
    DISPATCH_TIMEOUT = int(os.getenv("DISPATCH_TIMEOUT", "120"))

config = Config()