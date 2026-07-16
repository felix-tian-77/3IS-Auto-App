from unittest.mock import MagicMock, patch

from main import Worker
from file_downloader import DownloadedFile


def _make_worker():
    """Build a Worker without running __init__ (avoids device/network)."""
    w = Worker.__new__(Worker)
    w.worker_id = "w-test"
    w.token = "tok"
    w.adb_serial = "serial"
    w.airtest_executor = MagicMock()
    w.file_downloader = MagicMock()
    w.device_pusher = MagicMock()
    w.status_reporter = MagicMock()
    return w


def test_dispatch_warns_when_customer_phone_missing(tmp_path, caplog):
    """A warning is logged when customer_phone is None in the poll response."""
    w = _make_worker()

    task = {
        "task": {
            "transaction_id": "T-1",
            "holder_phone": "13800138000",
            "customer_phone": None,
            "business_type": "OLD_VEHICLE",
            "tax_exempt": False,
            "is_transfer": False,
            "attachments": [
                {"attachment_id": "att_1", "md5": "abc", "file_format": "JPG"},
            ],
        }
    }

    download_urls = [
        {"attachment_id": "att_1", "url": "http://example.com/a.jpg"},
    ]
    downloaded = [DownloadedFile(attachment_id="att_1", local_path="/tmp/a.jpg", md5_ok=True)]

    with patch.object(w, "fetch_download_urls", return_value=download_urls), \
         patch.object(w, "_download_with_refresh", return_value=downloaded), \
         patch.object(w, "report_attachments_delivered", return_value=True), \
         patch("main._resolve_script_path", return_value=None):
        with caplog.at_level("WARNING"):
            w.dispatch_to_device(task)

    assert any("customer_phone missing" in rec.message for rec in caplog.records)


def test_dispatch_no_warning_when_customer_phone_present(tmp_path, caplog):
    """No customer_phone warning when the field is populated."""
    w = _make_worker()

    task = {
        "task": {
            "transaction_id": "T-2",
            "holder_phone": "13800138000",
            "customer_phone": "13900139000",
            "business_type": "OLD_VEHICLE",
            "tax_exempt": False,
            "is_transfer": False,
            "attachments": [
                {"attachment_id": "att_1", "md5": "abc", "file_format": "JPG"},
            ],
        }
    }

    download_urls = [
        {"attachment_id": "att_1", "url": "http://example.com/a.jpg"},
    ]
    downloaded = [DownloadedFile(attachment_id="att_1", local_path="/tmp/a.jpg", md5_ok=True)]

    with patch.object(w, "fetch_download_urls", return_value=download_urls), \
         patch.object(w, "_download_with_refresh", return_value=downloaded), \
         patch.object(w, "report_attachments_delivered", return_value=True), \
         patch("main._resolve_script_path", return_value=None):
        with caplog.at_level("WARNING"):
            w.dispatch_to_device(task)

    assert not any("customer_phone missing" in rec.message for rec in caplog.records)
