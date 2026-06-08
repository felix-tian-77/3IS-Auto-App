import hmac
import hashlib
import base64
import time
from backend.config import get_settings

class URLSignatureService:
    def __init__(self):
        settings = get_settings()
        self.secret_key = settings.hmac_secret_key.encode()

    def generate_token(self, url_path: str, expires_at: int, device_id: str,
                       attachment_id: str, customer_id: str) -> str:
        base_string = f"{url_path}\n{expires_at}\n{device_id}\n{attachment_id}\n{customer_id}"
        signature = hmac.new(
            self.secret_key,
            base_string.encode(),
            hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(signature).decode().rstrip("=")

    def verify_token(self, token: str, url_path: str, expires_at: int,
                     device_id: str, attachment_id: str, customer_id: str) -> bool:
        if time.time() > expires_at:
            return False
        expected_token = self.generate_token(url_path, expires_at, device_id, attachment_id, customer_id)
        return hmac.compare_digest(token, expected_token)