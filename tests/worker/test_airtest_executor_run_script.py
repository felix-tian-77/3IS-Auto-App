import os
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


def test_run_script_injects_env_vars_when_meta_provided():
    """Calling run_script with transaction_meta injects all 5 keys into os.environ for the duration of the call."""
    ex = _make_executor()

    captured_env = {}

    def fake_run_script(args, testcase_cls=None):
        # Snapshot os.environ at the moment the airtest runner is invoked.
        for k in ("TRANSACTION_ID", "HOLDER_PHONE", "BUSINESS_TYPE", "TAX_EXEMPT", "IS_TRANSFER"):
            captured_env[k] = os.environ.get(k)

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script(
            "/tmp/fake.air",
            transaction_meta={
                "transaction_id": "T-1",
                "holder_phone": "13800138000",
                "business_type": "NEW_VEHICLE",
                "tax_exempt": False,
                "is_transfer": True,
            },
        )

    assert ok is True
    assert captured_env == {
        "TRANSACTION_ID": "T-1",
        "HOLDER_PHONE": "13800138000",
        "BUSINESS_TYPE": "NEW_VEHICLE",
        "TAX_EXEMPT": "false",
        "IS_TRANSFER": "true",
    }


def test_run_script_restores_existing_env_after_call():
    """If os.environ already has HOLDER_PHONE before the call, its prior value is restored after."""
    ex = _make_executor()
    os.environ["HOLDER_PHONE"] = "old"

    try:
        def fake_run_script(args, testcase_cls=None):
            pass

        with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
            ok = ex.run_script(
                "/tmp/fake.air",
                transaction_meta={"holder_phone": "new", "transaction_id": "T-X"},
            )
        assert ok is True
        assert os.environ["HOLDER_PHONE"] == "old", (
            "HOLDER_PHONE must be restored to its pre-call value, not overwritten"
        )
    finally:
        os.environ.pop("HOLDER_PHONE", None)


def test_run_script_pops_injected_keys_when_no_prior_value():
    """If os.environ had no HOLDER_PHONE before the call, the key is gone after the call."""
    ex = _make_executor()
    os.environ.pop("HOLDER_PHONE", None)
    assert "HOLDER_PHONE" not in os.environ

    def fake_run_script(args, testcase_cls=None):
        pass

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script(
            "/tmp/fake.air",
            transaction_meta={"holder_phone": "13800138000"},
        )
    assert ok is True
    assert "HOLDER_PHONE" not in os.environ, (
        "HOLDER_PHONE must be removed after the call when it did not exist before"
    )


def test_run_script_with_none_meta_does_not_touch_env():
    """Calling run_script with transaction_meta=None leaves the 5 keys untouched."""
    ex = _make_executor()

    # Pre-populate one of the keys with a sentinel to prove it isn't touched.
    os.environ["BUSINESS_TYPE"] = "SENTINEL"
    try:
        def fake_run_script(args, testcase_cls=None):
            pass

        with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
            ok = ex.run_script("/tmp/fake.air")  # no transaction_meta kwarg
        assert ok is True
        assert os.environ["BUSINESS_TYPE"] == "SENTINEL", (
            "transaction_meta=None must leave os.environ untouched"
        )
    finally:
        os.environ.pop("BUSINESS_TYPE", None)


def test_run_script_skips_none_meta_values():
    """None values in transaction_meta are NOT written to os.environ (key stays absent)."""
    ex = _make_executor()
    # Ensure clean slate.
    for k in ("HOLDER_PHONE", "BUSINESS_TYPE"):
        os.environ.pop(k, None)

    snapshot_during_call = {}

    def fake_run_script(args, testcase_cls=None):
        # Capture os.environ state at the moment airtest would run.
        snapshot_during_call["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")
        snapshot_during_call["BUSINESS_TYPE"] = os.environ.get("BUSINESS_TYPE")

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script(
            "/tmp/fake.air",
            transaction_meta={
                "holder_phone": None,        # must be skipped → key absent
                "business_type": "NEW_VEHICLE",  # must be present
            },
        )
    assert ok is True
    # None-valued fields stay absent (os.environ.get returns None).
    assert snapshot_during_call["HOLDER_PHONE"] is None, (
        f"HOLDER_PHONE must be absent when meta['holder_phone'] is None; "
        f"saw {snapshot_during_call['HOLDER_PHONE']!r}"
    )
    # Truthy-valued fields land as strings.
    assert snapshot_during_call["BUSINESS_TYPE"] == "NEW_VEHICLE"
    # After the call, the helper restored the snapshot — absent keys stay absent.
    assert "HOLDER_PHONE" not in os.environ


def test_run_script_restores_env_after_systemexit_with_meta(monkeypatch):
    """If airtest raises SystemExit, the injected env var was visible AND was restored after."""
    monkeypatch.setenv("HOLDER_PHONE", "old")
    ex = _make_executor()

    seen = {}

    def fake_run_script(args, testcase_cls=None):
        # Capture what the airtest process would have seen.
        seen["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")
        raise SystemExit(20)

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script("/tmp/fake.air", transaction_meta={"holder_phone": "new"})

    assert ok is False
    # During execution the injected value was visible.
    assert seen["HOLDER_PHONE"] == "new"
    # After the call, the prior value is restored.
    assert os.environ.get("HOLDER_PHONE") == "old"


def test_run_script_restores_env_after_exception_with_meta(monkeypatch):
    """If airtest raises a regular Exception, the injected env var was visible AND was restored after."""
    monkeypatch.setenv("HOLDER_PHONE", "old")
    monkeypatch.delenv("BUSINESS_TYPE", raising=False)
    ex = _make_executor()

    seen = {}

    def fake_run_script(args, testcase_cls=None):
        seen["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")
        raise RuntimeError("boom")

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script(
            "/tmp/fake.air",
            transaction_meta={"holder_phone": "13800138000", "business_type": "X"},
        )

    assert ok is False
    assert seen["HOLDER_PHONE"] == "13800138000"
    assert os.environ.get("HOLDER_PHONE") == "old"
    assert "BUSINESS_TYPE" not in os.environ


def test_run_script_pops_stale_env_for_none_meta_value(monkeypatch):
    """If meta has holder_phone=None AND os.environ has a stale value, the stale
    value is hidden during execution and restored after."""
    monkeypatch.setenv("HOLDER_PHONE", "stale_phone")
    monkeypatch.delenv("BUSINESS_TYPE", raising=False)
    ex = _make_executor()

    seen_during_call = {}

    def fake_run_script(args, testcase_cls=None):
        # Capture what the airtest process would have seen at execution time.
        seen_during_call["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")
        seen_during_call["BUSINESS_TYPE"] = os.environ.get("BUSINESS_TYPE")

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script(
            "/tmp/fake.air",
            transaction_meta={"holder_phone": None, "business_type": "NEW_VEHICLE"},
        )

    assert ok is True
    # Stale value MUST be hidden during execution.
    assert seen_during_call["HOLDER_PHONE"] is None, (
        f"stale HOLDER_PHONE must be popped when meta['holder_phone'] is None; "
        f"saw {seen_during_call['HOLDER_PHONE']!r}"
    )
    # Truthy meta field is visible as before.
    assert seen_during_call["BUSINESS_TYPE"] == "NEW_VEHICLE"
    # After the call, the stale value MUST be restored.
    assert os.environ.get("HOLDER_PHONE") == "stale_phone"
