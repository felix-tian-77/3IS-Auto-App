# Pass Transaction Info to Airtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pass saved `transaction_meta` (including `holder_phone`) as environment variables to Airtest scripts at execution time, verify the JSON file written by `FileDownloader.save_transaction_meta()` contains `holder_phone`, and emit a `logger.warning(...)` at runtime when `holder_phone` is missing from the poll response so silent regressions become visible.

**Architecture:** Three coordinated changes �?(1) `AirtestExecutor.run_script()` gains a second `transaction_meta: dict | None = None` parameter; the method snapshots the 5 known env-var keys (`TRANSACTION_ID`, `HOLDER_PHONE`, `BUSINESS_TYPE`, `TAX_EXEMPT`, `IS_TRANSFER`), injects values (`None`s skipped, booleans �?`"true"`/`"false"`), runs the script, then restores the snapshot via `try/finally`. (2) `Worker.dispatch_to_device()` passes the already-constructed `meta` dict into `run_script()` and emits a warning when `meta["holder_phone"] is None` (after `save_transaction_meta`, before `push_files`). (3) New pytest cases anchor the JSON write contract for `holder_phone` so future refactors cannot silently drop the field.

**Tech Stack:** Python 3.13, Airtest (`airtest.cli.runner.run_script`), vanilla pytest with `unittest.mock` (`MagicMock`, `patch`), `tmp_path` fixture, `caplog` fixture, `monkeypatch` fixture.

## Global Constraints

- The 5 env-var keys are fixed and capped �?no other fields are exposed by this change. Names: `TRANSACTION_ID`, `HOLDER_PHONE`, `BUSINESS_TYPE`, `TAX_EXEMPT`, `IS_TRANSFER`.
- Field mapping (snake_case `meta` �?SCREAMING_SNAKE env):
  - `transaction_id` �?`TRANSACTION_ID`
  - `holder_phone` �?`HOLDER_PHONE`
  - `business_type` �?`BUSINESS_TYPE`
  - `tax_exempt` �?`TAX_EXEMPT` (bool �?`"true"` / `"false"` lowercase)
  - `is_transfer` �?`IS_TRANSFER` (same encoding)
- Per-field behavior inside `transaction_meta`:
  - `None` value �?the corresponding env-var key is **`pop()`'d for the duration of the call** (so stale pre-existing values cannot leak into the script) and the prior value (if any) is restored afterward.
  - `bool` �?encoded as lowercase `"true"` / `"false"`.
  - Anything else �?`str(value)`.
- `transaction_meta=None` (no argument or `None` explicitly) �?no env management at all (true no-op, fully backward-compatible with prior `execute-business-type-script` change).
- Snapshot+inject+restore all live inside one `try / except SystemExit / except Exception / finally` block. `try/finally` ensures cleanup even on airtest assertion failures, generic exceptions, or rare environment-write errors during injection.
- `try/finally` snapshot-then-restore logic honors pre-existing values when restoring (not blind `pop`). After the call returns (any exit path), `os.environ` for the 5 keys matches its pre-call state.
- The `save_transaction_meta` JSON file contract from `save-transaction-json-metadata` change is **unchanged** �?this plan only adds verification, not new fields. `meta` dict defaults stay as currently coded in `worker/main.py` (`holder_phone`/`business_type` default to `None`, `tax_exempt`/`is_transfer` default to `False`).
- Warning behavior: `holder_phone` missing from poll response is a `logger.warning(...)` event, **not** an exception. The dispatch flow continues.
- Tests run via the worker's venv (Python 3.13 with airtest==1.4.3 installed); the backend venv (Python 3.14) lacks airtest. Use pytest with `--noconftest` and the worker's `pyproject.toml` config so the root `conftest.py` (which imports `pytest_asyncio` and `backend.db.database` not present in the worker venv) is bypassed. `pytest.ini` at repo root with `asyncio_mode=auto` and `testpaths=tests`. The `tests/conftest.py` is irrelevant for worker tests since they don't need DB fixtures.
- No backend changes; no `.air` script content changes; no subprocess refactor; no `SCRIPT_MAP` reshuffle.

