# Sync Transaction Customer Phone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `customer_phone` to the worker's transaction sync `meta` dict and the airtest environment-variable injection, so Airtest scripts can read the customer's phone number via `os.environ["CUSTOMER_PHONE"]`.

**Architecture:** The backend poll response already returns `customer_phone` (`backend/api/v1/tasks.py:61`). The worker's `meta` dict (`worker/main.py:190-196`) currently omits it. We add it to the `meta` dict, to the `_META_TO_ENV` env-var mapping in `worker/airtest_executor.py`, and add a runtime warning when it's missing -- mirroring the existing `holder_phone` pattern.

**Tech Stack:** Python 3.13, pytest 9.0.3, airtest 1.4.3. Worker tests run from the `worker/` directory using bare module imports (e.g. `from file_downloader import FileDownloader`), no package prefix.

## Global Constraints

- Worker Python version: `>=3.13,<3.14` (use `dict | None` syntax, not `Optional[Dict]`)
- Tests run via `python -m pytest` from the `worker/` directory (rootdir has its own `pyproject.toml` with `testpaths = ["tests"]`)
- Imports in worker tests are bare: `from airtest_executor import AirtestExecutor`, `from file_downloader import FileDownloader, DownloadedFile`
- Do NOT modify backend code, `.air` scripts, or existing `holder_phone` behavior
- Warning policy: `logger.warning` (NOT raise) when `customer_phone` is missing -- do not abort dispatch

---

### Task 1: Add `customer_phone` to the airtest env-var mapping

**Files:**
- Modify: `worker/airtest_executor.py:13-19` (`_META_TO_ENV` dict)
- Modify: `worker/airtest_executor.py:86-88` (`run_script` docstring)
- Test: `worker/tests/test_airtest_executor.py` (create)

**Interfaces:**
- Consumes: nothing new (the `meta` dict is constructed later in Task 2)
- Produces: `_META_TO_ENV` now contains `"customer_phone": "CUSTOMER_PHONE"`, so any `transaction_meta` dict with a `customer_phone` key will be injected as `os.environ["CUSTOMER_PHONE"]`

- [ ] **Step 1: Write the failing test**

Create `worker/tests/test_airtest_executor.py`:

```python
import os
from unittest.mock import MagicMock, patch

from airtest_executor import AirtestExecutor


def _make_executor():
    """Build an AirtestExecutor without connecting to a device."""
    executor = AirtestExecutor.__new__(AirtestExecutor)
    executor.adb_serial = "test_serial"
    executor.device = None
    return executor


def test_run_script_injects_customer_phone():
    """CUSTOMER_PHONE env var is set during the airtest call and cleaned after."""
    executor = _make_executor()

    captured = {}

    def fake_run_script(args):
        captured["CUSTOMER_PHONE"] = os.environ.get("CUSTOMER_PHONE")
        captured["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")

    with patch("airtest_executor._airtest_run_script", side_effect=fake_run_script):
        executor.run_script(
            "/tmp/fake.air",
            transaction_meta={
                "transaction_id": "T-1",
                "holder_phone": "13800138000",
                "customer_phone": "13900139000",
                "business_type": "NEW_VEHICLE",
                "tax_exempt": False,
                "is_transfer": True,
            },
        )

    assert captured["CUSTOMER_PHONE"] == "13900139000"
    assert captured["HOLDER_PHONE"] == "13800138000"
    # After the call, injected vars must be cleaned up
    assert "CUSTOMER_PHONE" not in os.environ
    assert "HOLDER_PHONE" not in os.environ
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd worker && python -m pytest tests/test_airtest_executor.py::test_run_script_injects_customer_phone -v
```
Expected: FAIL -- `CUSTOMER_PHONE` will be `None` during the call because `_META_TO_ENV` does not yet contain `customer_phone`

- [ ] **Step 3: Add `customer_phone` to `_META_TO_ENV`**

In `worker/airtest_executor.py`, edit the `_META_TO_ENV` dict (lines 13-19) to add the new entry:

```python
_META_TO_ENV = {
    "transaction_id": "TRANSACTION_ID",
    "holder_phone":   "HOLDER_PHONE",
    "customer_phone": "CUSTOMER_PHONE",
    "business_type":  "BUSINESS_TYPE",
    "tax_exempt":     "TAX_EXEMPT",
    "is_transfer":    "IS_TRANSFER",
}
```

- [ ] **Step 4: Update the `run_script` docstring**

In `worker/airtest_executor.py`, the docstring of `run_script` (around line 86) says "the 5 known keys". Update it to "the 6 known keys" and mention `CUSTOMER_PHONE` alongside `HOLDER_PHONE`:

Change:
```
        reads them via ``os.environ.get("HOLDER_PHONE")`` etc., and then
```
to:
```
        reads them via ``os.environ.get("HOLDER_PHONE")``,
        ``os.environ.get("CUSTOMER_PHONE")`` etc., and then
```

And change:
```
        If ``transaction_meta`` is provided, the 5 known keys are injected into
```
to:
```
        If ``transaction_meta`` is provided, the 6 known keys are injected into
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd worker && python -m pytest tests/test_airtest_executor.py::test_run_script_injects_customer_phone -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add worker/airtest_executor.py worker/tests/test_airtest_executor.py
git commit -m "feat: add CUSTOMER_PHONE to airtest env-var injection mapping"
```

---

