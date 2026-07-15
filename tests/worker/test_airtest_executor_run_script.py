from unittest.mock import patch, MagicMock

from worker.airtest_executor import AirtestExecutor


def _make_executor():
    ex = AirtestExecutor.__new__(AirtestExecutor)
    ex.adb_serial = "ADB-test-001"
    ex.device = MagicMock()
    return ex


def test_run_script_builds_correct_argparse_namespace(tmp_path):
    """run_script passes script path and android device URI to Airtest's run_script."""
    ex = _make_executor()
    script_dir = tmp_path / "renew_01.air"
    script_dir.mkdir()

    captured = {}

    def fake_run_script(args, testcase_cls=None):
        captured["script"] = args.script
        captured["device"] = args.device
        captured["log"] = args.log
        return None  # no SystemExit

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script(str(script_dir))

    assert ok is True
    assert captured["script"] == str(script_dir)
    assert captured["device"] == "android:///ADB-test-001"
    assert captured["log"] is True


def test_run_script_returns_false_on_systemexit():
    ex = _make_executor()

    def fake_run_script(args, testcase_cls=None):
        # Airtest calls sys.exit(20) on assertion failure.
        raise SystemExit(20)

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script("/nonexistent/whatever.air")

    assert ok is False


def test_run_script_returns_false_on_generic_exception():
    ex = _make_executor()

    def fake_run_script(args, testcase_cls=None):
        raise RuntimeError("boom")

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script("/nonexistent/whatever.air")

    assert ok is False


def test_run_script_does_not_rely_on_existing_device_attribute():
    """run_script must work even when self.device is None — Airtest creates its own."""
    ex = AirtestExecutor.__new__(AirtestExecutor)
    ex.adb_serial = "ADB-x"
    ex.device = None  # explicit: run_script must not touch self.device

    captured = {}

    def fake_run_script(args, testcase_cls=None):
        captured["device"] = args.device

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script("/tmp/some.air")
    assert ok is True
    assert captured["device"] == "android:///ADB-x"