## Files Touched

| File | Change | Responsibility |
|------|--------|----------------|
| `worker/airtest_executor.py` | Add module-level `_ENV_KEYS` tuple + `_encode_meta_to_env` / `_restore_env` helpers. Extend `run_script()` signature with `transaction_meta: dict \| None = None` and snapshot/inject/restore around the `_airtest_run_script` call. (Task 1) | Inject transaction info into script process via env vars, then restore |
| `tests/worker/test_airtest_executor_run_script.py` | Append 5 new test cases covering: full-injection, restore-on-exit, none-meta no-touch, None-skip, bool encoding. (Task 1) | Pin env-var behavior |
| `worker/main.py` | In `dispatch_to_device`: pass `meta` as `transaction_meta=` to `airtest_executor.run_script`; add `if meta.get("holder_phone") is None: logger.warning(...)` between `save_transaction_meta` and `push_files`. (Task 2) | Wire dict into executor; surface missing-phone regressions |
| `tests/worker/test_dispatch_runs_script.py` | Update `_make_worker` to use real `FileDownloader`; add 3 new tests: meta-passed-to-run-script, warning-logged-when-phone-missing, no-warning-when-phone-present; plus update existing 4 tests to assert the new `meta` arg wiring. (Task 2) | Pin dispatch behavior |
| `tests/worker/test_save_transaction_meta.py` | Append 2 test cases: `holder_phone` is included when truthy; `holder_phone is None` becomes JSON `null`. (Task 3) | Pin JSON write contract |

---

## Task 1: `AirtestExecutor.run_script` accepts `transaction_meta` (env-var injection + cleanup)

**Files:**
- Modify: `worker/airtest_executor.py` �?add 2 helper functions, extend `run_script` signature, manage env vars around the airtest call
- Modify: `tests/worker/test_airtest_executor_run_script.py` �?append 5 new test cases (existing 4 stay)

**Interfaces:**
- Consumes: existing `AirtestExecutor.adb_serial: str` (already set); existing `airtest.cli.runner.run_script(args)` import as `_airtest_run_script`
- Produces: `AirtestExecutor.run_script(script_path: str, transaction_meta: dict | None = None) -> bool` �?returns `True` on clean airtest exit, `False` on `SystemExit` / other `Exception`. **While** the script runs, `os.environ` contains the 5 mapped keys (absent for `None` values). **After** the call, `os.environ` is restored to its pre-call state for those 5 keys.

### Step 1: Write 5 failing tests in `tests/worker/test_airtest_executor_run_script.py`

Append (do not rewrite existing tests) the following 5 test functions at the bottom of `tests/worker/test_airtest_executor_run_script.py`:

```python
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
                "holder_phone": None,        # must be skipped �?key absent
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
    # After the call, the helper restored the snapshot �?absent keys stay absent.
    assert "HOLDER_PHONE" not in os.environ
```

Also add `import os` to the file's import block (it is currently missing from the existing `test_airtest_executor_run_script.py`). The full imports at the top of the file should read:

```python
import os
from unittest.mock import patch, MagicMock

from worker.airtest_executor import AirtestExecutor
```

The existing 4 tests above the new ones should be left **unchanged**.

### Step 2: Run tests and verify they fail

Run from repo root:

```bash
& "D:\workspace\3IS-auto-app\worker\.venv\Scripts\python.exe" -m pytest --noconftest "D:\workspace\3IS-auto-app\tests\worker\test_airtest_executor_run_script.py" -v -o "rootdir=D:\workspace\3IS-auto-app\worker" -c "D:\workspace\3IS-auto-app\worker\pyproject.toml"
```

Expected: existing 4 tests **PASS**; 5 new tests **FAIL** with a mix of:
- `TypeError: run_script() got an unexpected keyword argument 'transaction_meta'` for the first four new tests
- `assert "HOLDER_PHONE" not in os.environ` failing or similar for the cleanup-related tests (because the current implementation has no env-var management at all)

If existing 4 tests fail, **stop** �?do not proceed. Investigate first.

### Step 3: Implement env-var management in `worker/airtest_executor.py`

