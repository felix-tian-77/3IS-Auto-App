#!/usr/bin/env python3
"""Mock Worker that pushes one DOWNLOAD_FILES message to a connecting Device Agent.

Usage:
    python mock_worker.py <download_url> <md5>

The script listens on :8765, accepts exactly one connection, sends the
DOWNLOAD_FILES JSON message, then waits up to 120s for an ack line
("ack: <json>") to be echoed back from the Device.
"""
import json
import socket
import sys
import time


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: mock_worker.py <url> <md5>", file=sys.stderr)
        return 2

    url, md5 = sys.argv[1], sys.argv[2]
    msg = {
        "cmd": "DOWNLOAD_FILES",
        "params": {
            "transaction_id": "TXN-MOCK-0001",
            "download_urls": [
                {"attachment_id": "att_mock0001", "url": url, "md5": md5, "ext": "jpg"}
            ],
        },
    }
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 8765))
    s.listen(1)
    print("Mock worker listening on :8765", flush=True)
    conn, addr = s.accept()
    print(f"device connected: {addr}", flush=True)
    conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    try:
        conn.settimeout(120.0)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
        if buf:
            print("ack:", buf.decode("utf-8", errors="replace"), flush=True)
    except socket.timeout:
        print("no ack within 120s", flush=True)
    finally:
        conn.close()
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
