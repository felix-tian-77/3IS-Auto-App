import logging
import requests

logger = logging.getLogger(__name__)


class DeviceStatusReporter:
    def __init__(self, device_controller, backend_url: str, token: str = ""):
        self.device_controller = device_controller
        self.backend_url = backend_url.rstrip("/")
        self.token = token

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def report_ready(self, device_id: str) -> bool:
        url = f"{self.backend_url}/api/v1/devices/{device_id}/ready"
        try:
            resp = requests.post(url, json={"status": "READY"}, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                logger.info("Device %s reported READY", device_id)
                return True
            logger.error("report_ready failed: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("report_ready error: %s", e)
        return False

    def report_status(self, device_id: str) -> bool:
        status = self.device_controller.get_status()
        url = f"{self.backend_url}/api/v1/workers/heartbeat"
        try:
            resp = requests.post(
                url,
                params={"worker_id": device_id},
                json={
                    "cpu_usage": 0.0,
                    "memory_usage": 0.0,
                    "battery_level": status.get("battery_level"),
                    "storage_free_mb": status.get("storage_free_mb"),
                    "screen_locked": status.get("screen_locked"),
                    "adb_status": "CONNECTED",
                },
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("Device status reported for %s", device_id)
                return True
            logger.error("report_status failed: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("report_status error: %s", e)
        return False