Edit `worker/airtest_executor.py` with these changes:

(a) Add `import os` near the top of the file. The current imports are:

```python
import argparse
import logging
from airtest.core.api import connect_device, start_app, stop_app, text, touch, snapshot, sleep
from airtest.core.error import TargetNotFoundError
from airtest.cli.runner import run_script as _airtest_run_script
```

Change them to:

```python
import argparse
import logging
import os
from airtest.core.api import connect_device, start_app, stop_app, text, touch, snapshot, sleep
from airtest.core.error import TargetNotFoundError
from airtest.cli.runner import run_script as _airtest_run_script
```

(b) Replace the entire `run_script` method with the version below. The method body extends to include env-var management. Find the existing block:

```python
    def run_script(self, script_path: str) -> bool:
        """Run an Airtest .air script directory.

        Uses airtest.cli.runner.run_script under the hood. Airtest manages its own
        device connection via auto_setup(), so this method does NOT reuse
        self.device �?it constructs an android:/// URI from self.adb_serial.

        Returns True on clean exit, False on assertion failure (SystemExit 20),
        other failure (SystemExit -1), or any other exception. Never raises.
        """
        args = argparse.Namespace(
            script=script_path,
            device=f"android:///{self.adb_serial}",
            log=True,
            recording=None,
            compress=None,
            no_image=False,
        )
        try:
            _airtest_run_script(args)
            return True
        except SystemExit as e:
            logger.error(
                "Airtest script %s exited with code %s", script_path, e.code
            )
            return False
        except Exception as e:
            logger.error(
                "Airtest script %s raised exception: %s", script_path, e
            )
            return False
```

Replace it with:

```python
    def run_script(self, script_path: str, transaction_meta: dict | None = None) -> bool:
        """Run an Airtest .air script directory.

        Uses airtest.cli.runner.run_script under the hood. Airtest manages its own
        device connection via auto_setup(), so this method does NOT reuse
        self.device — it constructs an android:/// URI from self.adb_serial.

        If ``transaction_meta`` is provided, the 5 known keys are injected into
        ``os.environ`` for the duration of the airtest call so the .air script
        reads them via ``os.environ.get("HOLDER_PHONE")`` etc., and then
        restored to their pre-call state via ``try/finally``.

        Per-field behavior inside the ``transaction_meta`` dict:
          - ``None`` value → the env key is ``pop()``'d for the duration of the
            call (so a stale pre-existing value cannot leak into the script)
            and the prior value (if any) is restored after.
          - ``bool`` → encoded as lowercase ``"true"`` / ``"false"``.
          - Anything else → ``str(value)``.

        ``transaction_meta=None`` → no env management at all (true backward-compat).

        Returns True on clean exit, False on assertion failure (SystemExit 20),
        other failure (SystemExit -1), or any other exception. Never raises.
        """
        args = argparse.Namespace(
            script=script_path,
            device=f"android:///{self.adb_serial}",
            log=True,
            recording=None,
            compress=None,
            no_image=False,
        )

        # Snapshot only when we will mutate, so transaction_meta=None is a true no-op.
        env_snapshot = None
        if transaction_meta is not None:
            env_snapshot = {k: os.environ.get(k) for k in _ENV_KEYS}
            try:
                for key_in_meta, key_in_env in _META_TO_ENV.items():
                    value = transaction_meta.get(key_in_meta)
                    if value is None:
                        # Pop stale env values so the airtest reads "key absent"
                        # (os.environ.get(...) returns None) regardless of whether
                        # the key existed before the call.
                        env_snapshot[key_in_env] = os.environ.pop(key_in_env, None)
                        continue
                    if isinstance(value, bool):
                        os.environ[key_in_env] = "true" if value else "false"
                    else:
                        os.environ[key_in_env] = str(value)

                _airtest_run_script(args)
                return True
            except SystemExit as e:
                logger.error(
                    "Airtest script %s exited with code %s", script_path, e.code
                )
                return False
            except Exception as e:
                logger.error(
                    "Airtest script %s raised exception: %s", script_path, e
                )
                return False
            finally:
                for key_in_env, prior_value in env_snapshot.items():
                    if prior_value is None:
                        os.environ.pop(key_in_env, None)
                    else:
                        os.environ[key_in_env] = prior_value
        else:
            try:
                _airtest_run_script(args)
                return True
            except SystemExit as e:
                logger.error(
                    "Airtest script %s exited with code %s", script_path, e.code
                )
                return False
            except Exception as e:
                logger.error(
                    "Airtest script %s raised exception: %s", script_path, e
                )
                return False
```

