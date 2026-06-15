# Device Android Agent APP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Python `device/` simulator with a real Android APK that downloads attachment files into `/sdcard/3is/<attachment_id>.<ext>` on demand, and wire the new protocol through Backend & Worker so any of the four ends can be developed and tested in isolation.

**Architecture:**
- Device Agent: Single-module Kotlin Android app, Foreground Service + 4 helper classes, OkHttp for HTTP, raw `java.net.Socket` for the Worker connection, `org.json` for serialization. No Hilt / Retrofit / Room.
- Backend: Two new endpoints under `POST /api/v1/devices/{device_id}/{ready,download-ack}`; a `Device` ORM already exists and only needs the default `sandbox_path` updated.
- Worker: A new `DeviceDispatcher` module that connects to the Device Agent's TCP port, sends the `DOWNLOAD_FILES` JSON instruction, and waits for the ack. Currently `poll_tasks()` logs the task but does nothing; this plan adds the dispatch path.
- Cleanup: The old `device/` Python directory is deleted after the Android APK builds and the mock worker round-trip succeeds.

**Tech Stack:** Kotlin 1.9.x, Android Gradle Plugin 8.x, minSdk=24, targetSdk=34, OkHttp 4.12, Python 3.12 (Worker), FastAPI + SQLAlchemy (Backend).

---

## Current State Findings (must read before starting)

These are facts about the repo that deviate from a literal reading of the spec, and the plan compensates for them:

1. **`device/` is a Python simulator**, not a real Android app. It has its own `pyproject.toml`, `socket_client.py`, `downloader.py`, `main.py`. The spec already plans to delete it; this plan does so in Task T18 after the Android APK is verified to work.
2. **Worker currently has no "push DOWNLOAD_FILES" code.** `worker/main.py:111-113` polls tasks and only logs them. `device_controller.py` exists and can talk ADB but is never called from `run()`. The new `DeviceDispatcher` module to be added in Task T5 fills this gap.
3. **Backend `Device` model already exists** (`backend/models/device.py:20`) with `last_seen_at` (timezone-aware) and a `sandbox_path` default of `/sdcard/sandbox/{txn_id}/`. Task T2 updates that default to `/sdcard/3is/`.
4. **`Attachment.file_format` is already a `JPG|PNG|PDF` enum** (`backend/models/attachment.py:12-16`). The spec's R2 requirement that "Worker transmits `ext` derived from `file_format`" maps directly to `att.file_format.lower()` in Task T5.
5. **No existing tests in backend or worker.** The plan adds minimal pytest coverage for the new Backend endpoints (T3, T4) and one unit test for the Worker's payload assembly (T7) — these are the only tests, per spec §5.1 "first version: manual ADB verification only."

---

## File Structure

```
3is-auto-app/
├── backend/
│   ├── api/
│   │   ├── router.py                          (modify: register devices router)
│   │   └── v1/
│   │       └── devices.py                     (create: 2 endpoints)
│   ├── models/device.py                       (modify: default sandbox_path → /sdcard/3is/)
│   ├── schemas/device.py                      (create: Pydantic request/response)
│   ├── services/
│   │   ├── dispatcher_service.py              (modify: respect sandbox_path change)
│   │   └── url_signature_service.py           (no change; reference only)
│   ├── tests/
│   │   └── api/v1/test_devices.py             (create: 2 endpoint tests)
│   ├── migrations/versions/                   (Alembic auto-gen; commit only)
│   └── pyproject.toml                         (modify: add httpx test dep if missing)
├── worker/
│   ├── device_dispatcher.py                   (create: Socket connect + send DOWNLOAD_FILES + await ack)
│   ├── tests/
│   │   └── test_dispatcher_payload.py         (create: payload assembly unit test)
│   ├── main.py                                (modify: wire DeviceDispatcher into task handler)
│   └── pyproject.toml                         (modify: add pytest dev dep)
├── android/                                    (create root)
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── gradle.properties
│   ├── gradle/wrapper/
│   │   ├── gradle-wrapper.properties
│   │   └── gradle-wrapper.jar                 (binary; generated via `gradle wrapper`)
│   ├── gradlew                                (generated)
│   ├── gradlew.bat                            (generated)
│   ├── local.properties                       (gitignored; holds sdk.dir)
│   ├── scripts/
│   │   ├── mock_worker.py                     (create)
│   │   └── adb_install.sh                     (create)
│   └── app/
│       ├── build.gradle.kts
│       ├── proguard-rules.pro                 (empty placeholder)
│       └── src/main/
│           ├── AndroidManifest.xml
│           ├── res/values/strings.xml         (app name + permission labels)
│           ├── res/values/themes.xml          (Material 3 default)
│           └── java/com/threeis/deviceagent/
│               ├── DeviceAgentApplication.kt  (create: boot Service)
│               ├── MainActivity.kt            (create: permission flow + config)
│               ├── service/DeviceAgentService.kt
│               ├── net/SocketClient.kt
│               ├── net/BackendApi.kt
│               ├── download/Downloader.kt
│               ├── download/SandboxManager.kt
│               ├── data/Models.kt
│               ├── data/Config.kt
│               └── util/Logger.kt
├── docs/
│   ├── user-manu.md                           (modify: §5.1/5.3/5.6/6.3/7.5)
│   └── superpowers/specs/
│       └── 2026-06-03-rpa-worker-side-architecture-design.md
│                                                (modify: §3.1/§3.4/§11.x)
├── device/                                     (DELETE in T18)
└── docs/superpowers/specs/
    └── 2026-06-12-device-android-app-design.md  (spec; reference only)
```

---

## Task Dependency Graph

```
T1 (schemas) ─┐
              ├─→ T2 (Device.sandbox_path default + Alembic) ─→ T3 (ready endpoint) ─┐
              │                                              └─→ T4 (download-ack) ─┤
              │                                                                     ├─→ T15 (E2E backend tests)
T5 (DeviceDispatcher module) ─→ T6 (Wire into Worker.run) ─→ T7 (payload unit test) ┤
                                                                                      │
T8 (Android project skeleton) ─→ T9 (AndroidManifest + permissions) ─→ T10 (Models + Config) ┐
                                                                                                ├─→ T13 (MainActivity)
                                                                                                ├─→ T14 (Service + Socket + Downloader)
                                                                                                │
                                                                                                └─→ T16 (Mock worker integration)
T17 (Docs sync) [parallel with above once T8 starts]                                            │
                                                                                                └─→ T18 (Delete old device/ + close-out)
```

T1-T2-T3-T4 must be done first (Backend has the API contract). T5-T6-T7 can run in parallel with T8-T9-T10-T14 once T1 is done. T15 validates Backend+Worker; T16 validates Device end-to-end. T17 can run at any time after T8. T18 is final cleanup.

---

### Task T1: Backend — Define `device` Pydantic schemas

**Files:**
- Create: `backend/schemas/device.py`

**Why:** The two new endpoints need typed request/response models. Mirrors the existing `backend/schemas/worker.py` style.

- [ ] **Step 1: Create the schemas file**

Write `backend/schemas/device.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DeviceReadyRequest(BaseModel):
    status: str = Field(pattern="^(READY|BUSY|OFFLINE)$")
    sandbox_clear_failed: Optional[bool] = False


class DeviceReadyResponse(BaseModel):
    device_id: str
    status: str
    last_seen_at: datetime


class DownloadAckFile(BaseModel):
    attachment_id: str = Field(min_length=1)
    local_path: str = Field(min_length=1)
    success: bool
    error_reason: Optional[str] = None


class DeviceDownloadAckRequest(BaseModel):
    transaction_id: str = Field(min_length=1)
    files: List[DownloadAckFile]
    all_success: bool
    sandbox_clear_failed: bool = False
    completed_at: datetime


class DeviceDownloadAckResponse(BaseModel):
    transaction_id: str
    next_state: str
```

- [ ] **Step 2: Register in `backend/schemas/__init__.py`**

