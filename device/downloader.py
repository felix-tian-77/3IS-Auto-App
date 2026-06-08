import requests
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self):
        self.session = requests.Session()

    def download_file(self, url: str, local_path: str, expected_md5: str = None) -> bool:
        """Download file from URL with MD5 verification"""
        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk

            # Verify MD5 if provided
            if expected_md5:
                actual_md5 = hashlib.md5(content).hexdigest()
                if actual_md5 != expected_md5:
                    logger.error(f"MD5 mismatch: expected {expected_md5}, got {actual_md5}")
                    return False

            # Save to local path
            with open(local_path, "wb") as f:
                f.write(content)

            logger.info(f"Downloaded file to {local_path}")
            return True

        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
            logger.error(f"Download failed: {e}")
            return False

    def download_urls(self, download_urls: list, sandbox_path: str) -> dict:
        """Download multiple files"""
        results = []
        for url_info in download_urls:
            url = url_info["url"]
            md5 = url_info.get("md5")
            file_type = url_info.get("file_type", "unknown")
            local_file = f"{sandbox_path}/{file_type}.jpg"

            success = self.download_file(url, local_file, md5)
            results.append({
                "file_type": file_type,
                "local_path": local_file,
                "success": success,
            })

        return results