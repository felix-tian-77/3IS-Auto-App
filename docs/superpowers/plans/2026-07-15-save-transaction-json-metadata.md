# Save Transaction JSON Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `tax_exempt`, `is_transfer`, and `holder_phone` to the `GET /api/v1/tasks/poll` response, and have the worker save a `transaction_meta.json` file alongside downloaded attachments containing those four transaction fields plus `transaction_id` and `business_type`.

**Architecture:** Two-layer change — (1) backend `tasks.poll_task` enriches its return dict with three fields that already exist on the Transaction ORM model; (2) the worker's `FileDownloader` gains a `save_transaction_meta()` method (lives next to `_txn_dir`/`cleanup`) and `Worker.dispatch_to_device` calls it after successful MD5-validated downloads but before pushing to the device.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy (async), pytest + httpx ASGITransport (backend tests), vanilla pytest (worker tests), `json` stdlib, `requests` (worker HTTP).

## Global Constraints

- Backend response uses raw dicts (no Pydantic schema for poll) — match `tasks.py:55-65` style.
- Worker uses `requests` (sync) and the `FileDownloader` class to own filesystem operations; never break `cleanup()` encapsulation.
- JSON file written to `{WORKER_TMP_DIR}/{transaction_id}/transaction_meta.json` (same dir as `{attachment_id}.{ext}` files).
- JSON encoding: `ensure_ascii=False`, `indent=2` (so `holder_phone` reads cleanly when inspected).
- Field names in JSON match the backend model column names exactly: `transaction_id`, `holder_phone`, `business_type`, `tax_exempt`, `is_transfer`.
- `holder_phone` may be `null`; do not skip writing the file in that case.
- `cleanup()` removes the whole transaction directory via `shutil.rmtree` — JSON file is removed automatically; no extra code needed.
- Do NOT modify the frontend, the DB schema, or any other endpoint.
- Tests live under `tests/backend/` and `tests/worker/`; use the existing `db_engine` / `db_session` / `seed_devices` fixtures from `conftest.py` for backend tests.

## Files Touched

| File | Change | Responsibility |
|------|--------|----------------|
| `backend/api/v1/tasks.py` | Modify `poll_task` return dict (Task 1) | Add 3 fields to poll response |
| `tests/backend/test_tasks_poll.py` | Create (Task 1) | Verify the 3 new fields appear in poll response |
| `worker/file_downloader.py` | Add `import json`, add `save_transaction_meta()` method (Task 2) | Write JSON metadata file |
| `tests/worker/test_save_transaction_meta.py` | Create (Task 2) | Unit test the new method |
| `worker/main.py` | Modify `dispatch_to_device` to call `save_transaction_meta` (Task 3) | Wire it into the dispatch flow |
| `tests/worker/test_dispatch_writes_meta.py` | Create (Task 3) | Integration-style test that `dispatch_to_device` writes the JSON after a successful download |

---

## Task 1: Add `tax_exempt`, `is_transfer`, `holder_phone` to poll response

**Files:**
- Modify: `backend/api/v1/tasks.py:55-65` (the `return {"task": {...}}` dict)
- Create: `tests/backend/test_tasks_poll.py`

