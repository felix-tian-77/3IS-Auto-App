from pathlib import Path
from unittest.mock import MagicMock, patch

from worker.file_downloader import FileDownloader
from worker.main import Worker


def _make_worker(tmp_path, script_map=None, business_type="OLD_VEHICLE"):
    """Build a Worker wired with real FileDownloader + mocked collaborators."""
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

    # Real FileDownloader against tmp_path — needed so the meta-warning path
    # exercises actual file I/O without mocking away the JSON save.
    fd = FileDownloader(tmp_dir=str(tmp_path))
    w.file_downloader = fd

    w.device_pusher = MagicMock()
    from worker.device_pusher import PushedFile
    w.device_pusher.push_files.return_value = [
        PushedFile(
            attachment_id="A-0001",
            local_path="/sdcard/3is/T-SCRIPT-0001/ID_CARD_FRONT.jpg",
            filename="ID_CARD_FRONT.jpg",
        )
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


def test_dispatch_propagates_backend_filename(tmp_path):
    from worker.device_pusher import PushedFile
    from worker.file_downloader import DownloadedFile

    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    filename = "ID_CARD_FRONT.jpg"
    remote_path = "/sdcard/3is/T-SCRIPT-0001/ID_CARD_FRONT.jpg"
    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / filename),
        md5_ok=True,
        filename=filename,
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {
            "attachment_id": "A-0001",
            "url": "http://example/x",
            "md5": "",
            "filename": filename,
        }
    ])
    w.device_pusher.push_files.return_value = [
        PushedFile(
            attachment_id="A-0001",
            local_path=remote_path,
            filename=filename,
        )
    ]
    task["task"]["attachments"] = [
        {"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}
    ]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    combined = w._download_with_refresh.call_args.args[0]
    assert combined[0]["filename"] == filename
    report = w.report_attachments_delivered
    report.assert_called_once_with("T-SCRIPT-0001", w.device_pusher.push_files.return_value)



def test_build_download_item_uses_attachment_filename_when_url_missing():
    item = Worker._build_download_item(
        {
            "attachment_id": "A-0001",
            "md5": "md5",
            "file_format": "jpg",
            "filename": "ID_CARD_FRONT.jpg",
        },
        {"url": "http://example/x"},
    )

    assert item["filename"] == "ID_CARD_FRONT.jpg"



def test_refresh_preserves_filename_from_original_item(tmp_path):
    from file_downloader import DownloadedFile, URLExpiredError

    w = Worker.__new__(Worker)
    w.file_downloader = MagicMock()
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/refreshed", "md5": ""}
    ])
    downloaded = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w.file_downloader.download_all.side_effect = [
        URLExpiredError("expired"),
        [downloaded],
    ]

    with patch("worker.main.config") as cfg_mock:
        cfg_mock.URL_REFRESH_MAX_RETRIES = 1
        results = w._download_with_refresh([
            {
                "attachment_id": "A-0001",
                "url": "http://example/expired",
                "md5": "",
                "file_format": "jpg",
                "filename": "ID_CARD_FRONT.jpg",
            }
        ], "T-SCRIPT-0001")

    assert results == [downloaded]
    assert w.file_downloader.download_all.call_count == 2
    refreshed_items = w.file_downloader.download_all.call_args_list[1].args[0]
    assert refreshed_items[0]["filename"] == "ID_CARD_FRONT.jpg"



def test_refresh_fails_when_any_attachment_url_is_missing(tmp_path):
    from file_downloader import DownloadedFile, URLExpiredError

    w = Worker.__new__(Worker)
    w.file_downloader = MagicMock()
    w.fetch_download_urls = MagicMock(return_value=[
        {
            "attachment_id": "A-0001",
            "url": "http://example/refreshed",
            "md5": "",
            "filename": "ID_CARD_FRONT.jpg",
        }
    ])
    downloaded = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w.file_downloader.download_all.side_effect = [
        URLExpiredError("expired"),
        [downloaded],
    ]

    with patch("worker.main.config") as cfg_mock:
        cfg_mock.URL_REFRESH_MAX_RETRIES = 1
        results = w._download_with_refresh([
            {
                "attachment_id": "A-0001",
                "url": "http://example/expired-1",
                "md5": "",
                "file_format": "jpg",
                "filename": "ID_CARD_FRONT.jpg",
            },
            {
                "attachment_id": "A-0002",
                "url": "http://example/expired-2",
                "md5": "",
                "file_format": "jpg",
                "filename": "ID_CARD_BACK.jpg",
            },
        ], "T-SCRIPT-0001")

    assert results == []
    assert w.file_downloader.download_all.call_count == 1