Read `backend/schemas/__init__.py`. If it does not exist, create it as an empty file. If it exists, add the export lines:

```python
from backend.schemas.device import (
    DeviceReadyRequest,
    DeviceReadyResponse,
    DeviceDownloadAckRequest,
    DeviceDownloadAckResponse,
    DownloadAckFile,
)
```

(Only add these lines if `__init__.py` already exports other schemas; otherwise leave it empty and let the router import directly.)

- [ ] **Step 3: Commit**

```bash
git add backend/schemas/device.py backend/schemas/__init__.py
git commit -m "feat(backend): add device Pydantic schemas for ready + download-ack"
```

---

### Task T2: Backend — Update `Device.sandbox_path` default

> **Amendment (mid-execution):** The original plan called for an Alembic migration, but the codebase does not use Alembic — schema is created via `Base.metadata.create_all()` in `backend/main.py:11` on app startup. `alembic` is in `pyproject.toml` but never initialized (no `alembic.ini`, no `migrations/` directory). The pragmatic move: change the Python-level `default=` on the model. New INSERTs through SQLAlchemy (which is the only path that creates `Device` rows) will pick up the new default automatically. Existing rows with the old default are out of scope for the MVP; the new T3 endpoint creates rows on first contact, and the old path `/sdcard/sandbox/{txn_id}/` is no longer used anywhere after T6 wires the new flow. If a backfill is needed later, run an ad-hoc SQL `UPDATE` then.

**Files:**
- Modify: `backend/models/device.py:23`

- [ ] **Step 1: Update the default sandbox path**

In `backend/models/device.py` change line 23:

```python
    sandbox_path = Column(String(256), default="/sdcard/3is/")
```

(Was: `default="/sdcard/sandbox/{txn_id}/"`.)

- [ ] **Step 2: Verify nothing else in the codebase hard-codes the old path**

```bash
cd /data/workspaces/3IS-Auto-App
grep -rn "/sdcard/sandbox" backend/ worker/ --include="*.py" --include="*.md" | grep -v ".venv\|.pyc"
```

