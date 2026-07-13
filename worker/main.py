import sys
import time
import socket
import hashlib
import requests
import logging
from device_controller import DeviceController
from airtest_executor import AirtestExecutor
from device_dispatcher import DeviceDispatcher, build_instruction
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_fingerprint():
    return hashlib.md5(socket.gethostname().encode()).hexdigest()


def get_ip_address():
    return socket.gethostbyname(socket.gethostname())

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
            "fingerprint": get_fingerprint(),
            "hostname": socket.gethostname(),
            "ip_address": get_ip_address(),
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

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def send_heartbeat(self):
        """Send heartbeat to backend"""
        url = f"{config.BACKEND_URL}/api/v1/workers/heartbeat"
        try:
            resp = requests.post(
                url,
                params={"worker_id": self.worker_id},
                json={"cpu_usage": 0.3, "memory_usage": 0.5},
                headers=self.get_headers(),
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False

    def poll_tasks(self):
        """Poll for tasks from backend; returns dict with .task and .attachments, or None."""
        url = f"{config.BACKEND_URL}/api/v1/tasks/poll"
        try:
            resp = requests.get(
                url,
                params={"worker_id": self.worker_id},
                headers=self.get_headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error("Task poll failed: %e", e)
        return None

    def fetch_download_urls(self, transaction_id: str) -> list:
        """Ask the Backend to issue signed download URLs for the transaction.

        The signed URLs are what the Device Agent will actually fetch from,
        so this must happen *after* the poll (which only tells us *what* to do)
        and *before* we build the TCP instruction.
        """
        url = f"{config.BACKEND_URL}/api/v1/transactions/{transaction_id}/download-urls"
        try:
            resp = requests.post(url, headers=self.get_headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("download_urls", []) or []
            logger.error(
                "download-urls request failed for %s: %s %s",
                transaction_id, resp.status_code, resp.text,
            )
        except Exception as e:
            logger.error("download-urls request errored for %s: %s", transaction_id, e)
        return []

    def dispatch_to_device(self, task: dict) -> bool:
        if not task.get("task"):
            return False
        txn = task["task"]
        # The poll endpoint nests attachments under "task", not at the top level.
        attachment_meta = txn.get("attachments", [])
        # `file_format` in poll uses uppercase ("JPG"); `build_instruction` lowercases.
        # We pass the metadata through directly — the dict contract is the source of
        # truth, so field name normalization happens inside `build_instruction`.

        # Step 1: get the signed URLs the Device Agent will actually use.
        download_urls = self.fetch_download_urls(txn["transaction_id"])
        if not download_urls:
            logger.error(
                "No download URLs issued for txn %s; cannot dispatch",
                txn["transaction_id"],
            )
            return False

        # Step 2: join the signed URLs with attachment metadata by attachment_id.
        url_by_id = {u["attachment_id"]: u for u in download_urls}
        combined = []
        for att in attachment_meta:
            url_entry = url_by_id.get(att["attachment_id"])
            if not url_entry:
                logger.error(
                    "Missing signed URL for attachment %s (txn %s)",
                    att["attachment_id"], txn["transaction_id"],
                )
                return False
            combined.append({
                "attachment_id": att["attachment_id"],
                "url": url_entry["url"],
                "md5": att["md5"],
                "file_format": att["file_format"],
            })

        instruction = build_instruction(txn["transaction_id"], combined)
        dispatcher = DeviceDispatcher(
            config.WORKER_LISTEN_HOST,
            config.PORT,
            ack_timeout_sec=config.DISPATCH_TIMEOUT,
        )
        ack = dispatcher.send_and_await_ack(instruction)
        if ack is None:
            logger.error("No ack from device for txn %s", txn["transaction_id"])
            return False
        logger.info("Device ack: %s", ack)
        # TODO (post-MVP): POST ack back to Backend via workers/ack or similar
        return True

    def run(self):
        """Main worker loop"""
        logger.info(f"Worker starting with ADB serial: {self.adb_serial}")

        if not self.register():
            logger.error("Worker registration failed, exiting")
            sys.exit(1)
        if not self.device_controller.connect():
            logger.error("Device connection failed, exiting")
            sys.exit(1)
        self.airtest_executor = AirtestExecutor(self.adb_serial)
        self.airtest_executor.connect()
        logger.info("Worker started successfully")

        while True:
            self.send_heartbeat()
            task = self.poll_tasks()
            if task:
                self.dispatch_to_device(task)
            time.sleep(config.HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    if not config.ADB_SERIAL:
        logger.error("ADB_SERIAL environment variable required")
        sys.exit(1)

    worker = Worker()
    worker.run()