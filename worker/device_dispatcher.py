import json
import logging
import socket
import time
from dataclasses import dataclass, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DownloadUrl:
    attachment_id: str
    url: str
    md5: str
    ext: str


@dataclass
class DownloadInstruction:
    transaction_id: str
    download_urls: List[DownloadUrl]


def build_instruction(transaction_id: str, attachments: list) -> dict:
    """Translate Backend attachment rows into the Worker→Device JSON.

    attachments: iterable of objects exposing .attachment_id, .download_url, .md5, .file_format
    """
    urls = [
        DownloadUrl(
            attachment_id=att.attachment_id,
            url=att.download_url,
            md5=att.md5,
            ext=att.file_format.lower(),  # JPG/PNG/PDF → jpg/png/pdf
        )
        for att in attachments
    ]
    return {
        "cmd": "DOWNLOAD_FILES",
        "params": asdict(
            DownloadInstruction(
                transaction_id=transaction_id,
                download_urls=urls,
            )
        ),
    }


class DeviceDispatcher:
    """Talks to the Android Device Agent over a single TCP socket.

    Lifecycle:
        d = DeviceDispatcher(host, port)
        d.send_and_await_ack(instruction) -> (ack_dict | None)
    """

    def __init__(self, host: str, port: int, ack_timeout_sec: int = 120):
        self.host = host
        self.port = port
        self.ack_timeout_sec = ack_timeout_sec

    def send_and_await_ack(self, instruction: dict) -> Optional[dict]:
        payload = (json.dumps(instruction) + "\n").encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=10) as s:
            s.sendall(payload)
            s.settimeout(1.0)
            buf = b""
            deadline = time.time() + self.ack_timeout_sec
            while time.time() < deadline:
                try:
                    chunk = s.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    line, _, _ = buf.partition(b"\n")
                    try:
                        return json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        logger.error("Device sent non-JSON ack: %r", line)
                        return None
        logger.warning("Device closed before ack")
        return None