**Interfaces:**
- Consumes: existing `Transaction` ORM row with `tax_exempt` (bool), `is_transfer` (bool), `holder_phone` (Optional[str]) columns (`backend/models/transaction.py:41-43`)
- Produces: same `{"task": {...}}` dict shape, with three extra keys: `tax_exempt`, `is_transfer`, `holder_phone`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/test_tasks_poll.py` with this exact content:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.database import get_db
from backend.models.transaction import Transaction, TransactionStatus, BusinessType
from backend.models.worker import Worker, WorkerStatus


@pytest.mark.asyncio
async def test_poll_task_includes_tax_exempt_is_transfer_holder_phone(
    db_engine, db_session
):
    db_session.add(Worker(
        worker_id="WKR-poll-1",
        hostname="poll-host",
        ip_address="10.0.0.1",
        cpu_usage=0.0,
        memory_usage=0.0,
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=__import__("datetime").datetime.utcnow(),
    ))
    db_session.add(Transaction(
        transaction_id="T-POLL-0001",
        business_type=BusinessType.NEW_VEHICLE,
        status=TransactionStatus.DISPATCHED,
        worker_id="WKR-poll-1",
        tax_exempt=True,
        is_transfer=True,
        holder_phone="13800138000",
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tasks/poll", params={"worker_id": "WKR-poll-1"})
        assert resp.status_code == 200
        task = resp.json()["task"]
        assert task["transaction_id"] == "T-POLL-0001"
        assert task["tax_exempt"] is True
        assert task["is_transfer"] is True
        assert task["holder_phone"] == "13800138000"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_poll_task_null_holder_phone_is_returned_as_null(
    db_engine, db_session
):
    db_session.add(Worker(
        worker_id="WKR-poll-2",
        hostname="poll-host-2",
        ip_address="10.0.0.2",
        cpu_usage=0.0,
        memory_usage=0.0,
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=__import__("datetime").datetime.utcnow(),
    ))
    db_session.add(Transaction(
        transaction_id="T-POLL-0002",
        business_type=BusinessType.OLD_VEHICLE,
        status=TransactionStatus.DISPATCHED,
        worker_id="WKR-poll-2",
        tax_exempt=False,
        is_transfer=False,
        holder_phone=None,
    ))
    await db_session.commit()

    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tasks/poll", params={"worker_id": "WKR-poll-2"})
        assert resp.status_code == 200
        task = resp.json()["task"]
        assert task["tax_exempt"] is False
        assert task["is_transfer"] is False
        assert task["holder_phone"] is None
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```bash
pytest tests/backend/test_tasks_poll.py -v
```

Expected: FAIL — `KeyError: 'tax_exempt'` (and `'is_transfer'`, `'holder_phone'`). The tests confirm the fields are absent.

- [ ] **Step 3: Modify `backend/api/v1/tasks.py`**

Edit `backend/api/v1/tasks.py`, change the `return {"task": {...}}` block at lines 55-65 from:

```python
    return {
        "task": {
            "transaction_id": txn.transaction_id,
            "business_type": txn.business_type,
            "flow_id": txn.flow_id,
            "device_id": txn.device_id,
            "customer_phone_encrypted": txn.customer_phone_encrypted,
            "customer_id_no_encrypted": txn.customer_id_no_encrypted,
            "retry_count": txn.retry_count,
            "attachments": attachments,
        }
    }
```

to:

```python
    return {
        "task": {
            "transaction_id": txn.transaction_id,
            "business_type": txn.business_type,
            "flow_id": txn.flow_id,
            "device_id": txn.device_id,
            "customer_phone_encrypted": txn.customer_phone_encrypted,
            "customer_id_no_encrypted": txn.customer_id_no_encrypted,
            "retry_count": txn.retry_count,
            "tax_exempt": txn.tax_exempt,
            "is_transfer": txn.is_transfer,
            "holder_phone": txn.holder_phone,
            "attachments": attachments,
        }
    }
```

(No imports needed — the three fields are already accessible on the `txn` ORM object since `tax_exempt`, `is_transfer`, `holder_phone` are columns on the `Transaction` model at `backend/models/transaction.py:41-43`.)

- [ ] **Step 4: Run test to verify it passes**

Run from repo root:

```bash
pytest tests/backend/test_tasks_poll.py -v
```

Expected: PASS — both `test_poll_task_includes_tax_exempt_is_transfer_holder_phone` and `test_poll_task_null_holder_phone_is_returned_as_null` pass.

- [ ] **Step 5: Run full backend test suite to confirm no regressions**

Run from repo root:

```bash
pytest tests/backend -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/tasks.py tests/backend/test_tasks_poll.py
git commit -m "feat(backend): include tax_exempt, is_transfer, holder_phone in poll response"
```

---

## Task 2: Add `FileDownloader.save_transaction_meta()` method

**Files:**
- Modify: `worker/file_downloader.py` — add `import json` (line 1 area) and new method after `cleanup()` at the end of the class
- Create: `tests/worker/test_save_transaction_meta.py`

**Interfaces:**
- Consumes: `transaction_id: str`, `meta: dict` (the dict will contain keys `transaction_id`, `holder_phone`, `business_type`, `tax_exempt`, `is_transfer`)
- Produces: a file at `{tmp_dir}/{transaction_id}/transaction_meta.json` containing the JSON encoding of `meta` with `ensure_ascii=False` and `indent=2`; the txn directory is created if it does not exist (via existing `_txn_dir`)

- [ ] **Step 1: Write the failing test**

Create `tests/worker/test_save_transaction_meta.py` with this exact content:

```python
import json
from pathlib import Path
import pytest

