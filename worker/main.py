import sys
import time
import socket
import hashlib
import logging
import requests as req_lib
from device_controller import DeviceController
from airtest_executor import AirtestExecutor
from file_downloader import FileDownloader, URLExpiredError
from device_pusher import DevicePusher
from device_status_reporter import DeviceStatusReporter
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
        self.file_downloader = FileDownloader(config.WORKER_TMP_DIR)
        self.device_pusher = DevicePusher(self.device_controller, config.DEVICE_SANDBOX_ROOT)
        self.status_reporter = DeviceStatusReporter(
            self.device_controller, config.BACKEND_URL, self.token
        )

    def register(self) -> bool:
        url = f"{config.BACKEND_URL}/api/v1/workers/register"
        data = {
            "fingerprint": get_fingerprint(),
            "hostname": socket.gethostname(),
            "ip_address": get_ip_address(),
            "version": "1.0.0",
            "tags": {},
            "adb_serial": self.adb_serial,
            "port": 0,
        }
        try:
            resp = req_lib.post(url, json=data)
            if resp.status_code == 200:
                result = resp.json()
                self.worker_id = result["worker_id"]
                self.token = result["token"]
                self.status_reporter.token = self.token
                logger.info(f"Worker registered: {self.worker_id}")
                return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
        return False

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def send_heartbeat(self):
        url = f"{config.BACKEND_URL}/api/v1/workers/heartbeat"
        try:
            resp = req_lib.post(
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
        url = f"{config.BACKEND_URL}/api/v1/tasks/poll"
        try:
            resp = req_lib.get(
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
        url = f"{config.BACKEND_URL}/api/v1/transactions/{transaction_id}/download-urls"
        try:
            resp = req_lib.post(url, headers=self.get_headers())
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

    def report_attachments_delivered(self, transaction_id: str, pushed_files: list) -> bool:
        url = f"{config.BACKEND_URL}/api/v1/transactions/{transaction_id}/attachments-delivered"
        body = {
            "device_id": self.adb_serial,
            "files": [
                {"attachment_id": pf.attachment_id, "local_path": pf.local_path}
                for pf in pushed_files
            ],
        }
        try:
            resp = req_lib.post(url, json=body, headers=self.get_headers(), timeout=10)
            if resp.status_code == 200:
                logger.info("Attachments delivered reported for %s", transaction_id)
                return True
            logger.error("attachments-delivered failed: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("attachments-delivered error: %s", e)
        return False

    def dispatch_to_device(self, task: dict) -> bool:
        if not task.get("task"):
            return False
        txn = task["task"]
        transaction_id = txn["transaction_id"]
        attachment_meta = txn.get("attachments", [])

        download_urls = self.fetch_download_urls(transaction_id)
        if not download_urls:
            logger.error("No download URLs issued for txn %s; cannot dispatch", transaction_id)
            return False

        url_by_id = {u["attachment_id"]: u for u in download_urls}
        combined = []
        for att in attachment_meta:
            url_entry = url_by_id.get(att["attachment_id"])
            if not url_entry:
                logger.error(
                    "Missing signed URL for attachment %s (txn %s)",
                    att["attachment_id"], transaction_id,
                )
                return False
            combined.append({
                "attachment_id": att["attachment_id"],
                "url": url_entry["url"],
                "md5": att.get("md5", ""),
                "file_format": att.get("file_format", ""),
            })

        downloaded = self._download_with_refresh(combined, transaction_id)
        if not downloaded or not all(d.md5_ok for d in downloaded):
            logger.error("Download failed for txn %s", transaction_id)
            self.file_downloader.cleanup(transaction_id)
            return False

        pushed = self.device_pusher.push_files(transaction_id, downloaded)
        if not pushed:
            logger.error("Push failed for txn %s", transaction_id)
            self.file_downloader.cleanup(transaction_id)
            return False

        self.report_attachments_delivered(transaction_id, pushed)

        logger.info("Dispatch complete for txn %s, ready for Airtest", transaction_id)
        return True

    def _download_with_refresh(self, combined: list, transaction_id: str) -> list:
        max_retries = config.URL_REFRESH_MAX_RETRIES
        for attempt in range(max_retries + 1):
            try:
                return self.file_downloader.download_all(combined, transaction_id)
            except URLExpiredError:
                if attempt >= max_retries:
                    logger.error("URL refresh exhausted after %d retries", max_retries)
                    return []
                logger.info("URL expired, refreshing (attempt %d/%d)", attempt + 1, max_retries)
                refreshed_urls = self.fetch_download_urls(transaction_id)
                if not refreshed_urls:
                    return []
                url_by_id = {u["attachment_id"]: u for u in refreshed_urls}
                combined = []
                for item in combined:
                    url_entry = url_by_id.get(item["attachment_id"])
                    if url_entry:
                        combined.append({
                            "attachment_id": item["attachment_id"],
                            "url": url_entry["url"],
                            "md5": item["md5"],
                            "file_format": item["file_format"],
                        })
        return []

    def run(self):
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
            self.status_reporter.report_status(self.worker_id)
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