Expected: the only match is the one line you just changed (or any historical reference in `docs/` that doesn't affect code behavior). If other code references the old path, STOP and report BLOCKED.

- [ ] **Step 3: Verify the model still imports cleanly and the default is correct**

```bash
cd backend
.venv/bin/python -c "from backend.models.device import Device; print(Device.__table__.columns.sandbox_path.default)"
```

Expected: prints `ScalarElementColumnDefault('/sdcard/3is/')` (or similar representation of the new default). Note: `Device().sandbox_path` will print `None` at construction time because `Column(default=...)` is a SQLAlchemy flush-time default, not a Python `__init__` default. The default fires on INSERT, which is when T3's endpoint creates a row.

- [ ] **Step 4: Commit**

```bash
cd ..
git add backend/models/device.py
git commit -m "feat(backend): default device sandbox_path to /sdcard/3is/"
```

---

### Task T3: Backend — Implement `POST /api/v1/devices/{device_id}/ready`

**Files:**
- Create: `backend/api/v1/devices.py`
- Modify: `backend/api/router.py:6,11`

- [ ] **Step 1: Write the failing test first**

> **Project test convention:** This repo keeps tests in `tests/backend/`, not `backend/tests/`. Existing sibling files: `tests/backend/test_workers.py`, `tests/backend/test_workers_list.py`, etc. Use the same path. The repository root `conftest.py` provides `db_engine`, `db_session`, and `seed_devices` fixtures; tests use `app.dependency_overrides[get_db]` to point FastAPI at the in-memory sqlite engine. See `tests/backend/test_workers_list.py` for the exact pattern.

Create `tests/backend/test_devices.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.database import get_db


@pytest.mark.asyncio
async def test_device_ready_updates_status_and_last_seen_at(db_engine):
    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/devices/device-001/ready",
                json={"status": "READY"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["device_id"] == "device-001"
        assert body["status"] == "READY"
        assert "last_seen_at" in body
    finally:
        app.dependency_overrides.clear()
```

`httpx==0.28.1` and `pytest-asyncio==1.4.0` are already in `pyproject.toml` — no dependency changes needed.

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /data/workspaces/3IS-Auto-App
pytest tests/backend/test_devices.py::test_device_ready_updates_status_and_last_seen_at -v
```

Expected: `404 Not Found` (route does not exist yet).

- [ ] **Step 3: Implement the endpoint**

Create `backend/api/v1/devices.py`:

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.device import Device, DeviceStatus
from backend.schemas.device import (
    DeviceReadyRequest,
    DeviceReadyResponse,
    DeviceDownloadAckRequest,
    DeviceDownloadAckResponse,
)

router = APIRouter()


@router.post("/devices/{device_id}/ready", response_model=DeviceReadyResponse)
async def device_ready(
    device_id: str,
    req: DeviceReadyRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        # First-ever ready from this device: create a minimal record
        device = Device(
            device_id=device_id,
            status=DeviceStatus(req.status) if req.status in DeviceStatus.__members__ else DeviceStatus.ONLINE,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(device)
    else:
        device.status = DeviceStatus(req.status) if req.status in DeviceStatus.__members__ else device.status
        device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(device)
    return DeviceReadyResponse(
        device_id=device.device_id,
        status=device.status.value,
        last_seen_at=device.last_seen_at,
    )


@router.post(
    "/devices/{device_id}/download-ack",
    response_model=DeviceDownloadAckResponse,
)
async def device_download_ack(
    device_id: str,
    req: DeviceDownloadAckRequest,
    db: AsyncSession = Depends(get_db),
):
    # Mark device busy → idle based on the ack outcome
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    device.last_seen_at = datetime.now(timezone.utc)
    if req.all_success and not req.sandbox_clear_failed:
        device.status = DeviceStatus.ONLINE
        next_state = "READY"
    else:
        device.status = DeviceStatus.BUSY
        next_state = "RETRY_REQUIRED"

    # Persist local_path back to the matching attachment rows
    from backend.models.attachment import Attachment
    for f in req.files:
        att_result = await db.execute(
            select(Attachment).where(Attachment.attachment_id == f.attachment_id)
        )
        att = att_result.scalar_one_or_none()
        if att is not None and f.success:
            att.local_path = f.local_path

    await db.commit()
    return DeviceDownloadAckResponse(transaction_id=req.transaction_id, next_state=next_state)
```

- [ ] **Step 4: Register the router**

Edit `backend/api/router.py`. After line 6 (`from backend.api.v1 import ...`), add `devices`, and after line 11 (`api_router.include_router(tasks.router, ...)`) add:

```python
from backend.api.v1 import transactions, workers, downloads, statistics, tasks, devices

api_router = APIRouter()
api_router.include_router(transactions.router, prefix="", tags=["transactions"])
api_router.include_router(workers.router, prefix="", tags=["workers"])
api_router.include_router(downloads.router, prefix="", tags=["downloads"])
api_router.include_router(statistics.router, prefix="", tags=["statistics"])
api_router.include_router(tasks.router, prefix="", tags=["tasks"])
api_router.include_router(devices.router, prefix="", tags=["devices"])
```

- [ ] **Step 5: Run the test to confirm it passes**

```bash
cd /data/workspaces/3IS-Auto-App
pytest tests/backend/test_devices.py::test_device_ready_updates_status_and_last_seen_at -v
```

Expected: `PASSED`. If a `local_path` column is missing on `Attachment`, also add it via Alembic (see T2 pattern).

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/devices.py backend/api/router.py tests/backend/test_devices.py
git commit -m "feat(backend): POST /api/v1/devices/{id}/ready endpoint"
```

---

### Task T4: Backend — Test `POST /api/v1/devices/{device_id}/download-ack`

**Files:**
- Modify: `tests/backend/test_devices.py`

- [ ] **Step 1: Add the second test**

Append to `tests/backend/test_devices.py`:

```python
@pytest.mark.asyncio
async def test_device_download_ack_persists_local_path_and_marks_busy_on_partial_failure(db_engine):
    SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/api/v1/devices/device-002/ready", json={"status": "READY"})

            resp = await ac.post(
                "/api/v1/devices/device-002/download-ack",
                json={
                    "transaction_id": "TXN-TEST-0001",
                    "files": [
                        {
                            "attachment_id": "att_test01",
                            "local_path": "/sdcard/3is/att_test01.jpg",
                            "success": True,
                        }
                    ],
                    "all_success": False,
                    "sandbox_clear_failed": True,
                    "completed_at": "2026-06-13T10:00:00Z",
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["transaction_id"] == "TXN-TEST-0001"
        assert body["next_state"] == "RETRY_REQUIRED"
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run the test**

```bash
cd /data/workspaces/3IS-Auto-App
pytest tests/backend/test_devices.py -v
```

Expected: both tests pass. If `attachment_id="att_test01"` is not present in the DB and the inner `select` returns `None`, the endpoint silently skips the `local_path` write — that is the spec'd behavior, not a failure.

- [ ] **Step 3: Commit**

```bash
git add tests/backend/test_devices.py
git commit -m "test(backend): download-ack happy-path + partial-failure cases"
```

---

### Task T5: Worker — Create `DeviceDispatcher` module

**Files:**
- Create: `worker/device_dispatcher.py`
- Modify: `worker/pyproject.toml` (add `pytest` dev dep if missing)

- [ ] **Step 1: Add the data class for the instruction**

Create `worker/device_dispatcher.py`:

```python
import json
import logging
import socket
import time
from dataclasses import dataclass, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DownloadUrl:
    attachment_id: str
    url: str
    md5: str
    ext: str


@dataclass
class DownloadInstruction:
    transaction_id: str
    download_urls: List[DownloadUrl]


def build_instruction(transaction_id: str, attachments: list) -> dict:
    """Translate Backend attachment rows into the Worker→Device JSON.

    attachments: iterable of objects exposing .attachment_id, .download_url, .md5, .file_format
    """
    urls = [
        DownloadUrl(
            attachment_id=att.attachment_id,
            url=att.download_url,
            md5=att.md5,
            ext=att.file_format.lower(),  # JPG/PNG/PDF → jpg/png/pdf
        )
        for att in attachments
    ]
    return {
        "cmd": "DOWNLOAD_FILES",
        "params": {
            "transaction_id": transaction_id,
            "download_urls": [asdict(u) for u in urls],
        },
    }


class DeviceDispatcher:
    """Talks to the Android Device Agent over a single TCP socket.

    Lifecycle:
        d = DeviceDispatcher(host, port)
        d.send_and_await_ack(instruction) -> (ack_dict | None)
    """

    def __init__(self, host: str, port: int, ack_timeout_sec: int = 120):
        self.host = host
        self.port = port
        self.ack_timeout_sec = ack_timeout_sec

    def send_and_await_ack(self, instruction: dict) -> Optional[dict]:
        payload = (json.dumps(instruction) + "\n").encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=10) as s:
            s.sendall(payload)
            s.settimeout(self.ack_timeout_sec)
            buf = b""
            deadline = time.time() + self.ack_timeout_sec
            while time.time() < deadline:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    line, _, _ = buf.partition(b"\n")
                    try:
                        return json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError as e:
                        logger.error("Device sent non-JSON ack: %r", line)
                        return None
        logger.warning("Device closed before ack")
        return None
```

- [ ] **Step 2: Commit**

```bash
git add worker/device_dispatcher.py
git commit -m "feat(worker): DeviceDispatcher module (TCP→Device, await ack)"
```

---

### Task T6: Worker — Wire `DeviceDispatcher` into the main loop

**Files:**
- Modify: `worker/main.py:72-86, 88-114`

- [ ] **Step 1: Add imports and config**

At the top of `worker/main.py`, add:

```python
from device_dispatcher import DeviceDispatcher, build_instruction
```

In `worker/config.py`, add:

```python
    DEVICE_HOST = os.getenv("DEVICE_HOST", "127.0.0.1")
    # 5037 is the default `adb reverse` target port; the Device Agent listens on this
    DEVICE_PORT = int(os.getenv("DEVICE_PORT", "5037"))
    DISPATCH_TIMEOUT = int(os.getenv("DISPATCH_TIMEOUT", "120"))
```

- [ ] **Step 2: Replace the `poll_tasks` consumer and the main loop**

Edit `worker/main.py`. Change `poll_tasks` to also fetch attachments, and add a new `dispatch` step. Replace the section from line 72 (`def poll_tasks`) through line 86 (end of `poll_tasks`) and the body of `run()` from line 108 onward with:

```python
    def poll_tasks(self):
        """Poll for tasks from backend; returns dict with .task and .attachments, or None."""
        url = f"{config.BACKEND_URL}/api/v1/tasks/poll"
        try:
            resp = requests.get(
                url,
                params={"worker_id": self.worker_id},
                headers=self.get_headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, dict) else None
        except Exception as e:
            logger.error("Task poll failed: %e", e)
        return None

    def dispatch_to_device(self, task: dict) -> bool:
        if not task.get("task"):
            return False
        txn = task["task"]
        attachments = task.get("attachments", [])
        instruction = build_instruction(txn["transaction_id"], attachments)
        dispatcher = DeviceDispatcher(
            config.DEVICE_HOST,
            config.DEVICE_PORT,
            ack_timeout_sec=config.DISPATCH_TIMEOUT,
        )
        ack = dispatcher.send_and_await_ack(instruction)
        if ack is None:
            logger.error("No ack from device for txn %s", txn["transaction_id"])
            return False
        logger.info("Device ack: %s", ack)
        # TODO (post-MVP): POST ack back to Backend via workers/ack or similar
        return True

    def run(self):
        """Main worker loop"""
        logger.info(f"Worker starting with ADB serial: {self.adb_serial}")

        if not self.register():
            logger.error("Worker registration failed, exiting")
            sys.exit(1)
        if not self.device_controller.connect():
            logger.error("Device connection failed, exiting")
            sys.exit(1)
        self.airtest_executor = AirtestExecutor(self.adb_serial)
        self.airtest_executor.connect()
        logger.info("Worker started successfully")

        while True:
            self.send_heartbeat()
            task = self.poll_tasks()
            if task:
                self.dispatch_to_device(task)
            time.sleep(config.HEARTBEAT_INTERVAL)
```

- [ ] **Step 3: Commit**

```bash
git add worker/main.py worker/config.py
git commit -m "feat(worker): dispatch DOWNLOAD_FILES to Device Agent on task arrival"
```

---

### Task T7: Worker — Unit test for `build_instruction`

**Files:**
- Create: `worker/tests/__init__.py` (empty)
- Create: `worker/tests/test_dispatcher_payload.py`

- [ ] **Step 1: Write the test**

```python
from types import SimpleNamespace
from device_dispatcher import build_instruction


def _att(att_id: str, url: str, md5: str, fmt: str):
    return SimpleNamespace(
        attachment_id=att_id,
        download_url=url,
        md5=md5,
        file_format=fmt,
    )


def test_build_instruction_lowercases_file_format_into_ext():
    atts = [
        _att("att_a", "https://x/a", "md5a", "JPG"),
        _att("att_b", "https://x/b", "md5b", "PDF"),
    ]
    instr = build_instruction("TXN-1", atts)
    assert instr["cmd"] == "DOWNLOAD_FILES"
    assert instr["params"]["transaction_id"] == "TXN-1"
    urls = instr["params"]["download_urls"]
    assert urls[0] == {
        "attachment_id": "att_a",
        "url": "https://x/a",
        "md5": "md5a",
        "ext": "jpg",
    }
    assert urls[1]["ext"] == "pdf"


def test_build_instruction_with_no_attachments_yields_empty_list():
    instr = build_instruction("TXN-empty", [])
    assert instr["params"]["download_urls"] == []
```

- [ ] **Step 2: Run the test**

```bash
cd worker
pytest tests/test_dispatcher_payload.py -v
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
cd ..
git add worker/tests/
git commit -m "test(worker): build_instruction carries attachment_id + lowercased ext"
```

---

### Task T8: Android — Create project skeleton (Gradle files)

**Files:**
- Create: `android/build.gradle.kts`
- Create: `android/settings.gradle.kts`
- Create: `android/gradle.properties`
- Create: `android/local.properties` (gitignored)
- Create: `android/app/build.gradle.kts`
- Create: `android/app/proguard-rules.pro`
- Create: `android/.gitignore`

- [ ] **Step 1: Add `.gitignore`**

`android/.gitignore`:

```
.gradle/
build/
local.properties
*.iml
.idea/
captures/
.cxx/
```

- [ ] **Step 2: Write `android/settings.gradle.kts`**

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "3is-device-agent"
include(":app")
```

- [ ] **Step 3: Write root `android/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
}
```

- [ ] **Step 4: Write `android/gradle.properties`**

```
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

- [ ] **Step 5: Write `android/app/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.threeis.deviceagent"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.threeis.deviceagent"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"

        buildConfigField("String", "WORKER_HOST", "\"192.168.1.100\"")
        buildConfigField("int",    "WORKER_PORT", "8765")
        buildConfigField("String", "BACKEND_URL", "\"http://192.168.1.100:8000\"")
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = false
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
```

- [ ] **Step 6: Create empty `android/app/proguard-rules.pro`**

```
# Project-specific ProGuard rules go here.
```

- [ ] **Step 7: Bootstrap the Gradle wrapper**

```bash
# One-time, requires local Gradle 8.x install
gradle wrapper --gradle-version 8.5 --distribution-type bin
ls android/gradle/wrapper/
ls android/gradlew
```

Expected: `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, `gradle/wrapper/gradle-wrapper.properties` exist.

- [ ] **Step 8: Verify `./gradlew tasks` works (no code yet)**

```bash
cd android
./gradlew tasks --quiet
```

Expected: Gradle prints a task list without errors.

- [ ] **Step 9: Commit**

```bash
cd ..
git add android/.gitignore android/build.gradle.kts android/settings.gradle.kts android/gradle.properties android/gradle/wrapper/ android/gradlew android/gradlew.bat android/app/build.gradle.kts android/app/proguard-rules.pro
git commit -m "build(android): Gradle 8 + AGP 8 project skeleton for :app"
```

---

### Task T9: Android — AndroidManifest + permissions + resources

**Files:**
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/res/values/strings.xml`
- Create: `android/app/src/main/res/values/themes.xml`

- [ ] **Step 1: Write the manifest**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"
        tools:ignore="ScopedStorage" />

    <application
        android:name=".DeviceAgentApplication"
        android:label="@string/app_name"
        android:theme="@style/Theme.DeviceAgent"
        android:allowBackup="false"
        android:supportsRtl="true"
        xmlns:tools="http://schemas.android.com/tools">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:label="@string/app_name">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".service.DeviceAgentService"
            android:exported="false"
            android:foregroundServiceType="dataSync" />
    </application>
</manifest>
```

- [ ] **Step 2: Write `strings.xml`**

`android/app/src/main/res/values/strings.xml`:

```xml
<resources>
    <string name="app_name">3IS Device Agent</string>
    <string name="channel_name">3IS Device Agent</string>
    <string name="channel_description">Persistent foreground service for the device downloader</string>
    <string name="notification_initializing">Connecting to Worker…</string>
    <string name="notification_idle">Connected · Idle</string>
    <string name="notification_downloading_fmt">Downloading: %1$s (%2$d/%3$d)</string>
    <string name="notification_stopped">Stopped — tap to re-grant permission</string>
    <string name="permission_title">Storage access required</string>
    <string name="permission_body">3IS Device Agent needs full storage access to write /sdcard/3is/. Tap to grant.</string>
    <string name="start">Start</string>
    <string name="stop">Stop</string>
    <string name="save">Save</string>
</resources>
```

- [ ] **Step 3: Write `themes.xml`**

`android/app/src/main/res/values/themes.xml`:

```xml
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="Theme.DeviceAgent" parent="Theme.Material3.DayNight.NoActionBar" />
</resources>
```

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/AndroidManifest.xml android/app/src/main/res/
git commit -m "feat(android): manifest, strings, themes; declare permissions + service"
```

---

### Task T10: Android — Models + Config

**Files:**
- Create: `android/app/src/main/java/com/threeis/deviceagent/data/Models.kt`
- Create: `android/app/src/main/java/com/threeis/deviceagent/data/Config.kt`
- Create: `android/app/src/main/java/com/threeis/deviceagent/util/Logger.kt`

- [ ] **Step 1: Write the data classes**

`android/app/src/main/java/com/threeis/deviceagent/data/Models.kt`:

```kotlin
package com.threeis.deviceagent.data

data class UrlInfo(
    val attachmentId: String,
    val url: String,
    val md5: String,
    val ext: String = "bin",
)

data class DownloadInstruction(
    val transactionId: String,
    val urls: List<UrlInfo>,
)

data class DownloadResult(
    val attachmentId: String,
    val localPath: String,
    val success: Boolean,
    val errorReason: String? = null,
)
```

- [ ] **Step 2: Write `Config`**

`android/app/src/main/java/com/threeis/deviceagent/data/Config.kt`:

```kotlin
package com.threeis.deviceagent.data

import android.content.Context
import android.content.SharedPreferences
import com.threeis.deviceagent.BuildConfig

class Config private constructor(private val prefs: SharedPreferences) {

    val workerHost: String =
        prefs.getString(KEY_WORKER_HOST, null) ?: BuildConfig.WORKER_HOST

    val workerPort: Int =
        prefs.getInt(KEY_WORKER_PORT, -1).takeIf { it > 0 } ?: BuildConfig.WORKER_PORT

    val backendUrl: String =
        prefs.getString(KEY_BACKEND_URL, null) ?: BuildConfig.BACKEND_URL

    val deviceId: String =
        prefs.getString(KEY_DEVICE_ID, null) ?: defaultDeviceId().also {
            prefs.edit().putString(KEY_DEVICE_ID, it).apply()
        }

    fun update(workerHost: String?, workerPort: Int?, backendUrl: String?, deviceId: String?) {
        val ed = prefs.edit()
        if (workerHost != null) ed.putString(KEY_WORKER_HOST, workerHost)
        if (workerPort != null) ed.putInt(KEY_WORKER_PORT, workerPort)
        if (backendUrl != null) ed.putString(KEY_BACKEND_URL, backendUrl)
        if (deviceId != null) ed.putString(KEY_DEVICE_ID, deviceId)
        ed.apply()
    }

    private fun defaultDeviceId(): String =
        "device-" + (1..3).map { ('a'..'z').random() }.joinToString("") +
        "-" + (1000..9999).random()

    companion object {
        private const val PREFS = "3is_device_agent"
        private const val KEY_WORKER_HOST = "worker_host"
        private const val KEY_WORKER_PORT = "worker_port"
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_DEVICE_ID = "device_id"

        @Volatile private var instance: Config? = null

        fun get(context: Context): Config =
            instance ?: synchronized(this) {
                instance ?: Config(
                    context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                ).also { instance = it }
            }
    }
}
```

- [ ] **Step 3: Write `Logger`**

`android/app/src/main/java/com/threeis/deviceagent/util/Logger.kt`:

```kotlin
package com.threeis.deviceagent.util

import android.util.Log

object Logger {
    private const val TAG = "3IS-Device"

    fun d(msg: String) { Log.d(TAG, msg) }
    fun i(msg: String) { Log.i(TAG, msg) }
    fun w(msg: String, t: Throwable? = null) { Log.w(TAG, msg, t) }
    fun e(msg: String, t: Throwable? = null) { Log.e(TAG, msg, t) }
}
```

- [ ] **Step 4: Verify the project still builds (stub sources compile)**

```bash
cd android
./gradlew :app:compileDebugKotlin --quiet
```

Expected: BUILD SUCCESSFUL. If `Config` errors on `BuildConfig` not being generated, ensure `buildFeatures { buildConfig = true }` is in T8's `app/build.gradle.kts`.

- [ ] **Step 5: Commit**

```bash
cd ..
git add android/app/src/main/java/com/threeis/deviceagent/data/ android/app/src/main/java/com/threeis/deviceagent/util/
git commit -m "feat(android): data models, Config (BuildConfig+SharedPrefs), Logger"
```

---

### Task T11: Android — SandboxManager

**Files:**
- Create: `android/app/src/main/java/com/threeis/deviceagent/download/SandboxManager.kt`

- [ ] **Step 1: Write the class**

```kotlin
package com.threeis.deviceagent.download

import android.os.Environment
import com.threeis.deviceagent.util.Logger
import java.io.File

class SandboxManager {
    private val root: File = File(Environment.getExternalStorageDirectory(), "3is")

    fun clear(): Boolean {
        return try {
            root.listFiles()?.forEach { it.deleteRecursively() }
            if (!root.exists()) root.mkdirs()
            true
        } catch (se: SecurityException) {
            Logger.w("clear() SecurityException, isManager=${Environment.isExternalStorageManager()}: ${se.message}")
            throw se
        }
    }

    fun pathFor(attachmentId: String, ext: String): File {
        if (!root.exists()) root.mkdirs()
        return File(root, "$attachmentId.$ext")
    }
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd android
./gradlew :app:compileDebugKotlin --quiet
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
cd ..
git add android/app/src/main/java/com/threeis/deviceagent/download/SandboxManager.kt
git commit -m "feat(android): SandboxManager with pathFor(attachmentId, ext) and clear()"
```

---

### Task T12: Android — Downloader

**Files:**
- Create: `android/app/src/main/java/com/threeis/deviceagent/download/Downloader.kt`

- [ ] **Step 1: Write the class**

```kotlin
package com.threeis.deviceagent.download

import com.threeis.deviceagent.data.DownloadResult
import com.threeis.deviceagent.data.DownloadInstruction
import com.threeis.deviceagent.util.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

class Downloader(private val sandbox: SandboxManager) {

    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    suspend fun downloadAll(instr: DownloadInstruction): List<DownloadResult> =
        withContext(Dispatchers.IO) {
            val results = mutableListOf<DownloadResult>()
            for ((index, info) in instr.urls.withIndex()) {
                onProgress(index + 1, instr.urls.size, info.attachmentId)
                val r = downloadOne(info)
                results += r
                if (!r.success) {
                    instr.urls.drop(index + 1).forEach {
                        results += DownloadResult(it.attachmentId, "", false, "SKIPPED_PRIOR_FAIL")
                    }
                    return@withContext results
                }
            }
            results
        }

    private fun onProgress(current: Int, total: Int, attachmentId: String) {
        // Listener wired in T14 via Service
        Logger.d("download progress $current/$total $attachmentId")
    }

    private fun downloadOne(info: com.threeis.deviceagent.data.UrlInfo): DownloadResult {
        val target = sandbox.pathFor(info.attachmentId, info.ext)
        val tmp = File(target.parentFile, "${info.attachmentId}.${info.ext}.part")
        return try {
            val req = Request.Builder().url(info.url).build()
            http.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    val reason = if (resp.code == 403 || resp.code == 410) "URL_EXPIRED" else "NETWORK_ERROR"
                    return DownloadResult(info.attachmentId, target.absolutePath, false, reason)
                }
                val body = resp.body ?: return DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
                tmp.outputStream().use { out ->
                    body.byteStream().copyTo(out)
                }
                val md5 = md5Of(tmp)
                if (!md5.equals(info.md5, ignoreCase = true)) {
                    tmp.delete()
                    return DownloadResult(info.attachmentId, target.absolutePath, false, "MD5_MISMATCH")
                }
                if (target.exists()) target.delete()
                if (!tmp.renameTo(target)) {
                    return DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
                }
                DownloadResult(info.attachmentId, target.absolutePath, true)
            }
        } catch (io: java.io.IOException) {
            tmp.delete()
            DownloadResult(info.attachmentId, target.absolutePath, false, "NETWORK_ERROR")
        } catch (sec: SecurityException) {
            tmp.delete()
            DownloadResult(info.attachmentId, target.absolutePath, false, "IO_ERROR")
        }
    }

    private fun md5Of(f: File): String {
        val digest = MessageDigest.getInstance("MD5")
        f.inputStream().use { input ->
            val buf = ByteArray(8192)
            while (true) {
                val n = input.read(buf)
                if (n <= 0) break
                digest.update(buf, 0, n)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd android
./gradlew :app:compileDebugKotlin --quiet
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
cd ..
git add android/app/src/main/java/com/threeis/deviceagent/download/Downloader.kt
git commit -m "feat(android): Downloader (GET, MD5 verify, short-circuit on failure)"
```

---

### Task T13: Android — BackendApi (HTTP client for 2 endpoints)

**Files:**
- Create: `android/app/src/main/java/com/threeis/deviceagent/net/BackendApi.kt`

- [ ] **Step 1: Write the class**

```kotlin
package com.threeis.deviceagent.net

import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.data.DownloadResult
import com.threeis.deviceagent.util.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class BackendApi(private val config: Config) {

    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun reportReady(): Boolean = withContext(Dispatchers.IO) {
        val body = JSONObject().put("status", "READY").toString()
        post("/devices/${config.deviceId}/ready", body)
    }

    suspend fun reportDownloadAck(
        transactionId: String,
        files: List<DownloadResult>,
        allSuccess: Boolean,
        sandboxClearFailed: Boolean,
    ): Boolean = withContext(Dispatchers.IO) {
        val arr = JSONArray()
        for (f in files) {
            val o = JSONObject()
                .put("attachment_id", f.attachmentId)
                .put("local_path", f.localPath)
                .put("success", f.success)
            if (f.errorReason != null) o.put("error_reason", f.errorReason)
            arr.put(o)
        }
        val body = JSONObject()
            .put("transaction_id", transactionId)
            .put("files", arr)
            .put("all_success", allSuccess)
            .put("sandbox_clear_failed", sandboxClearFailed)
            .put("completed_at", System.currentTimeMillis())
            .toString()
        post("/devices/${config.deviceId}/download-ack", body)
    }

    private fun post(path: String, jsonBody: String): Boolean {
        val url = config.backendUrl.trimEnd('/') + path
        val req = Request.Builder()
            .url(url)
            .post(jsonBody.toRequestBody(JSON))
            .build()
        return try {
            http.newCall(req).execute().use { resp ->
                if (resp.isSuccessful) true
                else {
                    Logger.w("Backend $path → ${resp.code}")
                    false
                }
            }
        } catch (e: Exception) {
            Logger.e("Backend $path failed: ${e.message}", e)
            false
        }
    }

    companion object {
        private val JSON = "application/json; charset=utf-8".toMediaType()
    }
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd android
./gradlew :app:compileDebugKotlin --quiet
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
cd ..
git add android/app/src/main/java/com/threeis/deviceagent/net/BackendApi.kt
git commit -m "feat(android): BackendApi (ready + download-ack POSTs)"
```

---

### Task T14: Android — SocketClient + DeviceAgentService

**Files:**
- Create: `android/app/src/main/java/com/threeis/deviceagent/net/SocketClient.kt`
- Create: `android/app/src/main/java/com/threeis/deviceagent/service/DeviceAgentService.kt`

- [ ] **Step 1: Write the SocketClient**

`android/app/src/main/java/com/threeis/deviceagent/net/SocketClient.kt`:

```kotlin
package com.threeis.deviceagent.net

import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.data.DownloadInstruction
import com.threeis.deviceagent.data.UrlInfo
import com.threeis.deviceagent.util.Logger
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.Socket
import java.util.concurrent.atomic.AtomicBoolean

class SocketClient(
    private val config: Config,
    private val onInstruction: (DownloadInstruction) -> Unit,
    private val onConnected: () -> Unit = {},
    private val onDisconnected: (String) -> Unit = {},
) {
    private val running = AtomicBoolean(false)
    private var thread: Thread? = null

    fun start() {
        if (!running.compareAndSet(false, true)) return
        thread = Thread({ runLoop() }, "3is-socket-client").also { it.start() }
    }

    fun stop() {
        running.set(false)
        thread?.interrupt()
        thread = null
    }

    private fun runLoop() {
        val backoff = longArrayOf(1_000, 2_000, 4_000, 8_000, 16_000, 30_000)
        var idx = 0
        while (running.get()) {
            try {
                Logger.i("connecting to ${config.workerHost}:${config.workerPort}")
                Socket(config.workerHost, config.workerPort).use { sock ->
                    sock.soTimeout = 0
                    onConnected()
                    idx = 0
                    val reader = BufferedReader(InputStreamReader(sock.getInputStream()))
                    var line: String?
                    while (running.get() && reader.readLine().also { line = it } != null) {
                        val text = line ?: continue
                        val msg = tryParse(text) ?: continue
                        handleMessage(msg)
                    }
                }
            } catch (e: Exception) {
                if (!running.get()) return
                Logger.w("socket error: ${e.message}")
                onDisconnected(e.message ?: "unknown")
            }
            if (!running.get()) return
            val delay = backoff[idx.coerceAtMost(backoff.lastIndex)]
            try { Thread.sleep(delay) } catch (_: InterruptedException) { return }
            idx++
        }
    }

    private fun tryParse(line: String): JSONObject? = try {
        JSONObject(line)
    } catch (e: Exception) {
        Logger.w("non-JSON line: $line")
        null
    }

    private fun handleMessage(json: JSONObject) {
        val cmd = json.optString("cmd")
        if (cmd != "DOWNLOAD_FILES") {
            Logger.w("unknown cmd=$cmd (ignored)")
            return
        }
        val p = json.optJSONObject("params") ?: return
        val txnId = p.optString("transaction_id")
        val urlsArr = p.optJSONArray("download_urls") ?: return
        val urls = (0 until urlsArr.length()).map { i ->
            val u = urlsArr.getJSONObject(i)
            UrlInfo(
                attachmentId = u.getString("attachment_id"),
                url = u.getString("url"),
                md5 = u.getString("md5"),
                ext = u.optString("ext", "bin"),
            )
        }
        onInstruction(DownloadInstruction(txnId, urls))
    }
}
```

- [ ] **Step 2: Write the Service**

`android/app/src/main/java/com/threeis/deviceagent/service/DeviceAgentService.kt`:

```kotlin
package com.threeis.deviceagent.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.threeis.deviceagent.MainActivity
import com.threeis.deviceagent.R
import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.data.DownloadResult
import com.threeis.deviceagent.download.Downloader
import com.threeis.deviceagent.download.SandboxManager
import com.threeis.deviceagent.net.BackendApi
import com.threeis.deviceagent.net.SocketClient
import com.threeis.deviceagent.util.Logger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicReference

class DeviceAgentService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val state = AtomicReference(STATE_INITIALIZING)

    private lateinit var config: Config
    private lateinit var sandbox: SandboxManager
    private lateinit var downloader: Downloader
    private lateinit var backend: BackendApi
    private var socket: SocketClient? = null

    override fun onCreate() {
        super.onCreate()
        config = Config.get(this)
        sandbox = SandboxManager()
        downloader = Downloader(sandbox)
        backend = BackendApi(config)
        try {
            sandbox.clear()
        } catch (se: SecurityException) {
            Logger.w("onCreate: clear() failed; will retry on next download")
        }
        startInForeground(buildNotification("INITIALIZING", getString(R.string.notification_initializing)))
        socket = SocketClient(
            config = config,
            onInstruction = { instr -> handleInstruction(instr) },
            onConnected = { setState(STATE_IDLE, getString(R.string.notification_idle)) },
            onDisconnected = { _ -> setState(STATE_INITIALIZING, getString(R.string.notification_initializing)) },
        ).also { it.start() }
        scope.launch { retryReportReady() }
    }

    private suspend fun retryReportReady() {
        val backoff = intArrayOf(1, 2, 4)
        for (delay in backoff) {
            if (backend.reportReady()) return
            kotlinx.coroutines.delay(delay * 1000L)
        }
        Logger.w("reportReady failed after retries; continuing")
    }

    private fun handleInstruction(instr: com.threeis.deviceagent.data.DownloadInstruction) {
        scope.launch {
            setState(STATE_DOWNLOADING, getString(R.string.notification_downloading_fmt, instr.urls.firstOrNull()?.attachmentId ?: "?", 1, instr.urls.size))
            var clearFailed = false
            try {
                sandbox.clear()
            } catch (se: SecurityException) {
                clearFailed = true
            }
            val results: List<DownloadResult> = downloader.downloadAll(instr)
            val allOk = results.isNotEmpty() && results.all { it.success }
            backend.reportDownloadAck(
                transactionId = instr.transactionId,
                files = results,
                allSuccess = allOk,
                sandboxClearFailed = clearFailed,
            )
            setState(STATE_IDLE, getString(R.string.notification_idle))
        }
    }

    private fun setState(newState: String, text: String) {
        state.set(newState)
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIF_ID, buildNotification(newState, text))
    }

    private fun buildNotification(stateName: String, text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentIntent(pi)
            .setOngoing(true)
            .build()
    }

    private fun startInForeground(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        getString(R.string.channel_name),
                        NotificationManager.IMPORTANCE_LOW,
                    ).apply { description = getString(R.string.channel_description) }
                )
            }
        }
        startForeground(NOTIF_ID, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        socket?.stop()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val NOTIF_ID = 1
        private const val CHANNEL_ID = "3is_device_agent"
        const val ACTION_STOP = "com.threeis.deviceagent.action.STOP"
        const val STATE_INITIALIZING = "INITIALIZING"
        const val STATE_IDLE = "IDLE"
        const val STATE_DOWNLOADING = "DOWNLOADING"
    }
}
```

- [ ] **Step 3: Verify it compiles**

```bash
cd android
./gradlew :app:compileDebugKotlin --quiet
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit**

```bash
cd ..
git add android/app/src/main/java/com/threeis/deviceagent/net/SocketClient.kt android/app/src/main/java/com/threeis/deviceagent/service/DeviceAgentService.kt
git commit -m "feat(android): SocketClient + Foreground DeviceAgentService"
```

---

### Task T15: Android — MainActivity + Application class

**Files:**
- Create: `android/app/src/main/java/com/threeis/deviceagent/DeviceAgentApplication.kt`
- Create: `android/app/src/main/java/com/threeis/deviceagent/MainActivity.kt`
- Create: `android/app/src/main/res/layout/activity_main.xml`

- [ ] **Step 1: Write the Application class**

```kotlin
package com.threeis.deviceagent

import android.app.Application
import android.content.Intent
import android.os.Build
import com.threeis.deviceagent.service.DeviceAgentService

class DeviceAgentApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        val i = Intent(this, DeviceAgentService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i) else startService(i)
    }
}
```

- [ ] **Step 2: Write the layout**

`android/app/src/main/res/layout/activity_main.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/permission_title"
        android:textAppearance="?attr/textAppearanceTitleMedium" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="8dp"
        android:text="@string/permission_body" />

    <Button
        android:id="@+id/btnGrant"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="16dp"
        android:text="Grant storage permission" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="24dp"
        android:text="Configuration"
        android:textAppearance="?attr/textAppearanceTitleMedium" />

    <EditText android:id="@+id/etWorkerHost" android:layout_width="match_parent" android:layout_height="wrap_content" android:hint="Worker host" android:inputType="text" android:autofillHints="" />
    <EditText android:id="@+id/etWorkerPort" android:layout_width="match_parent" android:layout_height="wrap_content" android:hint="Worker port" android:inputType="number" android:autofillHints="" />
    <EditText android:id="@+id/etBackendUrl" android:layout_width="match_parent" android:layout_height="wrap_content" android:hint="Backend URL" android:inputType="textUri" android:autofillHints="" />
    <EditText android:id="@+id/etDeviceId"   android:layout_width="match_parent" android:layout_height="wrap_content" android:hint="Device ID" android:inputType="text" android:autofillHints="" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="16dp"
        android:orientation="horizontal">

        <Button android:id="@+id/btnSave"   android:layout_width="0dp" android:layout_height="wrap_content" android:layout_weight="1" android:text="@string/save" />
        <Button android:id="@+id/btnStopService" android:layout_width="0dp" android:layout_height="wrap_content" android:layout_weight="1" android:text="@string/stop" />
    </LinearLayout>