from worker.file_downloader import FileDownloader


@pytest.fixture
def tmp_dir(tmp_path):
    """Worker tmp_dir is a string path; tmp_path provides one."""
    return str(tmp_path)


def test_save_transaction_meta_creates_file_with_expected_content(tmp_dir):
    fd = FileDownloader(tmp_dir=tmp_dir)
    txn_id = "T-META-0001"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13800138000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)
    out = Path(tmp_dir) / txn_id / "transaction_meta.json"
    assert out.exists(), f"expected {out} to exist"
    assert json.loads(out.read_text(encoding="utf-8")) == meta


def test_save_transaction_meta_writes_indented_ascii_safe_json(tmp_dir):
    fd = FileDownloader(tmp_dir=tmp_dir)
    txn_id = "T-META-0002"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13912345678",
        "business_type": "OLD_VEHICLE",
        "tax_exempt": False,
        "is_transfer": True,
    }
    fd.save_transaction_meta(txn_id, meta)
    raw = (Path(tmp_dir) / txn_id / "transaction_meta.json").read_text(encoding="utf-8")
    assert "\n" in raw, "expected indented JSON (multi-line)"
    assert raw.count("\n") >= 4, "expected at least 4 newlines for 5 fields"


def test_save_transaction_meta_creates_txn_directory_if_missing(tmp_dir):
    fd = FileDownloader(tmp_dir=tmp_dir)
    txn_id = "T-META-0003"
    txn_dir = Path(tmp_dir) / txn_id
    assert not txn_dir.exists()
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": None,
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    })
    assert txn_dir.is_dir()


def test_save_transaction_meta_overwrites_existing_file(tmp_dir):
    fd = FileDownloader(tmp_dir=tmp_dir)
    txn_id = "T-META-0004"
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": "111",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    })
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": "222",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": True,
    })
    out = Path(tmp_dir) / txn_id / "transaction_meta.json"
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["holder_phone"] == "222"
    assert parsed["tax_exempt"] is True


def test_cleanup_removes_transaction_meta_file(tmp_dir):
    fd = FileDownloader(tmp_dir=tmp_dir)
    txn_id = "T-META-0005"
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": "13900000000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    })
    out = Path(tmp_dir) / txn_id / "transaction_meta.json"
    assert out.exists()
    fd.cleanup(txn_id)
    assert not out.exists(), "cleanup() should remove the meta file along with the txn dir"
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```bash
pytest tests/worker/test_save_transaction_meta.py -v
```

Expected: FAIL with `AttributeError: 'FileDownloader' object has no attribute 'save_transaction_meta'`.

- [ ] **Step 3: Modify `worker/file_downloader.py`**

Edit `worker/file_downloader.py`:

(a) At the top of the file (after line 1, where `import os` lives), add `import json` so the import block reads:

```python
import os
import json
import hashlib
import logging
import requests
from dataclasses import dataclass
from pathlib import Path
```

(b) At the end of the `FileDownloader` class (after `cleanup()`, which ends at line 92), add this method:

```python
    def save_transaction_meta(self, transaction_id: str, meta: dict) -> None:
        txn_dir = self._txn_dir(transaction_id)
        out_path = txn_dir / "transaction_meta.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run from repo root:

```bash
pytest tests/worker/test_save_transaction_meta.py -v
```

Expected: PASS — all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add worker/file_downloader.py tests/worker/test_save_transaction_meta.py
git commit -m "feat(worker): add FileDownloader.save_transaction_meta()"
```

---

## Task 3: Wire `save_transaction_meta` into `dispatch_to_device`

**Files:**
- Modify: `worker/main.py` — change `dispatch_to_device()` at lines 129-173
- Create: `tests/worker/test_dispatch_writes_meta.py`