### Task 2: Add `customer_phone` to the worker `meta` dict + missing-field warning

**Files:**
- Modify: `worker/main.py:190-196` (`meta` dict construction)
- Modify: `worker/main.py:203-208` (add `customer_phone` warning after the `holder_phone` warning)
- Test: `worker/tests/test_file_downloader.py` (append)
- Test: `worker/tests/test_main_warning.py` (create)

**Interfaces:**
- Consumes: `_META_TO_ENV` from Task 1 now knows `customer_phone -> CUSTOMER_PHONE`
- Produces: `meta` dict now contains `customer_phone` key; `dispatch_to_device` warns when it's `None`

- [ ] **Step 1: Write the failing JSON-file test**

Append to `worker/tests/test_file_downloader.py`:

```python
import json


def test_save_transaction_meta_writes_customer_phone(tmp_path):
    """save_transaction_meta persists customer_phone into the JSON file."""
    downloader = FileDownloader(str(tmp_path))
    downloader.save_transaction_meta(
        "T-1",
        {
            "transaction_id": "T-1",
            "holder_phone": "13800138000",
            "customer_phone": "13900139000",
            "business_type": "NEW_VEHICLE",
            "tax_exempt": False,
            "is_transfer": False,
        },
    )
    meta_path = tmp_path / "T-1" / "transaction_meta.json"
    with open(meta_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["customer_phone"] == "13900139000"
    assert data["holder_phone"] == "13800138000"
```

- [ ] **Step 2: Run test to verify it passes (contract test)**

Run:
```bash
cd worker && python -m pytest tests/test_file_downloader.py::test_save_transaction_meta_writes_customer_phone -v
```
Expected: PASS -- This is a positive contract test: it supplies the `customer_phone` value directly in the test dict, so it passes independently of `main.py`. Its purpose is to lock in the JSON file format so future changes don't drop the field. Step 3 below is the change that makes `main.py` actually populate this field in production.

- [ ] **Step 3: Add `customer_phone` to the `meta` dict in `main.py`**

In `worker/main.py`, edit the `meta` dict (lines 190-196). Add the `customer_phone` line after `holder_phone`:

```python
        meta = {
            "transaction_id": transaction_id,
            "holder_phone": txn.get("holder_phone"),
            "customer_phone": txn.get("customer_phone"),
            "business_type": txn.get("business_type"),
            "tax_exempt": txn.get("tax_exempt", False),
            "is_transfer": txn.get("is_transfer", False),
        }
```

- [ ] **Step 4: Add the `customer_phone` missing-field warning**

In `worker/main.py`, immediately after the existing `holder_phone` warning block (which ends at line 208), add:

```python
        if meta.get("customer_phone") is None:
            logger.warning(
                "txn %s: customer_phone missing from poll response "
                "(business_type=%s); Airtest script will see CUSTOMER_PHONE unset",
                transaction_id, meta.get("business_type"),
            )
```

- [ ] **Step 5: Run the JSON-file test to verify it passes**

Run:
```bash
cd worker && python -m pytest tests/test_file_downloader.py::test_save_transaction_meta_writes_customer_phone -v
```
Expected: PASS

- [ ] **Step 6: Write the warning tests**

Create `worker/tests/test_main_warning.py`:

```python
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

    # fetch_download_urls must return a matching signed URL so dispatch proceeds
    download_urls = [
        {"attachment_id": "att_1", "url": "http://example.com/a.jpg"},
    ]

    # _download_with_refresh must return a list with md5_ok=True so dispatch
    # proceeds past the download check to the meta/warning section.
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
```

- [ ] **Step 7: Run warning test to verify it fails (TDD red)**

Run this BEFORE applying Step 4 (the warning code). If you already applied Step 4, temporarily comment out the `customer_phone` warning block to see the test fail, then restore it.

Run:
```bash
cd worker && python -m pytest tests/test_main_warning.py -v
```
Expected: FAIL -- `test_dispatch_warns_when_customer_phone_missing` fails because no "customer_phone missing" warning is logged yet

- [ ] **Step 8: Run warning test to verify it passes (TDD green)**

Ensure Step 4 (the `customer_phone` warning code) is applied, then run:

Run:
```bash
cd worker && python -m pytest tests/test_main_warning.py -v
```
Expected: PASS (both tests)

- [ ] **Step 9: Commit**

```bash
git add worker/main.py worker/tests/test_file_downloader.py worker/tests/test_main_warning.py
git commit -m "feat: add customer_phone to worker meta dict with missing-field warning"
```

---

### Task 3: Full regression run

**Files:**
- None modified

- [ ] **Step 1: Run the entire worker test suite**

Run:
```bash
cd worker && python -m pytest -v
```
Expected: All tests PASS, including the new `test_run_script_injects_customer_phone`, `test_save_transaction_meta_writes_customer_phone`, `test_dispatch_warns_when_customer_phone_missing`, and `test_dispatch_no_warning_when_customer_phone_present`.

- [ ] **Step 2: Verify no regressions in existing tests**

Confirm that the existing `holder_phone` warning still works (if a test exists) and no existing test broke from the `_META_TO_ENV` change or the `meta` dict change.

- [ ] **Step 3: Commit (if any fixups were needed)**

If everything passes without changes, skip this step. Otherwise:
```bash
git add -A
git commit -m "fix: address test regressions from customer_phone addition"
```
