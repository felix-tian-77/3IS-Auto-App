import os

class Config:
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    WORKER_ID = os.getenv("WORKER_ID")
    TOKEN = os.getenv("WORKER_TOKEN")
    ADB_SERIAL = os.getenv("ADB_SERIAL")
    PORT = int(os.getenv("WORKER_PORT", "8765"))
    HEARTBEAT_INTERVAL = 30  # seconds

config = Config()