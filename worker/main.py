import sys
import time
import requests
import logging
from device_controller import DeviceController
from airtest_executor import AirtestExecutor
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Worker:
    def __init__(self):
        self.worker_id = config.WORKER_ID
        self.token = config.TOKEN
        self.adb_serial = config.ADB_SERIAL
        self.device_controller = DeviceController(self.adb_serial)
        self.airtest_executor = None

    def register(self) -> bool:
        """Register worker with backend"""
        url = f"{config.BACKEND_URL}/api/v1/workers/register"
        data = {
            "fingerprint": "worker-fp-123",
            "hostname": "worker-host",
            "ip_address": "192.168.1.100",
            "version": "1.0.0",
            "tags": {},
            "adb_serial": self.adb_serial,
            "port": config.PORT,
        }
        try:
            resp = requests.post(url, json=data)
            if resp.status_code == 200:
                result = resp.json()
                self.worker_id = result["worker_id"]
                self.token = result["token"]
                logger.info(f"Worker registered: {self.worker_id}")
                return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
        return False

    def send_heartbeat(self):
        """Send heartbeat to backend"""
        url = f"{config.BACKEND_URL}/api/v1/workers/heartbeat"
        try:
            resp = requests.post(
                url,
                params={"worker_id": self.worker_id},
                json={
                    "cpu_usage": 0.3,
                    "memory_usage": 0.5,
                },
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False

    def poll_tasks(self):
        """Poll for tasks from backend"""
        url = f"{config.BACKEND_URL}/api/v1/tasks/poll"
        try:
            resp = requests.get(url, params={"worker_id": self.worker_id})
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Task poll failed: {e}")
        return None

    def run(self):
        """Main worker loop"""
        logger.info(f"Worker starting with ADB serial: {self.adb_serial}")

        # Register
        if not self.register():
            logger.error("Worker registration failed, exiting")
            sys.exit(1)

        # Connect to device
        if not self.device_controller.connect():
            logger.error("Device connection failed, exiting")
            sys.exit(1)

        # Connect Airtest
        self.airtest_executor = AirtestExecutor(self.adb_serial)
        self.airtest_executor.connect()

        logger.info("Worker started successfully")

        # Main loop
        while True:
            self.send_heartbeat()
            task = self.poll_tasks()
            if task:
                logger.info(f"Received task: {task}")
            time.sleep(config.HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    if not config.ADB_SERIAL:
        logger.error("ADB_SERIAL environment variable required")
        sys.exit(1)

    worker = Worker()
    worker.run()