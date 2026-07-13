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
    """Translate attachment rows into the Worker→Device JSON.

    attachments: list of dicts (or any object) exposing the fields:
        - attachment_id
        - url  (the signed download URL issued by Backend /download-urls)
        - md5
        - file_format  ("JPG"/"PNG"/"PDF" → lowercased to "jpg"/"png"/"pdf")
    """
    urls = [
        DownloadUrl(
            attachment_id=att["attachment_id"],
            url=att["url"],
            md5=att["md5"],
            ext=att["file_format"].lower(),
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
    """Talks to the Android Device Agent over a single TCP connection.

    Direction is **Worker listens, Device connects**: the Agent (see
    android/.../net/SocketClient.kt) maintains a long-lived client that
    actively dials `WORKER_HOST:WORKER_PORT` (typically 127.0.0.1:8765 via
    `adb reverse`). Worker picks up that connection here and pushes a
    single `DOWNLOAD_FILES` instruction, then waits for one ack line.

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
        deadline = time.time() + self.ack_timeout_sec
        # If no device is already connected, accept one for this dispatch.
        # Otherwise (fast path) reuse the connection Android's SocketClient keeps alive.
        try:
            with socket.create_server(
                (self.host, self.port), backlog=1, reuse_port=False
            ) as srv:
                srv.settimeout(self.ack_timeout_sec)
                logger.info("Waiting for Device Agent connection on %s:%s", self.host, self.port)
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    logger.warning("Timed out waiting for Device Agent connection")
                    return None
                with conn:
                    conn.settimeout(self.ack_timeout_sec)
                    logger.info("Device Agent connected from %s", addr)
                    conn.sendall(payload)
                    buf = b""
                    while time.time() < deadline:
                        try:
                            chunk = conn.recv(4096)
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
        except OSError as e:
            logger.error("Could not bind %s:%s for Device Agent: %s", self.host, self.port, e)
            return None
