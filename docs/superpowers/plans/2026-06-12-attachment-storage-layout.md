# Attachment Storage Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change attachment on-disk layout to `{YYYY-MM-DD}/{transaction_id}/{transaction_id}_{NNN}{ext}`, partitioned by server UTC date and grouped by transaction.

**Architecture:** Single-file edit in `backend/services/transaction_service.py`. `LocalStorageBackend.put()` already auto-creates parent directories, so we only change the storage key built in the service layer. Tests are added under `tests/backend/` using the existing `db_session` fixture and a temporary `STORAGE_LOCAL_PATH`.

**Tech Stack:** FastAPI, SQLAlchemy (async, SQLite for tests), pytest + pytest-asyncio, `pathlib`, `datetime`.

**Spec:** `docs/superpowers/specs/2026-06-12-attachment-storage-layout-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `tests/backend/test_attachment_storage_layout.py` | Create | Unit tests for new key format + on-disk layout via `TransactionService.create_transaction`. |
| `backend/services/transaction_service.py` | Modify | Build new storage key; preserve all other behavior. |

---

## Task 1: Add failing test for new storage key format

**Files:**
- Create: `tests/backend/test_attachment_storage_layout.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_attachment_storage_layout.py
import datetime
import tempfile
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_storage_key_uses_date_and_transaction_id(db_session, monkeypatch):
    """New layout: {YYYY-MM-DD}/{transaction_id}/{transaction_id}_{NNN}{ext}"""
    tmpdir = tempfile.mkdtemp(prefix="att-layout-test-")
    monkeypatch.setenv("STORAGE_LOCAL_PATH", tmpdir)

    # get_settings() is lru_cached; clear so the new env var takes effect.
    from backend.config import get_settings
    get_settings.cache_clear()

    from backend.services.transaction_service import TransactionService
    from backend.schemas.transaction import TransactionCreateRequest

    service = TransactionService(db_session)
    # Override storage base_path directly in case the backend was constructed
    # before the env var was patched.
    service.storage.base_path = tmpdir
    Path(tmpdir).mkdir(parents=True, exist_ok=True)

    request = TransactionCreateRequest(
        external_id="EXT-1",
        business_type="NEW",
        customer_phone="13800000000",
        customer_id_no="11010119900101001X",
        attachments_meta=[
            {"file_type": "ID_CARD_FRONT", "file_format": "JPG",
             "filename": "front.jpg", "description": None},
            {"file_type": "ID_CARD_BACK", "file_format": "PNG",
             "filename": "back.PNG", "description": None},
            {"file_type": "VEHICLE_CERT", "file_format": "PDF",
             "filename": "cert.pdf", "description": None},
        ],
    )
    files = [
        ({"filename": "front.jpg", "content_type": "image/jpeg",
          "file_type": "ID_CARD_FRONT", "file_format": "JPG",
          "description": None}, b"FRONTDATA"),
        ({"filename": "back.PNG", "content_type": "image/png",
          "file_type": "ID_CARD_BACK", "file_format": "PNG",
          "description": None}, b"BACKDATA"),
        ({"filename": "cert.pdf", "content_type": "application/pdf",
          "file_type": "VEHICLE_CERT", "file_format": "PDF",
          "description": None}, b"CERTDATA"),
    ]

    result = await service.create_transaction(request, files)

    txn_id = result["transaction_id"]
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    expected_keys = [
        f"{today}/{txn_id}/{txn_id}_001.jpg",
        f"{today}/{txn_id}/{txn_id}_002.png",
        f"{today}/{txn_id}/{txn_id}_003.pdf",
    ]
    actual_keys = [a["storage_path"] for a in result["attachments"]]
    assert actual_keys == expected_keys

    for key, (_meta, data) in zip(expected_keys, files):
        on_disk = Path(tmpdir) / key
        assert on_disk.exists(), f"missing: {on_disk}"
        assert on_disk.read_bytes() == data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/backend/test_attachment_storage_layout.py::test_storage_key_uses_date_and_transaction_id -v
```

Expected: FAIL — assertion shows old keys `default/ATT-.../ATT-..._front.jpg` instead of `YYYY-MM-DD/TXN-.../TXN-..._001.jpg`.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/backend/test_attachment_storage_layout.py
git commit -m "test: failing test for new attachment storage layout"
```

---

## Task 2: Add failing test for extension-less filenames

**Files:**
- Modify: `tests/backend/test_attachment_storage_layout.py` (append new test)

- [ ] **Step 1: Append failing test**

```python
# Append to tests/backend/test_attachment_storage_layout.py

@pytest.mark.asyncio
async def test_storage_key_handles_missing_extension(db_session, monkeypatch):
    """Files with no extension are stored as {txn}_{NNN} (no suffix)."""
    tmpdir = tempfile.mkdtemp(prefix="att-layout-noext-")
    monkeypatch.setenv("STORAGE_LOCAL_PATH", tmpdir)

    from backend.config import get_settings
    get_settings.cache_clear()

    from backend.services.transaction_service import TransactionService
    from backend.schemas.transaction import TransactionCreateRequest

    service = TransactionService(db_session)
    service.storage.base_path = tmpdir
    Path(tmpdir).mkdir(parents=True, exist_ok=True)

    request = TransactionCreateRequest(
        external_id="EXT-2",
        business_type="NEW",
        customer_phone="13800000000",
        customer_id_no="11010119900101001X",
        attachments_meta=[
            {"file_type": "OTHER", "file_format": "JPG",
             "filename": "noext", "description": None},
        ],
    )
    files = [
        ({"filename": "noext", "content_type": "application/octet-stream",
          "file_type": "OTHER", "file_format": "JPG",
          "description": None}, b"BLOB"),
    ]

    result = await service.create_transaction(request, files)

    txn_id = result["transaction_id"]
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    expected = f"{today}/{txn_id}/{txn_id}_001"
    assert result["attachments"][0]["storage_path"] == expected
    assert (Path(tmpdir) / expected).read_bytes() == b"BLOB"
```