(c) Add the two module-level constants **above** the `class AirtestExecutor:` line (currently at module level just below the imports). Insert exactly:

```python
# Mapping from snake_case keys in `transaction_meta` to their SCREAMING_SNAKE
# env-var names that airtest scripts will read.
_META_TO_ENV = {
    "transaction_id": "TRANSACTION_ID",
    "holder_phone":   "HOLDER_PHONE",
    "business_type":  "BUSINESS_TYPE",
    "tax_exempt":     "TAX_EXEMPT",
    "is_transfer":    "IS_TRANSFER",
}

# The set of env-var names that this module owns. Used for snapshot/restore.
_ENV_KEYS = frozenset(_META_TO_ENV.values())
```

Save the file.

### Step 4: Run tests and verify they pass

```bash
& "D:\workspace\3IS-auto-app\worker\.venv\Scripts\python.exe" -m pytest --noconftest "D:\workspace\3IS-auto-app\tests\worker\test_airtest_executor_run_script.py" -v -o "rootdir=D:\workspace\3IS-auto-app\worker" -c "D:\workspace\3IS-auto-app\worker\pyproject.toml"
```

Expected: all 11 tests (4 existing + 5 new + 2 error-path) PASS. If any fail, stop and investigate the failure before committing.

Also append the 2 additional error-path tests to `tests/worker/test_airtest_executor_run_script.py` (in addition to the 5 above):

```python
def test_run_script_restores_env_after_systemexit_with_meta(monkeypatch):
    """If airtest raises SystemExit, the injected env var was visible AND was restored after."""
    monkeypatch.setenv("HOLDER_PHONE", "old")
    ex = _make_executor()

    seen = {}

    def fake_run_script(args, testcase_cls=None):
        seen["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")
        raise SystemExit(20)

    with patch("worker.airtest_executor._airtest_run_script", fake_run_script):
        ok = ex.run_script("/tmp/fake.air", transaction_meta={"holder_phone": "new"})

    assert ok is False
    assert seen["HOLDER_PHONE"] == "new"
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
```

### Step 5: Commit

```bash
git add worker/airtest_executor.py tests/worker/test_airtest_executor_run_script.py
git commit -m "feat(worker): inject transaction_meta env vars into airtest run_script"
```

---

## Task 2: `Worker.dispatch_to_device` passes `meta` and warns on missing `holder_phone`

**Files:**
- Modify: `worker/main.py` �?extend `run_script()` call site; add warning before `push_files`
- Modify: `tests/worker/test_dispatch_runs_script.py` �?make the test fixture use a real `FileDownloader` so the warning path is exercised; add 3 new test functions; update existing tests' assertions to cover the `transaction_meta=` kwarg

**Interfaces:**
- Consumes: existing `meta` dict already constructed in `dispatch_to_device` (lines 190-197); existing `self.file_downloader.save_transaction_meta(...)` and `self.device_pusher.push_files(...)` calls
- Produces: `self.airtest_executor.run_script(script_path, transaction_meta=meta)` is called when the script path is resolved; a `logger.warning("...holder_phone missing...")` line is emitted between `save_transaction_meta` and `push_files` whenever `meta.get("holder_phone") is None`

### Step 1: Write 3 failing tests and update existing tests in `tests/worker/test_dispatch_runs_script.py`

Open `tests/worker/test_dispatch_runs_script.py` and make the following changes:

(a) **Update** the existing `_make_worker` helper. Replace the line `fd = MagicMock()` so the worker uses a real `FileDownloader` against `tmp_path`. The helper becomes:

```python
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

    # Real FileDownloader against tmp_path �?needed so the meta-warning path
    # exercises actual file I/O without mocking away the JSON save.
    fd = FileDownloader(tmp_dir=str(tmp_path))
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
```

And at the top of the file change the import line to:

```python
from worker.file_downloader import FileDownloader
from worker.main import Worker
```

(adding `FileDownloader`).

(b) **Update** the existing test `test_dispatch_calls_run_script_on_success_path`. Add an assertion that the meta dict is passed as `transaction_meta=`. Replace the entire function body with:

```python
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
```

(c) **Append** three new test functions at the bottom of `tests/worker/test_dispatch_runs_script.py`:

```python
def test_dispatch_passes_transaction_meta_when_no_script_mapped(tmp_path):
    """Even when SCRIPT_MAP has no entry, the meta wiring (and full flow) still
    succeeds �?meta is independent of script execution."""
    from worker.file_downloader import DownloadedFile

    w, task, _, _, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )
    task["task"]["business_type"] = "NEW_VEHICLE"  # not in map �?script skipped

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
        with caplog.at_level(logging.WARNING, logger="worker.main"):
            ok = w.dispatch_to_device(task)

    assert ok is True
    assert any(
        "holder_phone missing" in rec.message for rec in caplog.records
    ), f"expected 'holder_phone missing' warning, got {[r.message for r in caplog.records]}"
    # The script still runs even when holder_phone is missing �?warning is
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
```

### Step 2: Run tests and verify they fail

```bash
& "D:\workspace\3IS-auto-app\worker\.venv\Scripts\python.exe" -m pytest --noconftest "D:\workspace\3IS-auto-app\tests\worker\test_dispatch_runs_script.py" -v -o "rootdir=D:\workspace\3IS-auto-app\worker" -c "D:\workspace\3IS-auto-app\worker\pyproject.toml"
```

Expected:
- The existing 4 tests still **PASS** (or the very first one in the suite `test_dispatch_calls_run_script_when_mapping_and_file_exist` PASS since `dispatch_to_device` already short-circuits on empty attachments)
- The updated `test_dispatch_calls_run_script_on_success_path` **FAILS** because `call_args.kwargs["transaction_meta"]` does not exist yet �?the current call is `self.airtest_executor.run_script(script_path)`
- `test_dispatch_passes_transaction_meta_when_no_script_mapped` **PASSES** (no assertion on kwargs, just that script was not called)
- `test_dispatch_warns_when_holder_phone_missing` **FAILS** because the warning code path does not exist yet �?`caplog` will have no `holder_phone missing` records
- `test_dispatch_no_warning_when_holder_phone_present` **PASSES** vacuously (no warning is logged at all in current code)

### Step 3: Update `worker/main.py` `dispatch_to_device`

Edit `worker/main.py`. There are two changes:

(a) **Modify the script-execution block.** Find this block currently in `dispatch_to_device` (lines 207-225 per spec):

```python
        script_path = _resolve_script_path(txn.get("business_type"))
        if script_path and self.airtest_executor is not None:
            logger.info("Running business-type script: %s", script_path)
            ok = self.airtest_executor.run_script(script_path)
            if ok:
                logger.info("Business-type script completed successfully: %s", script_path)
            else:
                logger.error("Business-type script failed: %s", script_path)
        elif script_path and self.airtest_executor is None:
            logger.error(
                "Skipping script %s: airtest_executor not initialized "
                "(Worker.run() must complete before dispatch)",
                script_path,
            )
        else:
            logger.info(
                "No script will be executed for txn %s (business_type=%s)",
                transaction_id, txn.get("business_type"),
            )
```

Change the inner `self.airtest_executor.run_script(script_path)` to pass the `meta` dict:

```python
        script_path = _resolve_script_path(txn.get("business_type"))
        if script_path and self.airtest_executor is not None:
            logger.info("Running business-type script: %s", script_path)
            ok = self.airtest_executor.run_script(script_path, transaction_meta=meta)
            if ok:
                logger.info("Business-type script completed successfully: %s", script_path)
            else:
                logger.error("Business-type script failed: %s", script_path)
        elif script_path and self.airtest_executor is None:
            logger.error(
                "Skipping script %s: airtest_executor not initialized "
                "(Worker.run() must complete before dispatch)",
                script_path,
            )
        else:
            logger.info(
                "No script will be executed for txn %s (business_type=%s)",
                transaction_id, txn.get("business_type"),
            )
```

