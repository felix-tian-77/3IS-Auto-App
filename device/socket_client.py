import socket
import json
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SocketClient:
    def __init__(self, host: str, port: int, on_download_instruction):
        self.host = host
        self.port = port
        self.on_download_instruction = on_download_instruction
        self.socket = None
        self.running = False

    def connect(self):
        """Connect to Worker socket server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.running = True
        logger.info(f"Connected to Worker at {self.host}:{self.port}")

    def listen(self):
        """Listen for messages from Worker"""
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break

                message = json.loads(data.decode())
                if message.get("cmd") == "DOWNLOAD_FILES":
                    self.on_download_instruction(message["params"])
                elif message.get("event") == "DOWNLOAD_COMPLETE":
                    logger.info("Download completed")
                elif message.get("event") == "URL_EXPIRED":
                    logger.warning("URL expired")

            except Exception as e:
                logger.error(f"Socket error: {e}")
                break

    def send(self, message: dict):
        """Send message to Worker"""
        if self.socket:
            self.socket.sendall(json.dumps(message).encode())

    def close(self):
        """Close connection"""
        self.running = False
        if self.socket:
            self.socket.close()