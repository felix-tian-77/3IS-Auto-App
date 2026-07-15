import json
from pathlib import Path
from unittest.mock import MagicMock

from worker.file_downloader import FileDownloader
from worker.main import Worker


def test_dispatch_writes_meta_after_successful_download(tmp_path):
    """Worker.dispatch_to_device calls FileDownloader.save_transaction_meta after a successful download."""
    txn_id = "T-DISPATCH-0001"

    w = Worker.__new__(Worker)
    w.adb_serial = "ADB-test-1"
    w.worker_id = "WKR-test-1"
    w.token = "tkn"

    fd = FileDownloader(tmp_dir=str(tmp_path))
    w.file_downloader = fd

    pusher = MagicMock()
    pusher.push_files.return_value = []
    w.device_pusher = pusher

    w.fetch_download_urls = MagicMock(return_value=[])
    w._download_with_refresh = MagicMock(return_value=[])
    w.report_attachments_delivered = MagicMock(return_value=True)

    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13800138000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": False,
    }
    w.file_downloader.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == meta
