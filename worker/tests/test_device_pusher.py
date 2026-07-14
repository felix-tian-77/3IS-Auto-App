from unittest.mock import MagicMock
from pathlib import Path

from device_pusher import DevicePusher, PushedFile
from file_downloader import DownloadedFile


def _mock_controller():
    ctrl = MagicMock()
    ctrl.shell = MagicMock(return_value="")
    ctrl.push_file = MagicMock()
    return ctrl


def test_push_files_creates_transaction_subdir(tmp_path):
    ctrl = _mock_controller()
    pusher = DevicePusher(ctrl, sandbox_root="/sdcard/3is/")

    local_file = tmp_path / "att_001.jpg"
    local_file.write_bytes(b"data")

    downloaded = [
        DownloadedFile(attachment_id="att_001", local_path=str(local_file), md5_ok=True),
    ]

    results = pusher.push_files("TXN-100", downloaded)

    ctrl.shell.assert_any_call("mkdir -p /sdcard/3is/TXN-100")
    ctrl.push_file.assert_called_once_with(str(local_file), "/sdcard/3is/TXN-100/att_001.jpg")
    assert len(results) == 1
    assert results[0].attachment_id == "att_001"
    assert results[0].local_path == "/sdcard/3is/TXN-100/att_001.jpg"


def test_push_files_skips_md5_failed(tmp_path):
    ctrl = _mock_controller()
    pusher = DevicePusher(ctrl)

    downloaded = [
        DownloadedFile(attachment_id="att_bad", local_path="/tmp/bad.jpg", md5_ok=False),
        DownloadedFile(attachment_id="att_good", local_path=str(tmp_path / "good.jpg"), md5_ok=True),
    ]
    (tmp_path / "good.jpg").write_bytes(b"data")

    results = pusher.push_files("TXN-200", downloaded)

    assert len(results) == 1
    assert results[0].attachment_id == "att_good"


def test_cleanup_removes_transaction_dir():
    ctrl = _mock_controller()
    pusher = DevicePusher(ctrl, sandbox_root="/sdcard/3is/")

    pusher.cleanup("TXN-300")

    ctrl.shell.assert_called_with("rm -rf /sdcard/3is/TXN-300")


def test_push_files_preserves_extension(tmp_path):
    ctrl = _mock_controller()
    pusher = DevicePusher(ctrl)

    local_pdf = tmp_path / "doc.pdf"
    local_pdf.write_bytes(b"data")

    downloaded = [
        DownloadedFile(attachment_id="att_pdf", local_path=str(local_pdf), md5_ok=True),
    ]

    results = pusher.push_files("TXN-400", downloaded)

    assert results[0].local_path.endswith(".pdf")


def test_push_files_no_extension_defaults_bin(tmp_path):
    ctrl = _mock_controller()
    pusher = DevicePusher(ctrl)

    local_noext = tmp_path / "noext"
    local_noext.write_bytes(b"data")

    downloaded = [
        DownloadedFile(attachment_id="att_noext", local_path=str(local_noext), md5_ok=True),
    ]

    results = pusher.push_files("TXN-500", downloaded)

    assert results[0].local_path.endswith(".bin")