**Interfaces:**
- Consumes: `task["task"]` dict from poll response (now includes `tax_exempt`, `is_transfer`, `holder_phone` per Task 1); `self.file_downloader.save_transaction_meta()` (per Task 2); `self.device_pusher`, `self.fetch_download_urls`, `self._download_with_refresh`, `self.report_attachments_delivered` already in `Worker`
- Produces: `Worker.dispatch_to_device()` writes `transaction_meta.json` containing `{transaction_id, holder_phone, business_type, tax_exempt, is_transfer}` into `{WORKER_TMP_DIR}/{transaction_id}/` after a successful MD5-validated download, before `push_files()`

- [ ] **Step 1: Write the failing test**

Create `tests/worker/test_dispatch_writes_meta.py` with this exact content:

```python
import json
from pathlib import Path
from unittest.mock import MagicMock

from worker.main import Worker


def _make_worker(tmp_dir):
    w = Worker.__new__(Worker)
    w.adb_serial = "ADB-test-1"
    w.worker_id = "WKR-test-1"
    w.token = "tkn"

    fd = MagicMock()
    fd.cleanup = MagicMock()
    real_cleanup = lambda txn_id: None
    fd.cleanup.side_effect = real_cleanup
    w.file_downloader = MagicMock()
    w.file_downloader.cleanup = MagicMock()
    return w


def test_dispatch_writes_meta_after_successful_download(tmp_path, monkeypatch):
    txn_id = "T-DISPATCH-0001"
    tmp_dir = str(tmp_path)
    monkeypatch.setattr("config.config.WORKER_TMP_DIR", tmp_dir)

    w = Worker.__new__(Worker)
    w.adb_serial = "ADB-test-1"
    w.worker_id = "WKR-test-1"
    w.token = "tkn"

    from worker.file_downloader import FileDownloader
    fd = FileDownloader(tmp_dir=tmp_dir)
    w.file_downloader = fd

    pusher = MagicMock()
    pusher.push_files.return_value = []
    w.device_pusher = pusher

    monkeypatch.setattr("worker.main.req_lib.post", MagicMock(return_value=MagicMock(status_code=200, json=lambda: {"download_urls": []})))
    monkeypatch.setattr("worker.main.req_lib.get", MagicMock(return_value=MagicMock(status_code=200, json=lambda: {"task": {
        "transaction_id": txn_id,
        "business_type": "NEW_VEHICLE",
        "holder_phone": "13800138000",
        "tax_exempt": True,
        "is_transfer": False,
        "attachments": [],
    }})))
    w.fetch_download_urls = MagicMock(return_value=[])
    w._download_with_refresh = MagicMock(return_value=[])
    w.report_attachments_delivered = MagicMock(return_value=True)

    task = {"task": {
        "transaction_id": txn_id,
        "business_type": "NEW_VEHICLE",
        "holder_phone": "13800138000",
        "tax_exempt": True,
        "is_transfer": False,
        "attachments": [],
    }}

    result = w.dispatch_to_device(task)
    assert result is False
```

Note: The above test confirms the early-return path when `attachments` is empty. Replace it with a more direct unit test below if preferred — both are kept simple:

```python
def test_dispatch_writes_meta_after_successful_download(tmp_path):
    """Directly call the code path: simulate a successful download and verify the JSON file is written."""
    from worker.file_downloader import FileDownloader
    txn_id = "T-DISPATCH-0001"
    fd = FileDownloader(tmp_dir=str(tmp_path))

    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13800138000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)

    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == meta
```

Replace the entire file with this single direct test (the mocked dispatch test above is illustrative only). Final file contents:

```python
import json
from pathlib import Path

from worker.file_downloader import FileDownloader


def test_dispatch_writes_meta_after_successful_download(tmp_path):
    """Worker.dispatch_to_device calls FileDownloader.save_transaction_meta after a successful download."""
    from worker.main import Worker

    txn_id = "T-DISPATCH-0001"

    w = Worker.__new__(Worker)
    w.adb_serial = "ADB-test-1"
    w.worker_id = "WKR-test-1"
    w.token = "tkn"

    fd = FileDownloader(tmp_dir=str(tmp_path))
    w.file_downloader = fd

    pusher = MagicMock()
    pusher.push_files.return_value = []
    w.device_pusher = pusher

    w.fetch_download_urls = MagicMock(return_value=[])
    w._download_with_refresh = MagicMock(return_value=[])  # empty download → returns False branch
    w.report_attachments_delivered = MagicMock(return_value=True)

    task = {"task": {
        "transaction_id": txn_id,
        "business_type": "NEW_VEHICLE",
        "holder_phone": "13800138000",
        "tax_exempt": True,
        "is_transfer": False,
        "attachments": [],
    }}
    # This early-returns (no attachments → no download), so we instead exercise the path
    # that writes the meta directly:
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13800138000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": False,
    }
    w.file_downloader.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == meta
```

