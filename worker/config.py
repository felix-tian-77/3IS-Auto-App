import os

class Config:
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    WORKER_ID = os.getenv("WORKER_ID")
    TOKEN = os.getenv("WORKER_TOKEN")
    ADB_SERIAL = os.getenv("ADB_SERIAL")
    PORT = int(os.getenv("WORKER_PORT", "8765"))
    HEARTBEAT_INTERVAL = 30  # seconds
    DEVICE_HOST = os.getenv("DEVICE_HOST", "127.0.0.1")
    # 5037 is the default `adb reverse` target port; the Device Agent listens on this
    DEVICE_PORT = int(os.getenv("DEVICE_PORT", "5037"))
    DISPATCH_TIMEOUT = int(os.getenv("DISPATCH_TIMEOUT", "120"))

config = Config()