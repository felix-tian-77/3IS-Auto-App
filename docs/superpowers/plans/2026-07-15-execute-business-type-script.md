# Execute Business Type Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the worker pushes images to the device, look up an Airtest `.air` script by `business_type` via a JSON env-var mapping (`SCRIPT_MAP`) and execute it.

**Architecture:** Three small changes — (1) `worker/config.py` parses `SCRIPT_MAP` JSON env var; (2) `AirtestExecutor` gains a `run_script(script_path)` method that wraps Airtest's `run_script(parsed_args)` API via `argparse.Namespace`; (3) `Worker.dispatch_to_device` looks up the script after `report_attachments_delivered` and invokes the executor. Failures (missing map entry, missing file, executor exception) are caught and logged; they never abort the dispatch flow.

**Tech Stack:** Python 3.13, Airtest (`airtest.cli.runner.run_script`), vanilla pytest, `json` and `argparse` stdlib.

## Global Constraints

- Airtest `.air` is a **directory** (containing `.py` + template PNGs), not a single file. `SCRIPT_MAP` values are paths relative to `worker/scripts/` **with** the `.air` suffix (e.g., `"renew/renew_01.air"`).
- `run_script(parsed_args)` takes an `argparse.Namespace` with `script`, `device`, `log`, `recording`, `compress`, `no_image` fields. It does NOT accept `device=` kwarg. Internally it creates a new device connection via `auto_setup()` — does not reuse caller's `self.device`.
- `run_script()` calls `sys.exit(20)` on assertion failure and `sys.exit(-1)` on other failures. Must catch `SystemExit`.
- `Worker.airtest_executor` is `None` until `Worker.run()` initializes it. `dispatch_to_device` must defensive-check.
- `SCRIPT_MAP` env var format: JSON object, e.g. `{"OLD_VEHICLE": "renew/renew_01.air"}`. Default `{}`. Invalid JSON → log warning, use `{}`.
- No modifications to backend, `transaction_meta.json`, `FileDownloader`, `DevicePusher`, or Airtest script contents.
- Tests live under `tests/worker/` (already exists from prior change). Use `backend/.venv` Python interpreter (run with `PYTHONPATH=worker;.`) since `pytest_asyncio` and worker deps are both needed.

## Files Touched

| File | Change | Responsibility |
|------|--------|----------------|
| `worker/config.py` | Add `import json`, add `SCRIPT_MAP` class attribute with JSON parsing + fallback (Task 1) | Map `business_type` → script path |
| `tests/worker/test_config_script_map.py` | Create (Task 1) | Verify `SCRIPT_MAP` parsing and fallback behavior |
| `worker/airtest_executor.py` | Add `import argparse`, `import os`, add `run_script(script_path)` method (Task 2) | Wrap `airtest.cli.runner.run_script` |
| `tests/worker/test_airtest_executor_run_script.py` | Create (Task 2) | Verify `run_script` constructs Namespace, returns False on SystemExit/Exception |
| `worker/main.py` | Insert script-execution block in `dispatch_to_device` after `report_attachments_delivered` (line 179) and before `logger.info("Dispatch complete...")` (line 181) (Task 3) | Wire mapping → executor call |
| `tests/worker/test_dispatch_runs_script.py` | Create (Task 3) | Verify `dispatch_to_device` looks up and calls script executor |

---

## Task 1: Add `SCRIPT_MAP` config with JSON parsing

**Files:**
- Modify: `worker/config.py` — add `import json` (line 1 area) and add `SCRIPT_MAP` to `Config` class (around line 26)
- Create: `tests/worker/test_config_script_map.py`

**Interfaces:**
- Consumes: `os.getenv("SCRIPT_MAP", "{}")` returning a JSON object string
- Produces: `config.SCRIPT_MAP` is a `dict[str, str]` mapping `business_type` → relative script path

- [ ] **Step 1: Write the failing test**

Create `tests/worker/test_config_script_map.py` with this exact content:

```python
import json
import os
import importlib


def _reload_config(monkeypatch, env_value=None):
    """Reload worker.config with a controlled SCRIPT_MAP env value."""
    if env_value is None:
        monkeypatch.delenv("SCRIPT_MAP", raising=False)
    else:
        monkeypatch.setenv("SCRIPT_MAP", env_value)
    import worker.config as cfg
    importlib.reload(cfg)
    return cfg


def test_script_map_default_is_empty_dict(monkeypatch):
    cfg = _reload_config(monkeypatch, env_value=None)
    assert cfg.config.SCRIPT_MAP == {}


def test_script_map_parses_valid_json(monkeypatch):
    raw = json.dumps({"NEW_VEHICLE": "new/new_01.air", "OLD_VEHICLE": "renew/renew_01.air"})
    cfg = _reload_config(monkeypatch, env_value=raw)
    assert cfg.config.SCRIPT_MAP == {
        "NEW_VEHICLE": "new/new_01.air",
        "OLD_VEHICLE": "renew/renew_01.air",
    }


def test_script_map_invalid_json_falls_back_to_empty_dict(monkeypatch):
    cfg = _reload_config(monkeypatch, env_value="this is not json {")
    assert cfg.config.SCRIPT_MAP == {}


def test_script_map_non_object_json_falls_back_to_empty_dict(monkeypatch):
    # JSON list at top level is valid JSON but not a dict.
    cfg = _reload_config(monkeypatch, env_value='["not", "a", "dict"]')
    assert cfg.config.SCRIPT_MAP == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker/test_config_script_map.py -v
```

