import os
import json
import hashlib
import logging
import requests
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class URLExpiredError(Exception):
    pass


@dataclass
class DownloadedFile:
    attachment_id: str
    local_path: str
    md5_ok: bool


class FileDownloader:
    def __init__(self, tmp_dir: str):
        self.tmp_dir = tmp_dir

    def _txn_dir(self, transaction_id: str) -> Path:
        d = Path(self.tmp_dir) / transaction_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def verify_md5(self, file_path: str, expected_md5: str) -> bool:
        digest = hashlib.md5()
        with open(file_path, "rb") as f:
            buf = f.read(8192)
            while buf:
                digest.update(buf)
                buf = f.read(8192)
        return digest.hexdigest().lower() == expected_md5.lower()

    def download(self, url: str, attachment_id: str, transaction_id: str,
                 expected_md5: str, ext: str) -> DownloadedFile:
        txn_dir = self._txn_dir(transaction_id)
        part_path = txn_dir / f"{attachment_id}.{ext}.part"
        final_path = txn_dir / f"{attachment_id}.{ext}"

        resp = requests.get(url, stream=True, timeout=30)
        if resp.status_code in (403, 410):
            resp.close()
            raise URLExpiredError(f"URL expired ({resp.status_code}) for attachment {attachment_id}")
        resp.raise_for_status()

        with open(part_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        resp.close()

        md5_ok = self.verify_md5(str(part_path), expected_md5)
        if not md5_ok:
            part_path.unlink(missing_ok=True)
            logger.error("MD5 mismatch for attachment %s", attachment_id)
            return DownloadedFile(
                attachment_id=attachment_id,
                local_path=str(final_path),
                md5_ok=False,
            )

        part_path.replace(final_path)
        return DownloadedFile(
            attachment_id=attachment_id,
            local_path=str(final_path),
            md5_ok=True,
        )

    def download_all(self, signed_urls: list, transaction_id: str) -> list:
        results = []
        for item in signed_urls:
            att_id = item["attachment_id"]
            url = item["url"]
            md5 = item.get("md5", "")
            ext = item.get("file_format", "").lower() or item.get("ext", "")

            result = self.download(url, att_id, transaction_id, md5, ext)
            results.append(result)
            if not result.md5_ok:
                break
        return results

    def cleanup(self, transaction_id: str):
        import shutil
        txn_dir = Path(self.tmp_dir) / transaction_id
        if txn_dir.exists():
            shutil.rmtree(txn_dir, ignore_errors=True)

    def save_transaction_meta(self, transaction_id: str, meta: dict) -> None:
        txn_dir = self._txn_dir(transaction_id)
        out_path = txn_dir / "transaction_meta.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
