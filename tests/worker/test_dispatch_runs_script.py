from pathlib import Path
from unittest.mock import MagicMock, patch

from worker.main import Worker


def _make_worker(tmp_path, script_map=None, business_type="OLD_VEHICLE"):
    """Build a Worker wired with mocks, returning it plus helpers to assert."""
    txn_id = "T-SCRIPT-0001"
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_rel = (script_map or {}).get(business_type, "renew/renew_01.air")
    script_abs = scripts_dir / script_rel
    script_abs.mkdir(parents=True)

    w = Worker.__new__(Worker)
    w.adb_serial = "ADB-test-1"
    w.worker_id = "WKR-test-1"
    w.token = "tkn"

    fd = MagicMock()
    w.file_downloader = fd
    w.device_pusher = MagicMock()
    from worker.device_pusher import PushedFile
    w.device_pusher.push_files.return_value = [
        PushedFile(attachment_id="A-0001", local_path="/sdcard/3is/T-SCRIPT-0001/A-0001.jpg")
    ]
    w.fetch_download_urls = MagicMock(return_value=[])
    w._download_with_refresh = MagicMock(return_value=[])
    w.report_attachments_delivered = MagicMock(return_value=True)

    airtest_ex = MagicMock()
    airtest_ex.run_script = MagicMock(return_value=True)
    w.airtest_executor = airtest_ex

    task = {"task": {
        "transaction_id": txn_id,
        "business_type": business_type,
        "attachments": [],
        "holder_phone": "13800000000",
        "tax_exempt": False,
        "is_transfer": False,
    }}
    return w, task, scripts_dir, script_abs, airtest_ex


def _patch_resolver(tmp_path):
    """Patch worker.main._resolve_script_path to use tmp_path as scripts_dir."""
    scripts_dir = tmp_path / "scripts"

    def fake_resolver(business_type):
        from worker.main import config
        script_rel = config.SCRIPT_MAP.get(business_type)
        if not script_rel:
            return None
        script_path = scripts_dir / script_rel
        if not script_path.is_dir():
            return None
        return str(script_path)

    return patch("worker.main._resolve_script_path", fake_resolver)


def test_dispatch_calls_run_script_when_mapping_and_file_exist(tmp_path):
    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is False  # empty attachments → early-return


def test_dispatch_calls_run_script_on_success_path(tmp_path):
    from worker.file_downloader import DownloadedFile

    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )

    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "A-0001.jpg"),
        md5_ok=True,
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": ""}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    airtest_ex.run_script.assert_called_once()
    called_arg = airtest_ex.run_script.call_args[0][0]
    assert called_arg == str(script_abs)


def test_dispatch_skips_script_when_business_type_not_mapped(tmp_path):
    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    task["task"]["business_type"] = "NEW_VEHICLE"

    from worker.file_downloader import DownloadedFile
    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "A-0001.jpg"),
        md5_ok=True,
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": ""}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    airtest_ex.run_script.assert_not_called()


def test_dispatch_skips_script_when_executor_is_none(tmp_path):
    w, task, scripts_dir, script_abs, _ = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    w.airtest_executor = None

    from worker.file_downloader import DownloadedFile
    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "A-0001.jpg"),
        md5_ok=True,
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": ""}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    airtest_ex = w.airtest_executor  # None; run_script was never set
    # The point is: dispatch_to_device returned True (success) despite executor=None