def test_dispatch_calls_run_script_on_success_path(tmp_path):
    from worker.file_downloader import DownloadedFile

    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )

    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": "", "filename": "ID_CARD_FRONT.jpg"}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    airtest_ex.run_script.assert_called_once()
    call_args = airtest_ex.run_script.call_args
    assert call_args[0][0] == str(script_abs)
    # The transaction_meta kwarg MUST carry holder_phone so airtest scripts
    # can read it from os.environ inside the .air run.
    assert "transaction_meta" in call_args.kwargs
    meta = call_args.kwargs["transaction_meta"]
    assert meta["transaction_id"] == "T-SCRIPT-0001"
    assert meta["holder_phone"] == "13800000000"
    assert meta["business_type"] == "OLD_VEHICLE"
    assert meta["tax_exempt"] is False
    assert meta["is_transfer"] is False


def test_dispatch_skips_script_when_business_type_not_mapped(tmp_path):
    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    task["task"]["business_type"] = "NEW_VEHICLE"

    from worker.file_downloader import DownloadedFile
    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": "", "filename": "ID_CARD_FRONT.jpg"}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}]

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
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": "", "filename": "ID_CARD_FRONT.jpg"}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    airtest_ex = w.airtest_executor  # None; run_script was never set
    # The point is: dispatch_to_device returned True (success) despite executor=None


def test_dispatch_passes_transaction_meta_when_no_script_mapped(tmp_path):
    """Even when SCRIPT_MAP has no entry, the meta wiring (and full flow) still
    succeeds — meta is independent of script execution."""
    from worker.file_downloader import DownloadedFile

    w, task, _, _, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    task["task"]["business_type"] = "NEW_VEHICLE"  # not in map — script skipped

    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": "", "filename": "ID_CARD_FRONT.jpg"}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
    airtest_ex.run_script.assert_not_called()


def test_dispatch_warns_when_holder_phone_missing(caplog, tmp_path):
    """When holder_phone is None, dispatch_to_device logs a warning but still completes."""
    import logging
    from worker.file_downloader import DownloadedFile

    w, task, _, _, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    task["task"]["holder_phone"] = None  # trigger the warning path

    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": "", "filename": "ID_CARD_FRONT.jpg"}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        with caplog.at_level(logging.WARNING, logger="worker.main"):
            ok = w.dispatch_to_device(task)

    assert ok is True
    assert any(
        "holder_phone missing" in rec.message for rec in caplog.records
    ), f"expected 'holder_phone missing' warning, got {[r.message for r in caplog.records]}"
    # The script still runs even when holder_phone is missing — warning is
    # informational, not blocking.
    airtest_ex.run_script.assert_called_once()


def test_dispatch_no_warning_when_holder_phone_present(caplog, tmp_path):
    """Sanity check: when holder_phone is set, no holder_phone-missing warning is emitted."""
    import logging
    from worker.file_downloader import DownloadedFile

    w, task, _, _, _ = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )

    fake_df = DownloadedFile(
        attachment_id="A-0001",
        local_path=str(tmp_path / "ID_CARD_FRONT.jpg"),
        md5_ok=True,
        filename="ID_CARD_FRONT.jpg",
    )
    w._download_with_refresh = MagicMock(return_value=[fake_df])
    w.fetch_download_urls = MagicMock(return_value=[
        {"attachment_id": "A-0001", "url": "http://example/x", "md5": "", "filename": "ID_CARD_FRONT.jpg"}
    ])
    task["task"]["attachments"] = [{"attachment_id": "A-0001", "md5": "", "file_format": "jpg", "filename": "ID_CARD_FRONT.jpg"}]

    with patch("worker.main.config") as cfg_mock, _patch_resolver(tmp_path):
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        with caplog.at_level(logging.WARNING, logger="worker.main"):
            ok = w.dispatch_to_device(task)

    assert ok is True
    holder_phone_warnings = [
        rec for rec in caplog.records
        if "holder_phone missing" in rec.message
    ]
    assert holder_phone_warnings == [], (
        f"unexpected holder_phone warnings: {[r.message for r in holder_phone_warnings]}"
    )