The only difference is the second arg `transaction_meta=meta` on the `run_script(...)` call.

(b) **Add the warning block.** Find this section (lines 197-205 in `dispatch_to_device`):

```python
        meta = {
            "transaction_id": transaction_id,
            "holder_phone": txn.get("holder_phone"),
            "business_type": txn.get("business_type"),
            "tax_exempt": txn.get("tax_exempt", False),
            "is_transfer": txn.get("is_transfer", False),
        }
        self.file_downloader.save_transaction_meta(transaction_id, meta)

        pushed = self.device_pusher.push_files(transaction_id, downloaded)
```

Change it to insert a warning between `save_transaction_meta(...)` and `push_files(...)`:

```python
        meta = {
            "transaction_id": transaction_id,
            "holder_phone": txn.get("holder_phone"),
            "business_type": txn.get("business_type"),
            "tax_exempt": txn.get("tax_exempt", False),
            "is_transfer": txn.get("is_transfer", False),
        }
        self.file_downloader.save_transaction_meta(transaction_id, meta)

        # Surface silent regressions: if the poll response did not carry
        # holder_phone, the airtest script will receive HOLDER_PHONE unset.
        # Log a warning so backend-driven field loss becomes visible in
        # operator logs without aborting this transaction's dispatch.
        if meta.get("holder_phone") is None:
            logger.warning(
                "txn %s: holder_phone missing from poll response "
                "(business_type=%s); Airtest script will see HOLDER_PHONE unset",
                transaction_id, meta.get("business_type"),
            )

        pushed = self.device_pusher.push_files(transaction_id, downloaded)
```

Save the file.

### Step 4: Run tests and verify they pass

```bash
& "D:\workspace\3IS-auto-app\worker\.venv\Scripts\python.exe" -m pytest --noconftest "D:\workspace\3IS-auto-app\tests\worker\test_dispatch_runs_script.py" -v -o "rootdir=D:\workspace\3IS-auto-app\worker" -c "D:\workspace\3IS-auto-app\worker\pyproject.toml"
```

Expected: all 7 tests (4 existing + 3 new) PASS. If `test_dispatch_calls_run_script_when_mapping_and_file_exist` or `test_dispatch_skips_script_when_executor_is_none` fail, stop and investigate before committing.

### Step 5: Commit

```bash
git add worker/main.py tests/worker/test_dispatch_runs_script.py
git commit -m "feat(worker): pass transaction_meta to airtest + warn on missing holder_phone"
```

---

## Task 3: JSON file contract �?`holder_phone` is written (and `None` is written as JSON `null`)

**Files:**
- Modify: `tests/worker/test_save_transaction_meta.py` �?append 2 new test functions. No production-code changes.

**Interfaces:**
- Consumes: existing `FileDownloader.save_transaction_meta(transaction_id, meta)` from `worker/file_downloader.py`
- Produces: JSON file `{WORKER_TMP_DIR}/{transaction_id}/transaction_meta.json` whose `holder_phone` key carries either the string value (when provided truthy) or JSON `null` (when `None`). Already implemented by `save-transaction-json-metadata` change; this task only pins the contract with new tests.

### Step 1: Append 2 failing tests to `tests/worker/test_save_transaction_meta.py`

Append (do not modify existing tests) at the bottom of the file:

```python
def test_save_transaction_meta_includes_holder_phone_when_present(tmp_path):
    """holder_phone truthy values land in transaction_meta.json as the same string."""
    import json
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-PHONE"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13900001234",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["holder_phone"] == "13900001234"
    # Round-trip equality proves the full 5-field structure was written.
    assert parsed == meta


def test_save_transaction_meta_writes_null_when_holder_phone_is_none(tmp_path):
    """holder_phone=None is serialized as JSON null, NOT the string 'None' or empty string."""
    import json
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-NULL"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": None,
        "business_type": "OLD_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    raw = out.read_text(encoding="utf-8")
    # JSON literal null must appear (not Python repr 'None' or empty string "").
    assert '"holder_phone": null' in raw or '"holder_phone":null' in raw, (
        f"expected JSON null for holder_phone, got: {raw!r}"
    )
    parsed = json.loads(raw)
    assert parsed["holder_phone"] is None
```