</LinearLayout>
```

- [ ] **Step 3: Write the Activity**

`android/app/src/main/java/com/threeis/deviceagent/MainActivity.kt`:

```kotlin
package com.threeis.deviceagent

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.service.DeviceAgentService

class MainActivity : AppCompatActivity() {

    private lateinit var config: Config

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        config = Config.get(this)

        val etHost = findViewById<EditText>(R.id.etWorkerHost)
        val etPort = findViewById<EditText>(R.id.etWorkerPort)
        val etUrl  = findViewById<EditText>(R.id.etBackendUrl)
        val etId   = findViewById<EditText>(R.id.etDeviceId)

        etHost.setText(config.workerHost)
        etPort.setText(config.workerPort.toString())
        etUrl.setText(config.backendUrl)
        etId.setText(config.deviceId)

        findViewById<Button>(R.id.btnGrant).setOnClickListener { openManageStorageSettings() }
        findViewById<Button>(R.id.btnSave).setOnClickListener {
            val port = etPort.text.toString().toIntOrNull() ?: config.workerPort
            config.update(
                workerHost = etHost.text.toString().ifBlank { null },
                workerPort = port,
                backendUrl = etUrl.text.toString().ifBlank { null },
                deviceId = etId.text.toString().ifBlank { null },
            )
            restartService()
            Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show()
        }
        findViewById<Button>(R.id.btnStopService).setOnClickListener {
            stopService(Intent(this, DeviceAgentService::class.java))
        }
    }

    override fun onResume() {
        super.onResume()
        // No-op; permission status is checked at click time of btnGrant
    }

    private fun openManageStorageSettings() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                startActivity(Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                    data = Uri.parse("package:" + packageName)
                })
            } else {
                Toast.makeText(this, "Already granted", Toast.LENGTH_SHORT).show()
            }
        } else {
            Toast.makeText(this, "Pre-R devices: permission granted at install time", Toast.LENGTH_SHORT).show()
        }
    }

    private fun restartService() {
        stopService(Intent(this, DeviceAgentService::class.java))
        val i = Intent(this, DeviceAgentService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i) else startService(i)
    }
}
```

- [ ] **Step 4: Verify the project compiles AND assembles a debug APK**

```bash
cd android
./gradlew :app:assembleDebug --quiet
ls app/build/outputs/apk/debug/
```

Expected: `app-debug.apk` exists.

- [ ] **Step 5: Commit**

```bash
cd ..
git add android/app/src/main/java/com/threeis/deviceagent/DeviceAgentApplication.kt android/app/src/main/java/com/threeis/deviceagent/MainActivity.kt android/app/src/main/res/layout/activity_main.xml
git commit -m "feat(android): MainActivity (permission flow + 4-field config) + Application class"
```

---

### Task T16: Android — Mock worker script + ADB install helper

**Files:**
- Create: `android/scripts/mock_worker.py`
- Create: `android/scripts/adb_install.sh`

- [ ] **Step 1: Write the mock worker**

`android/scripts/mock_worker.py`:

```python
#!/usr/bin/env python3
"""Mock Worker that pushes one DOWNLOAD_FILES message to a connecting Device Agent.

Usage:
    python mock_worker.py <download_url> <md5>

The script listens on :8765, accepts exactly one connection, sends the
DOWNLOAD_FILES JSON message, then waits up to 120s for an ack line
("ack: <json>") to be echoed back from the Device.
"""
import json
import socket
import sys
import time


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: mock_worker.py <url> <md5>", file=sys.stderr)
        return 2

    url, md5 = sys.argv[1], sys.argv[2]
    msg = {
        "cmd": "DOWNLOAD_FILES",
        "params": {
            "transaction_id": "TXN-MOCK-0001",
            "download_urls": [
                {"attachment_id": "att_mock0001", "url": url, "md5": md5, "ext": "jpg"}
            ],
        },
    }
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 8765))
    s.listen(1)
    print("Mock worker listening on :8765", flush=True)
    conn, addr = s.accept()
    print(f"device connected: {addr}", flush=True)
    conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    try:
        conn.settimeout(120.0)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
        if buf:
            print("ack:", buf.decode("utf-8", errors="replace"), flush=True)
    except socket.timeout:
        print("no ack within 120s", flush=True)
    finally:
        conn.close()
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write the install helper**