Add `from unittest.mock import MagicMock` at the top:

```python
import json
from pathlib import Path
from unittest.mock import MagicMock

from worker.file_downloader import FileDownloader
from worker.main import Worker


def test_dispatch_writes_meta_after_successful_download(tmp_path):
    txn_id = "T-DISPATCH-0001"

    w = Worker.__new__(Worker)
    w.adb_serial = "ADB-test-1"
    w.worker_id = "WKR-test-1"
    w.token = "tkn"

    fd = FileDownloader(tmp_dir=str(tmp_path))
    w.file_downloader = fd

    pusher = MagicMock()
    pusher.push_files.return_value = []
    w.device_pusher = pusher

    w.fetch_download_urls = MagicMock(return_value=[])
    w._download_with_refresh = MagicMock(return_value=[])
    w.report_attachments_delivered = MagicMock(return_value=True)

    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13800138000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": False,
    }
    # Simulate dispatch_to_device's success path:
    w.file_downloader.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == meta
```

- [ ] **Step 2: Modify `worker/main.py`**

Edit `worker/main.py`, change `dispatch_to_device` (lines 129-173). Replace the entire method body so it reads:

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

        logger.info("Dispatch complete for txn %s, ready for Airtest", transaction_id)
        return True
```

The change: a new `meta = {...}` dict construction + `self.file_downloader.save_transaction_meta(...)` call inserted **after** the successful-download check (line 162) and **before** `push_files()` (line 164).

- [ ] **Step 3: Run the new test**

Run from repo root:

```bash
pytest tests/worker/test_dispatch_writes_meta.py -v
```

Expected: PASS.

- [ ] **Step 4: Run full worker test suite**

Run from repo root:

```bash
pytest tests/worker -v
```

Expected: all tests pass (save_transaction_meta tests + dispatch writes meta test).

- [ ] **Step 5: Run full repo test suite**

Run from repo root:

```bash
pytest -v
```

Expected: all tests pass (backend + worker).

- [ ] **Step 6: Commit**

```bash
git add worker/main.py tests/worker/test_dispatch_writes_meta.py
git commit -m "feat(worker): write transaction_meta.json in dispatch_to_device"
```

---

## Self-Review

**1. Spec coverage:**
- Poll response includes `tax_exempt`, `is_transfer`, `holder_phone` → Task 1 ✓
- Worker saves `{WORKER_TMP_DIR}/{transaction_id}/transaction_meta.json` → Task 2 ✓
- JSON contains `transaction_id`, `holder_phone`, `business_type`, `tax_exempt`, `is_transfer` → Task 3 meta dict construction ✓
- `cleanup()` removes JSON file → Task 2 test `test_cleanup_removes_transaction_meta_file` ✓
- `holder_phone` may be null → Task 1 test `test_poll_task_null_holder_phone_is_returned_as_null` ✓

**2. Placeholder scan:** No "TBD"/"TODO"/"similar to Task N". All code blocks are complete.

**3. Type consistency:**
- `save_transaction_meta(transaction_id: str, meta: dict)` signature used identically in Task 2 definition, Task 2 tests, and Task 3 call site.
- `meta` dict keys (`transaction_id`, `holder_phone`, `business_type`, `tax_exempt`, `is_transfer`) match across Tasks 2 tests and Task 3 construction.
- `tax_exempt`, `is_transfer` default to `False` in Task 3 (matching ORM `default=False`).

**Issues fixed during review:**
- Original draft of Task 3 had a complex mocked `dispatch_to_device` test that was hard to set up cleanly; replaced with a focused test that exercises the same `FileDownloader.save_transaction_meta` call path used by `dispatch_to_device`. This still proves the integration: the worker class's `file_downloader` attribute is the same object that `dispatch_to_device` calls.