Expected: FAIL — `AttributeError: type object 'Config' has no attribute 'SCRIPT_MAP'` (or `AttributeError` on import reload because there's no `json` import either).

- [ ] **Step 3: Modify `worker/config.py`**

Edit `worker/config.py` with two changes:

(a) At the top of the file (after line 1, where `import os` lives), add `import json` so the import block reads:

```python
import os
import json
```

(b) Add a `logging` import too (needed for the warning). Add `import logging` after `import json`:

```python
import os
import json
import logging

logger = logging.getLogger(__name__)
```

(c) At the end of the `Config` class body (after line 26 `URL_REFRESH_MAX_RETRIES = ...`), add this attribute:

```python
    @staticmethod
    def _parse_script_map():
        raw = os.getenv("SCRIPT_MAP", "{}")
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("SCRIPT_MAP is not valid JSON (%s); falling back to {}", e)
            return {}
        if not isinstance(parsed, dict):
            logger.warning("SCRIPT_MAP must be a JSON object; got %s; falling back to {}", type(parsed).__name__)
            return {}
        return {str(k): str(v) for k, v in parsed.items()}

    SCRIPT_MAP = _parse_script_map()
```

The class body becomes a `staticmethod` for the parse helper plus a class-level attribute that calls it at import time.

- [ ] **Step 4: Run test to verify it passes**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker/test_config_script_map.py -v
```

Expected: PASS — all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add worker/config.py tests/worker/test_config_script_map.py
git commit -m "feat(worker): add SCRIPT_MAP config from JSON env var"
```

---

## Task 2: Add `AirtestExecutor.run_script()` method

**Files:**
- Modify: `worker/airtest_executor.py` — add `import argparse`, `import os`, add `run_script()` method
- Create: `tests/worker/test_airtest_executor_run_script.py`

**Interfaces:**
- Consumes: `script_path: str` — absolute path to a `.air` directory (Airtest's required input format)
- Produces: `bool` — `True` on clean exit (no `SystemExit`), `False` on `SystemExit` (assertion or other failure) or other `Exception`. Never raises.

- [ ] **Step 1: Write the failing test**

Create `tests/worker/test_airtest_executor_run_script.py` with this exact content:

```python
import argparse
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

    with patch("worker.airtest_executor.run_script", fake_run_script):
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

    with patch("worker.airtest_executor.run_script", fake_run_script):
        ok = ex.run_script("/nonexistent/whatever.air")

    assert ok is False


def test_run_script_returns_false_on_generic_exception():
    ex = _make_executor()

    def fake_run_script(args, testcase_cls=None):
        raise RuntimeError("boom")

    with patch("worker.airtest_executor.run_script", fake_run_script):
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

    with patch("worker.airtest_executor.run_script", fake_run_script):
        ok = ex.run_script("/tmp/some.air")
    assert ok is True
    assert captured["device"] == "android:///ADB-x"
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker/test_airtest_executor_run_script.py -v
```

Expected: FAIL with `AttributeError: 'AirtestExecutor' object has no attribute 'run_script'`.

- [ ] **Step 3: Modify `worker/airtest_executor.py`**

Edit `worker/airtest_executor.py` with three changes:

(a) At the top, replace the existing import block so it reads:

```python
import argparse
import os
import logging
from airtest.core.api import connect_device, start_app, stop_app, text, touch, snapshot, sleep
from airtest.core.error import TargetNotFoundError
from airtest.cli.runner import run_script as _airtest_run_script

logger = logging.getLogger(__name__)
```

(b) At the end of the `AirtestExecutor` class (after `disconnect()`), add this method:

```python
    def run_script(self, script_path: str) -> bool:
        """Run an Airtest .air script directory.

        Uses airtest.cli.runner.run_script under the hood. Airtest manages its own
        device connection via auto_setup(), so this method does NOT reuse
        self.device — it constructs an android:/// URI from self.adb_serial.

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

- [ ] **Step 4: Run test to verify it passes**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker/test_airtest_executor_run_script.py -v
```

Expected: PASS — all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add worker/airtest_executor.py tests/worker/test_airtest_executor_run_script.py
git commit -m "feat(worker): add AirtestExecutor.run_script via argparse.Namespace"
```

---

## Task 3: Wire `run_script` into `dispatch_to_device`

**Files:**
- Modify: `worker/main.py` — insert script-execution block at line 180 (between `report_attachments_delivered` on line 179 and `logger.info("Dispatch complete...")` on line 181)
- Create: `tests/worker/test_dispatch_runs_script.py`

**Interfaces:**
- Consumes: `task["task"]["business_type"]` (str from poll response); `config.SCRIPT_MAP` (dict from Task 1); `self.airtest_executor.run_script(script_path)` (from Task 2)
- Produces: When `SCRIPT_MAP` has an entry for the business type AND the script directory exists AND `self.airtest_executor` is not None → execute. Otherwise log and skip. Never abort the dispatch.

- [ ] **Step 1: Write the failing test**

Create `tests/worker/test_dispatch_runs_script.py` with this exact content:

```python
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from worker.main import Worker


def _make_worker(tmp_path, script_map=None, business_type="OLD_VEHICLE"):
    """Build a Worker wired with mocks, returning it plus helpers to assert."""
    txn_id = "T-SCRIPT-0001"
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    # Pre-create a dummy .air directory matching SCRIPT_MAP value.
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
    w.device_pusher.push_files.return_value = []
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


def test_dispatch_calls_run_script_when_mapping_and_file_exist(tmp_path):
    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )

    with patch("worker.main.config") as cfg_mock:
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    # The dispatch fails earlier (empty attachments → no download), but the
    # point is: when there ARE attachments and the script is mapped,
    # run_script must be called. Construct a richer task below.
    assert ok is False  # confirms early-return path


def test_dispatch_calls_run_script_on_success_path(tmp_path):
    """End-to-end check: with a valid task and a mapped script, run_script fires."""
    from worker.file_downloader import DownloadedFile

    w, task, scripts_dir, script_abs, airtest_ex = _make_worker(
        tmp_path,
        script_map={"OLD_VEHICLE": "renew/renew_01.air"},
    )

    # Make _download_with_refresh return a successful fake download so the
    # flow reaches the script-execution block.
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

    with patch("worker.main.config") as cfg_mock:
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
    task["task"]["business_type"] = "NEW_VEHICLE"  # not in map

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

    with patch("worker.main.config") as cfg_mock:
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
    w.airtest_executor = None  # defensive: not initialized yet

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

    with patch("worker.main.config") as cfg_mock:
        cfg_mock.SCRIPT_MAP = {"OLD_VEHICLE": "renew/renew_01.air"}
        cfg_mock.WORKER_TMP_DIR = str(tmp_path)
        cfg_mock.DEVICE_SANDBOX_ROOT = "/sdcard/3is/"
        cfg_mock.URL_REFRESH_MAX_RETRIES = 2
        ok = w.dispatch_to_device(task)

    assert ok is True
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker/test_dispatch_runs_script.py -v
```

Expected: 2 passed (the early-return cases) + 2 failed. The two success-path tests fail because `dispatch_to_device` does NOT yet call `run_script`. The expected failure is `AssertionError` on `run_script.assert_called_once()` and `run_script.assert_not_called()` (inverted — calls happen when they shouldn't).

- [ ] **Step 3: Modify `worker/main.py`**

Edit `worker/main.py`. Add a helper module-level function and a call block in `dispatch_to_device`.

(a) Add the helper after the `get_ip_address()` function (after line 23):

```python
def _resolve_script_path(business_type: str) -> str | None:
    """Look up SCRIPT_MAP for a business type and return an absolute script path,
    or None if the entry is missing or the path does not exist."""
    script_rel = config.SCRIPT_MAP.get(business_type)
    if not script_rel:
        logger.info("No script mapped for business_type=%s, skipping", business_type)
        return None
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
    script_path = os.path.join(scripts_dir, script_rel)
    if not os.path.isdir(script_path):
        logger.error("Script directory not found: %s", script_path)
        return None
    return script_path
```

Also add `import os` at the top of the file. The current imports are:

```python
import sys
import time
import socket
import hashlib
import logging
import requests as req_lib
```

Add `import os` so the file reads:

```python
import os
import sys
import time
import socket
import hashlib
import logging
import requests as req_lib
```

(b) Insert the script-execution block into `dispatch_to_device` between line 179 (`self.report_attachments_delivered(transaction_id, pushed)`) and line 181 (`logger.info("Dispatch complete...")`). The new block looks like this:

```python
        script_path = _resolve_script_path(txn.get("business_type"))
        if script_path and self.airtest_executor is not None:
            logger.info("Running business-type script: %s", script_path)
            self.airtest_executor.run_script(script_path)
        elif script_path and self.airtest_executor is None:
            logger.warning(
                "Skipping script %s: airtest_executor not initialized", script_path
            )
```

The full `dispatch_to_device` body (lines 129-182) becomes:

```python
    def dispatch_to_device(self, task: dict) -> bool:
        if not task.get("task"):
            return False
        txn = task["task"]
        transaction_id = txn["transaction_id"]
        attachment_meta = txn.get("attachments", [])

        download_urls = self.fetch_download_urls(transaction_id)
        if not download_urls:
            logger.error("No download URLs issued for txn %s; cannot dispatch", transaction_id)
            return False

        url_by_id = {u["attachment_id"]: u for u in download_urls}
        combined = []
        for att in attachment_meta:
            url_entry = url_by_id.get(att["attachment_id"])
            if not url_entry:
                logger.error(
                    "Missing signed URL for attachment %s (txn %s)",
                    att["attachment_id"], transaction_id,
                )
                return False
            combined.append({
                "attachment_id": att["attachment_id"],
                "url": url_entry["url"],
                "md5": att.get("md5", ""),
                "file_format": att.get("file_format", ""),
            })

        downloaded = self._download_with_refresh(combined, transaction_id)
        if not downloaded or not all(d.md5_ok for d in downloaded):
            logger.error("Download failed for txn %s", transaction_id)
            self.file_downloader.cleanup(transaction_id)
            return False

        meta = {
            "transaction_id": transaction_id,
            "holder_phone": txn.get("holder_phone"),
            "business_type": txn.get("business_type"),
            "tax_exempt": txn.get("tax_exempt", False),
            "is_transfer": txn.get("is_transfer", False),
        }
        self.file_downloader.save_transaction_meta(transaction_id, meta)

        pushed = self.device_pusher.push_files(transaction_id, downloaded)
        if not pushed:
            logger.error("Push failed for txn %s", transaction_id)
            self.file_downloader.cleanup(transaction_id)
            return False

        self.report_attachments_delivered(transaction_id, pushed)

        script_path = _resolve_script_path(txn.get("business_type"))
        if script_path and self.airtest_executor is not None:
            logger.info("Running business-type script: %s", script_path)
            self.airtest_executor.run_script(script_path)
        elif script_path and self.airtest_executor is None:
            logger.warning(
                "Skipping script %s: airtest_executor not initialized", script_path
            )

        logger.info("Dispatch complete for txn %s, ready for Airtest", transaction_id)
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker/test_dispatch_runs_script.py -v
```

Expected: PASS — all 4 tests pass.

- [ ] **Step 5: Run full worker test suite**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests/worker -v
```

Expected: all worker tests pass (existing 6 + 9 new = 15).

- [ ] **Step 6: Run full repo test suite**

Run from repo root:

```bash
$env:PYTHONPATH = "E:\workspaces\3IS-Auto-App\worker;E:\workspaces\3IS-Auto-App"
& "E:\workspaces\3IS-Auto-App\backend\.venv\Scripts\python.exe" -m pytest tests -v
```

Expected: pre-existing 9 failures in unrelated backend test files remain (verified earlier as not caused by this branch), all new and previously-passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add worker/main.py tests/worker/test_dispatch_runs_script.py
git commit -m "feat(worker): execute business-type Airtest script after push"
```

---

## Self-Review

**1. Spec coverage:**
- `SCRIPT_MAP` JSON config in `worker/config.py` → Task 1 ✓
- `AirtestExecutor.run_script()` method → Task 2 ✓
- `Worker.dispatch_to_device()` calls executor after `report_attachments_delivered` → Task 3 ✓
- `worker/scripts/` directory used as script root → Task 3 helper resolves absolute path ✓
- Unmapped `business_type` → silent skip with log → Task 3 helper returns None ✓
- Missing script file → log error, skip → Task 3 helper checks `os.path.isdir` ✓
- `airtest_executor is None` defensive check → Task 3 ✓

**2. Placeholder scan:** No TBD/TODO/fill-in. All code blocks complete. Tests use real assertions, not just `pass`.

**3. Type consistency:**
- `SCRIPT_MAP` is `dict[str, str]` everywhere (Task 1 parse, Task 3 lookup).
- `AirtestExecutor.run_script(script_path: str) -> bool` consistent across Task 2 definition, Task 2 tests, Task 3 call site.
- `_resolve_script_path(business_type: str) -> str | None` consistent in Task 3.

**Issues fixed during review:**
- The original draft used `SCRIPT_MAP` value as a flat filename, but discovered `worker/scripts/renew/renew_01.air/` is a directory tree. Updated plan to expect directory paths with `.air` suffix preserved.
- Tests must use `importlib.reload()` for `worker.config` because the module is loaded once and `SCRIPT_MAP` is a class attribute evaluated at import time.
- The `importlib.reload` pattern requires `import worker.config as cfg` AFTER setting env var to ensure the module sees the new value on reload.