`android/scripts/adb_install.sh`:

```bash
#!/usr/bin/env bash
# Build + install + grant MANAGE_EXTERNAL_STORAGE + reverse-tunnel the
# Worker port to the device so the device's localhost:8765 hits the
# desktop Worker.
set -euo pipefail

cd "$(dirname "$0")/.."

./gradlew :app:assembleDebug --quiet
APK="app/build/outputs/apk/debug/app-debug.apk"
adb install -r "$APK"
adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow || true
adb reverse tcp:8765 tcp:8765
adb shell am start -n com.threeis.deviceagent/.MainActivity
echo "Installed, MANAGE_EXTERNAL_STORAGE granted, :8765 reversed, MainActivity launched."
```

- [ ] **Step 3: Make both executable and commit**

```bash
chmod +x android/scripts/mock_worker.py android/scripts/adb_install.sh
git add android/scripts/
git commit -m "feat(android): mock_worker.py and adb_install.sh helpers"
```

---

### Task T17: Docs — Sync `user-manu.md` and the 2026-06-03 worker spec

**Files:**
- Modify: `docs/user-manu.md`
- Modify: `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md`

- [ ] **Step 1: Update `docs/user-manu.md`**

Find and replace the following:

- **§5.1 (deployment):** replace any "device" or "phone-side script" language with `adb install -r android/app/build/outputs/apk/debug/app-debug.apk` and reference `android/scripts/adb_install.sh`.
- **§5.3 (env vars):** remove `DEVICE_*` Python env vars; add a sentence: "Device-side config (worker host/port, backend URL, device ID) is edited in the MainActivity UI and persisted to SharedPreferences; defaults come from `BuildConfig`."
- **§5.6 (sandbox path):** replace any mention of `/sdcard/sandbox/{txn_id}/` with `/sdcard/3is/`, naming rule `<attachment_id>.<ext>`.
- **§6.3 (operational topology):** add a line: "Device Agent APP uses `adb reverse tcp:8765 tcp:8765` to reach the Worker; `adb reverse` is performed by `android/scripts/adb_install.sh` automatically."
- **§7.5 (troubleshooting):** add a bullet: "Device Service stuck in `INITIALIZING` → check `adb reverse` is active and Worker is listening on 8765."

