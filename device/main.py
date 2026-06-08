import os
import sys
import requests
import logging
from datetime import datetime
from downloader import Downloader
from socket_client import SocketClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKER_HOST = os.getenv("WORKER_HOST", "192.168.1.100")
WORKER_PORT = int(os.getenv("WORKER_PORT", "8765"))
DEVICE_ID = os.getenv("DEVICE_ID", "device-001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

class Device:
    def __init__(self):
        self.device_id = DEVICE_ID
        self.downloader = Downloader()
        self.socket_client = None
        self.sandbox_path = "/sdcard/sandbox"

    def report_ready(self):
        """Report device ready status to backend"""
        url = f"{BACKEND_URL}/api/v1/devices/{self.device_id}/ready"
        try:
            resp = requests.post(url, json={"status": "READY"})
            logger.info(f"Ready reported: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to report ready: {e}")

    def report_download_ack(self, transaction_id: str, files: list):
        """Report download completion to backend"""
        url = f"{BACKEND_URL}/api/v1/devices/{self.device_id}/download-ack"
        data = {
            "transaction_id": transaction_id,
            "files": files,
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }
        try:
            resp = requests.post(url, json=data)
            logger.info(f"Download ack sent: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to send download ack: {e}")

    def on_download_instruction(self, params: dict):
        """Handle download instruction from Worker"""
        transaction_id = params["transaction_id"]
        download_urls = params["download_urls"]

        logger.info(f"Received download instruction for transaction {transaction_id}")

        # Create sandbox path
        sandbox = f"{self.sandbox_path}/{transaction_id}"
        os.makedirs(sandbox, exist_ok=True)

        # Download files
        results = self.downloader.download_urls(download_urls, sandbox)

        # Report completion
        self.report_download_ack(transaction_id, results)

    def run(self):
        """Main device loop"""
        logger.info(f"Device starting: {self.device_id}")

        # Report ready
        self.report_ready()

        # Connect to Worker socket
        self.socket_client = SocketClient(WORKER_HOST, WORKER_PORT, self.on_download_instruction)
        self.socket_client.connect()

        # Listen for instructions
        self.socket_client.listen()


if __name__ == "__main__":
    device = Device()
    device.run()