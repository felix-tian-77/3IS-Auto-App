import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PushedFile:
    attachment_id: str
    local_path: str


class DevicePusher:
    def __init__(self, device_controller, sandbox_root: str = "/sdcard/3is/"):
        self.device_controller = device_controller
        self.sandbox_root = sandbox_root.rstrip("/")

    def push_files(self, transaction_id: str, downloaded_files: list) -> list:
        txn_dir = f"{self.sandbox_root}/{transaction_id}"
        self.device_controller.shell(f"mkdir -p {txn_dir}")

        pushed = []
        for df in downloaded_files:
            if not df.md5_ok:
                continue
            ext = self._extract_ext(df.local_path)
            remote_path = f"{txn_dir}/{df.attachment_id}.{ext}"
            self.device_controller.push_file(df.local_path, remote_path)
            pushed.append(PushedFile(
                attachment_id=df.attachment_id,
                local_path=remote_path,
            ))
            logger.info("Pushed %s -> %s", df.attachment_id, remote_path)
        return pushed

    def cleanup(self, transaction_id: str):
        txn_dir = f"{self.sandbox_root}/{transaction_id}"
        self.device_controller.shell(f"rm -rf {txn_dir}")
        logger.info("Cleaned device sandbox: %s", txn_dir)

    @staticmethod
    def _extract_ext(local_path: str) -> str:
        import os
        _, ext = os.path.splitext(local_path)
        return ext.lstrip(".") if ext else "bin"