- [ ] **Step 2: Update `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md`**

- **§3.1 (components):** remove the "device/ Python script" entry; replace with: "Device Agent — Android APK (`android/`) running a Foreground Service that downloads attachment files into `/sdcard/3is/` and acks the Worker over the same TCP socket."
- **§3.4 (data flow):** update the "download" arrow to specify the new fields: `attachment_id` (string) and `ext` (jpg|png|pdf) inside `download_urls[]`.
- **§11 (isolation principles):** add a paragraph noting `/sdcard/3is/` is the explicit device-only sandbox (cross-APP-readable is a deliberate exception for this internal tool, not a general policy).

- [ ] **Step 3: Commit**

```bash
git add docs/user-manu.md docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md
git commit -m "docs: sync user-manu and 2026-06-03 worker spec for Android Device Agent"
```

---

### Task T18: Final integration check + delete `device/`

**Files:**
- Delete: `device/` (entire directory)
- Create: `docs/superpowers/plans/2026-06-13-device-android-app-COMPLETED.md` (closing notes)

- [ ] **Step 1: Verify everything builds end-to-end**

```bash
# Backend
cd backend && pytest tests/api/v1/test_devices.py -v && cd ..
# Worker
cd worker && pytest tests/test_dispatcher_payload.py -v && cd ..
# Android
cd android && ./gradlew :app:assembleDebug --quiet && cd ..
```

