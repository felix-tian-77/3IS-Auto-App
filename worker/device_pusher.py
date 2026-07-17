import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PushedFile:
    attachment_id: str
    local_path: str
    filename: str = ""


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
            filename = df.filename or Path(df.local_path).name
            remote_path = f"{txn_dir}/{filename}"
            self.device_controller.push_file(df.local_path, remote_path)
            pushed.append(PushedFile(
                attachment_id=df.attachment_id,
                local_path=remote_path,
                filename=filename,
            ))
            logger.info("Pushed %s -> %s", df.attachment_id, remote_path)
        return pushed

    def cleanup(self, transaction_id: str):
        txn_dir = f"{self.sandbox_root}/{transaction_id}"
        self.device_controller.shell(f"rm -rf {txn_dir}")
        logger.info("Cleaned device sandbox: %s", txn_dir)