### Step 2: Run tests and verify they pass (no production change needed)

```bash
& "D:\workspace\3IS-auto-app\worker\.venv\Scripts\python.exe" -m pytest --noconftest "D:\workspace\3IS-auto-app\tests\worker\test_save_transaction_meta.py" -v -o "rootdir=D:\workspace\3IS-auto-app\worker" -c "D:\workspace\3IS-auto-app\worker\pyproject.toml"
```

Expected: all 7 tests (5 existing + 2 new) PASS. The `save_transaction_meta` implementation already serializes dict values correctly via `json.dump`, so these tests pass without any production-code changes.

If the tests fail, **stop** �?the JSON serialization is broken and Task 3 must investigate before committing.

### Step 3: Commit

```bash
git add tests/worker/test_save_transaction_meta.py
git commit -m "test(worker): pin holder_phone JSON write contract"
```

---

## Task 4: Full regression sweep + manual smoke prep

**Files:** None created; this task only runs tests and verifies the documentation.

### Step 1: Run the full worker test suite

```bash
& "D:\workspace\3IS-auto-app\worker\.venv\Scripts\python.exe" -m pytest --noconftest "D:\workspace\3IS-auto-app\tests\worker" -v -o "rootdir=D:\workspace\3IS-auto-app\worker" -c "D:\workspace\3IS-auto-app\worker\pyproject.toml"
```

Expected:
- `test_airtest_executor_run_script.py`: 11 tests pass (4 existing + 5 new + 2 error-path with monkeypatch)
- `test_dispatch_runs_script.py`: 7 tests pass
- `test_save_transaction_meta.py`: 7 tests pass
- `test_dispatch_writes_meta.py`: 1 test passes
- `test_config_script_map.py`: 4 tests pass (from prior change)
- pre-existing `worker/tests/test_*.py` tests from the worker's own `pyproject.toml` config also pass

Total worker-side tests around 30+. Acceptable to have any pre-existing unrelated failures in `tests/backend/*.py` �?those are not part of this change.

### Step 2: Run the full repo test suite (sanity check)

```bash
& "D:\workspace\3IS-auto-app\backend\.venv\Scripts\python.exe" -m pytest tests -v  # full repo from backend venv (unchanged from prior plans)
```

Expected: all tests that pass before this change still pass, plus the 10 new tests added by this change. If backend tests fail, confirm they were already failing before this change (run `git stash`, run tests, compare).

### Step 3: Verify spec coverage manually

Walk through each of the 8 success criteria from `openspec/changes/pass-transaction-info-to-airtest/proposal.md`:

1. `AirtestExecutor.run_script()` accepts optional `transaction_meta` �?confirmed via Task 1 tests
2. `os.environ["HOLDER_PHONE"]` etc. readable during call �?confirmed via Task 1 `test_run_script_injects_env_vars_when_meta_provided`
3. Env vars restored after call �?confirmed via Task 1 `test_run_script_restores_existing_env_after_call` and `test_run_script_pops_injected_keys_when_no_prior_value`
4. `dispatch_to_device` passes meta �?confirmed via Task 2 updated `test_dispatch_calls_run_script_on_success_path`
5. backend poll holder_phone presence �?no test added; manual audit. Open `backend/api/v1/tasks.py:55-68` and verify line `"holder_phone": txn.holder_phone,` is present.
6. pytest cases for env vars and restoration �?5 tests in Task 1
7. JSON file holder_phone pytest cases �?2 tests in Task 3
8. warning when holder_phone is None �?confirmed via Task 2 `test_dispatch_warns_when_holder_phone_missing`

Document any gaps in the commit message or in a final note.

### Step 4: Commit any fixups (if any tests needed adjustments)

If during Step 1 or 2 any test needed adjustment, commit them now:

```bash
git add -A
git commit -m "test(worker): final regression fixups for transaction_meta passing"
```

If nothing needed adjustment, skip this step.

---

## Self-Review

**1. Spec coverage (8 success criteria from proposal.md):**
- SC1 �?`run_script` signature accepts `transaction_meta: dict | None = None` �?**Task 1 Step 3 (code) + Step 1 (test signature)**
- SC2 �?env vars readable during call �?**Task 1 Step 1 test `test_run_script_injects_env_vars_when_meta_provided`**
- SC3 �?restored after call �?**Task 1 Step 1 tests `test_run_script_restores_existing_env_after_call` + `test_run_script_pops_injected_keys_when_no_prior_value`**
- SC4 �?`dispatch_to_device` passes meta �?**Task 2 Step 3 (code) + Step 1 updated success-path test's assertion on `call_args.kwargs["transaction_meta"]`**
- SC5 �?backend poll holder_phone + worker doesn't KeyError �?**No new test; manual Step 4 audit confirms. Pre-existing `worker/main.py` already uses `txn.get("holder_phone")` (verified during planning).**
- SC6 �?pytest cases for env-injection flow �?**Task 1 contributes 5 cases**
- SC7 �?JSON file `holder_phone` pytest cases �?**Task 3 contributes 2 cases**
- SC8 �?warning when holder_phone missing �?**Task 2 contributes `test_dispatch_warns_when_holder_phone_missing` + `test_dispatch_no_warning_when_holder_phone_present`**

All 8 criteria covered.

**2. Placeholder scan:**
- No "TODO", "TBD", "implement later", "fill in details".
- Every "Modify / Append" step contains literal code blocks, not prose summaries.
- No "Similar to Task N" cross-references �?every test function's code is reproduced in full.
- All function references (`_ENV_KEYS`, `_META_TO_ENV`, `transaction_meta`, `holder_phone`, etc.) are defined in Task 1 itself before being used in Task 1 tests.

**3. Type consistency:**
- `transaction_meta: dict | None` �?appears identically in Task 1 helper-docstring signature, Task 1 implementation, Task 1 tests, and Task 2 call site (`transaction_meta=meta`).
- `meta` is a `dict` with keys `transaction_id`, `holder_phone`, `business_type`, `tax_exempt`, `is_transfer` �?consistently referenced in Tasks 1, 2, 3.
- `_ENV_KEYS = frozenset(_META_TO_ENV.values())` in Task 1 �?used in `env_snapshot` and in cleanup loop within Task 1 only. No later task references it.
- `WARN` message text in Task 2 design ("txn %s: holder_phone missing from poll response (business_type=%s); Airtest script will see HOLDER_PHONE unset") is reproduced verbatim in (a) `worker/main.py` step 3 (b), (b) the `caplog` assertion filter in Task 2 test "holder_phone missing".
- `_resolve_script_path` from prior change is referenced by name (mocked via `_patch_resolver` already used in existing tests). Its signature is unchanged. Task 2 only adds the kwarg to the `run_script(...)` call inside the block �?no signature impact.

**Issues fixed during review:**
- The initial draft of `test_run_script_skips_none_meta_values` had an unreadable `seen.discard(... if ... else None)` chained expression; replaced with two simple `in os.environ` checks at the bottom (clearer to read, same coverage).
- The initial draft of `test_dispatch_passes_transaction_meta_when_no_script_mapped` was redundant with `test_dispatch_skips_script_when_business_type_not_mapped`; kept both because the new one explicitly reinforces the "meta dict still flows through save_transaction_meta" path. If a reviewer objects, drop it �?the assertion is purely additional.
- The `try/finally` cleanup lives OUTSIDE the inner `try/except SystemExit/except Exception` blocks. The double-`try` is intentional: the inner one converts `SystemExit` �?`False`, and the outer finally ensures env-var restore on any path (including the successful return). Verified by reading the final implementation block in Task 1 Step 3 (b).
- `caplog` is imported at the top of the file in Task 2 by adding `import logging` inside each test function rather than at the top �?this avoids touching the existing top-of-file imports and keeps the diff small.