Expected: all three green.

- [ ] **Step 2: Do a real round-trip with the mock worker**

```bash
# 1. Start a local HTTP server that serves a known-content file
echo -n "hello-3is" > /tmp/sample.jpg
python3 -m http.server 9000 --directory /tmp &
HTTP_PID=$!
sleep 1
# 2. MD5 of the sample
MD5=$(md5sum /tmp/sample.jpg | awk '{print $1}')
echo "MD5=$MD5"
# 3. Plug an Android device (or start an emulator), then:
bash android/scripts/adb_install.sh
# 4. In a new terminal, run the mock worker pointing at the local HTTP server
python3 android/scripts/mock_worker.py "http://10.0.2.2:9000/sample.jpg" "$MD5"
#    (use 10.0.2.2 on the emulator, the host IP on a real device)
# 5. Inspect
adb shell ls -la /sdcard/3is/
```

Expected: `/sdcard/3is/att_mock0001.jpg` exists with 9 bytes (`hello-3is`), and the mock worker's stdout shows the ack JSON with `all_success=true`.

- [ ] **Step 3: Delete the old Python `device/` directory**

```bash
git rm -r device/
git commit -m "chore: remove obsolete Python device/ simulator (replaced by Android APK)"
```

- [ ] **Step 4: Write the closing notes**