- [ ] **Step 2: Run the new test to verify it fails**

```bash
pytest tests/backend/test_attachment_storage_layout.py::test_storage_key_handles_missing_extension -v
```

Expected: FAIL — current service produces `default/ATT-.../ATT-..._noext`.

- [ ] **Step 3: Commit**

```bash
git add tests/backend/test_attachment_storage_layout.py
git commit -m "test: failing test for extension-less attachment filenames"
```

---

## Task 3: Implement new storage key construction

**Files:**
- Modify: `backend/services/transaction_service.py`

- [ ] **Step 1: Add `pathlib.Path` import**

Edit the top of `backend/services/transaction_service.py`. Replace:

```python
import uuid
import hashlib
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.transaction import Transaction, TransactionStatus
from backend.models.attachment import Attachment
from backend.schemas.transaction import TransactionCreateRequest
from backend.storage.local import LocalStorageBackend
```

with:

```python
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.transaction import Transaction, TransactionStatus
from backend.models.attachment import Attachment
from backend.schemas.transaction import TransactionCreateRequest
from backend.storage.local import LocalStorageBackend
```

- [ ] **Step 2: Replace the per-file loop body**

Inside `create_transaction`, replace:

```python
        attachments = []
        for idx, (file_meta, file_data) in enumerate(files):
            attachment_id = self._generate_id("ATT")
            file_md5 = hashlib.md5(file_data).hexdigest()
            file_sha256 = hashlib.sha256(file_data).hexdigest()
            filename = f"{attachment_id}_{file_meta['filename']}"
            storage_key = f"{customer_id}/{attachment_id}/{filename}"

            await self.storage.put(storage_key, file_data, file_meta["content_type"])
```

with:

```python
        attachments = []
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        for idx, (file_meta, file_data) in enumerate(files):
            attachment_id = self._generate_id("ATT")
            file_md5 = hashlib.md5(file_data).hexdigest()
            file_sha256 = hashlib.sha256(file_data).hexdigest()
            ext = Path(file_meta["filename"]).suffix.lower()
            filename = f"{transaction_id}_{idx + 1:03d}{ext}"
            storage_key = f"{date_str}/{transaction_id}/{filename}"

            await self.storage.put(storage_key, file_data, file_meta["content_type"])
```

Everything else in the file stays exactly the same — the `Attachment(...)` construction (which still records `storage_path=storage_key`), `self.db.add(...)`, `self.db.commit()`, and the return dict are unchanged.

- [ ] **Step 3: Run the new tests**

```bash
pytest tests/backend/test_attachment_storage_layout.py -v
```

Expected: both tests PASS.

- [ ] **Step 4: Run the full backend test suite**

```bash
pytest tests/backend -v
```

Expected: all tests PASS (existing tests do not assert on `storage_path`).

- [ ] **Step 5: Commit**

```bash
git add backend/services/transaction_service.py
git commit -m "feat(storage): partition attachments by date/transaction with deterministic filenames"
```

---

## Task 4: Manual smoke test against running backend

**Files:** none (manual verification)

- [ ] **Step 1: Ensure backend is running in debug mode**

If not already running:

```bash
nohup .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug \
  > /tmp/opencode/logs/backend.log 2>&1 &
sleep 2
curl -s http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

- [ ] **Step 2: Submit a transaction with 3 files**

```bash
TODAY=$(date -u +%Y-%m-%d)
echo "FRONT" > /tmp/front.jpg
echo "BACK"  > /tmp/back.png
echo "CERT"  > /tmp/cert.pdf

curl -s -X POST http://localhost:8000/api/v1/transactions \
  -F 'transaction={"external_id":"smoke-1","business_type":"NEW","customer_phone":"13800000000","customer_id_no":"11010119900101001X","attachments_meta":[{"file_type":"ID_CARD_FRONT","file_format":"JPG","filename":"front.jpg"},{"file_type":"ID_CARD_BACK","file_format":"PNG","filename":"back.png"},{"file_type":"VEHICLE_CERT","file_format":"PDF","filename":"cert.pdf"}]}' \
  -F 'files=@/tmp/front.jpg' \
  -F 'files=@/tmp/back.png' \
  -F 'files=@/tmp/cert.pdf' | tee /tmp/smoke-resp.json
```

Expected: JSON response with `transaction_id` like `TXN-...` and 3 `attachments` whose `storage_path` start with `${TODAY}/TXN-`.

- [ ] **Step 3: Verify on-disk layout**

```bash
TXN=$(python3 -c "import json,sys;print(json.load(open('/tmp/smoke-resp.json'))['transaction_id'])")
ls -la /data/attachments/$(date -u +%Y-%m-%d)/$TXN/
```

Expected output (filenames):

```
TXN-..._001.jpg
TXN-..._002.png
TXN-..._003.pdf
```

- [ ] **Step 4: Verify file contents survived**

```bash
cat /data/attachments/$(date -u +%Y-%m-%d)/$TXN/${TXN}_001.jpg
```

Expected: `FRONT`

- [ ] **Step 5: Done — no commit needed (manual verification only)**

---

## Self-Review Notes

- **Spec coverage:** Tasks 1-2 cover both happy path (with extension) and edge case (no extension) from the spec's Risks table. Task 3 implements the spec's exact diff. Task 4 covers the spec's Verification section.
- **No placeholders.**
- **Type consistency:** `storage_key` / `filename` / `date_str` / `ext` names consistent across all tasks.
- **No-Goals respected:** No migration, no DB schema change, no download endpoint change.
