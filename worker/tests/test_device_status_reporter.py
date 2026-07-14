from unittest.mock import MagicMock, patch

from device_status_reporter import DeviceStatusReporter


def _mock_controller(status_return=None):
    ctrl = MagicMock()
    if status_return:
        ctrl.get_status = MagicMock(return_value=status_return)
    return ctrl


def test_report_ready_success():
    ctrl = _mock_controller()
    reporter = DeviceStatusReporter(ctrl, "http://localhost:8000", "tok")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("device_status_reporter.requests.post", return_value=mock_resp) as mock_post:
        result = reporter.report_ready("DEV-001")

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "DEV-001" in args[0]
    assert kwargs["json"] == {"status": "READY"}


def test_report_ready_failure_returns_false():
    ctrl = _mock_controller()
    reporter = DeviceStatusReporter(ctrl, "http://localhost:8000", "tok")

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "error"

    with patch("device_status_reporter.requests.post", return_value=mock_resp):
        result = reporter.report_ready("DEV-001")

    assert result is False


def test_report_status_sends_device_fields():
    status = {
        "battery_level": 85,
        "storage_free_mb": 16000,
        "screen_locked": False,
        "model": "Xiaomi 13",
        "android_version": "14",
    }
    ctrl = _mock_controller(status)
    reporter = DeviceStatusReporter(ctrl, "http://localhost:8000", "tok")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("device_status_reporter.requests.post", return_value=mock_resp) as mock_post:
        result = reporter.report_status("WKR-001")

    assert result is True
    args, kwargs = mock_post.call_args
    body = kwargs["json"]
    assert body["battery_level"] == 85
    assert body["storage_free_mb"] == 16000
    assert body["screen_locked"] is False
    assert body["adb_status"] == "CONNECTED"


def test_report_status_no_token_omits_auth_header():
    ctrl = _mock_controller({"battery_level": 50, "storage_free_mb": 1000, "screen_locked": True})
    reporter = DeviceStatusReporter(ctrl, "http://localhost:8000")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("device_status_reporter.requests.post", return_value=mock_resp) as mock_post:
        reporter.report_status("WKR-002")

    args, kwargs = mock_post.call_args
    assert "Authorization" not in kwargs.get("headers", {})