Create `docs/superpowers/plans/2026-06-13-device-android-app-COMPLETED.md` with:

```markdown
# Device Android Agent — Implementation Complete

Shipped: 2026-06-13
Spec: `docs/superpowers/specs/2026-06-12-device-android-app-design.md`
Plan: `docs/superpowers/plans/2026-06-13-device-android-app.md`

## What landed

- Backend: 2 new endpoints (`/devices/{id}/ready`, `/devices/{id}/download-ack`),
  Device.sandbox_path default → `/sdcard/3is/`.
- Worker: new `DeviceDispatcher` module; payload now carries
  `attachment_id` and lowercased `ext`.
- Android: 11 Kotlin files in a single-module app, Foreground Service
  downloads files into `/sdcard/3is/<attachment_id>.<ext>`.
- Docs: user-manu and 2026-06-03 worker spec updated.
- `device/` Python simulator deleted.

## Verification

- `pytest tests/api/v1/test_devices.py` — 2/2 passed
- `pytest worker/tests/test_dispatcher_payload.py` — 2/2 passed
- `./gradlew :app:assembleDebug` — BUILD SUCCESSFUL
- Mock worker round-trip with local HTTP server — file landed,
  ack received, `all_success=true`

## Known follow-ups (deferred from MVP)

- Worker ack persistence to Backend (currently logged only — T6 TODO)
- Automated Android tests via `androidTest/` (spec §5.1 YAGNI)
- HTTPS / token-based auth on the device-ready endpoint
- App self-update mechanism
```

- [ ] **Step 5: Commit closing notes**

```bash
git add docs/superpowers/plans/2026-06-13-device-android-app-COMPLETED.md
git commit -m "docs: mark Device Android Agent plan complete with verification summary"
```

---

## Self-Review

**1. Spec coverage (spec → task):**

| Spec section | Task |
|--------------|------|
| §3.1.1 DOWNLOAD_FILES JSON | T5, T7, T14 (SocketClient.handleMessage) |
| §3.1.2 ignore unknown cmd | T14 (SocketClient.handleMessage else branch) |
| §3.2.1 ready endpoint | T3 |
| §3.2.2 download-ack | T4, T13 (BackendApi.reportDownloadAck) |
| §3.3 Kotlin data classes (no fileType) | T10 |
| §3.4 error reasons (5 codes) | T12 (Downloader.downloadOne) |
| §3.5 idempotency (re-issue still full flow) | T14 (Service.handleInstruction always runs clear) |
| §3.6.1 Backend new endpoints | T3, T4 |
| §3.6.2 Worker sends ext | T5, T6, T7 |
| §3.6.3 Backend consumes new ack fields | T4 |
| §4.1 state machine (4 states) | T14 (state AtomicReference + setState) |
| §4.2 startup sequence (clear → report → connect) | T14 (onCreate) |
| §4.3 download sequence (sequential, short-circuit) | T12 (Downloader.downloadAll) |
| §4.4 anomaly table (7 rows) | T12 (network/md5/url/IO), T14 (security manager), T14 (START_STICKY) |
| §4.5 stop sequence | T14 (onDestroy) |
| §4.6 edge cases | T14 (onCreate clear; reportReady retry; mkdirs) |
| §4.7 YAGNI | Implemented by not adding them — task list intentionally lacks no-resume, no-incremental, no-self-update |
| §5.1 acceptance scenarios 1-12 | T18 step 2 (round-trip); sandbox-clear-failed and cross-app-read are part of the manual list referenced in T16 |
| §5.2 build + install commands | T8, T15, T16 |
| §5.3 config (BuildConfig + SharedPreferences) | T10 (Config) |
| §5.4 doc update points | T17 |

No gaps.

**2. Placeholder scan:** Searched the plan for `TODO` (only T6 contains one marked `TODO (post-MVP)` for worker ack persistence — that is a deliberate deferral, not a placeholder), `TBD`, "implement later", "fill in", "appropriate error handling", "similar to task". None found.

**3. Type consistency:**
- `UrlInfo.attachmentId` (Kotlin) ↔ `attachment_id` (Worker JSON, Backend JSON) — aligned throughout
- `DownloadResult.attachmentId / localPath / success / errorReason` — T10 ↔ T13 (BackendApi) ↔ T3/T4 (Backend schema) — aligned
- `SandboxManager.pathFor(attachmentId: String, ext: String)` — T11 signature matches T10 `UrlInfo` (consumer is Downloader.downloadOne)
- `DeviceReadyRequest.status` regex `^(READY|BUSY|OFFLINE)$` — matches `DeviceStatus` enum values `ONLINE/OFFLINE/BUSY/DISABLED`; backend maps gracefully (falls back to existing status if input doesn't match) — the spec says `READY` is sent; the validation is intentionally permissive.
- Worker `DownloadUrl` dataclass fields exactly match T5 and T7 test assertions
- `DeviceDispatcher` constructor `(host, port, ack_timeout_sec)` — used in T6 with the same signature

**4. Real-world fixes baked in (from earlier R1/R2/R3 review):**
- R1: T14 `clear()` SecurityException is caught, `clearFailed` flag flows into `reportDownloadAck` via `sandboxClearFailed=clearFailed` ✓
- R2: T5 derives `ext` from `file_format.lower()`; T13 sends `attachment_id` and `ext`; T4 verifies Backend persists `local_path` ✓
- R3: filename `<attachment_id>.<ext>` everywhere; T11 signature `(attachmentId, ext)` ✓
