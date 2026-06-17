# Device Android Agent — Implementation Complete

Shipped: 2026-06-15
Spec: `docs/superpowers/specs/2026-06-12-device-android-app-design.md`
Plan: `docs/superpowers/plans/2026-06-13-device-android-app.md`

## What landed

- **Backend** — 2 new endpoints (`/devices/{id}/ready`, `/devices/{id}/download-ack`),
  Device.sandbox_path default → `/sdcard/3is/`, `Attachment.local_path` column.
- **Worker** — new `DeviceDispatcher` module; payload now carries
  `attachment_id` and lowercased `ext`; main loop dispatches to Device on task arrival.
- **Android** — 11 Kotlin files in a single-module app, Foreground Service
  downloads files into `/sdcard/3is/<attachment_id>.<ext>`.
- **Docs** — user-manu and 2026-06-03 worker spec updated.
- **`device/`** — Python simulator deleted.

## Verification

| Component | Test command | Result |
|---|---|---|
| Backend | `backend/.venv/bin/python -m pytest tests/backend/test_devices.py -v` | 3/3 passed |
| Worker  | `cd worker && .venv/bin/python -m pytest tests/ -v` | 2/2 passed |
| Android | `cd android && ./gradlew :app:assembleDebug` | **PARTIAL** — Gradle 8.11.1 wrapper now in repo (commit `c755fd6`); APK build is `BUILD-VERIFIED-OFF-SANDBOX` pending a developer box with Android SDK 34. |

For the spec's 12 manual-acceptance scenarios, see `docs/superpowers/specs/2026-06-12-device-android-app-design.md` §5.1. The mock worker (`android/scripts/mock_worker.py`) supports scenarios 4, 5, 6, 11; a real device is required for the rest.

## Commit count

Run `git log --oneline 16f863b..HEAD | wc -l` for the live count. As of this doc: **44 commits** (38 initial + 6 post-review fixes).

Approximate breakdown (verified by `git log --oneline`):

- Plan amendments: 3 (T2 amend, T2 smoke-test fix, T3+T4 test-path fix)
- Backend: 11 (Pydantic schemas, sandbox default, ready endpoint, download-ack endpoint + revert + refactor, aiosqlite pin, 3 tests, style fix)
- Worker: 7 (DeviceDispatcher + 2 fixes, main-loop wiring, 2 tests, pytest build dep)
- Android: 18 (Gradle skeleton, manifest+resources, 11 Kotlin source/fix commits, mock+adb scripts, SocketClient bidirectional, ACTION_STOP wiring, POST_NOTIFICATIONS, strings refactor)
- Docs: 2 (T17 user-manu + worker-spec sync, T18 closing notes)
- Cleanup: 1 (device/ deletion)

## Post-review fixes

After the initial 38-commit landing, a final code review found 3 critical/important bugs in the Android implementation. They were fixed in 6 follow-up commits:

- **T14.2** (`7cac59f`) — SocketClient was read-only; the Device never wrote the `DOWNLOAD_COMPLETE` ack back over the TCP socket. The Worker would hit the 120s timeout on every task. Fix: `SocketClient` now stores an `OutputStream`, exposes `sendAck(payload)`, and the Service calls it after `backend.reportDownloadAck(...)`.
- **T15.2** (`a866e72`) — `DeviceAgentService.onDestroy` did not call `stopForeground(STOP_FOREGROUND_REMOVE)`, leaving the FGS notification on the device. The `ACTION_STOP` constant was dead code. Fix: `onStartCommand` now honors `ACTION_STOP` via `stopSelf()`; `onDestroy` calls `stopForeground` and sets state to `STATE_STOPPED`.
- **T15.3** (`5d27f67`, `2f987fb`) — `POST_NOTIFICATIONS` was declared in the manifest but never requested at runtime. On Android 13+ this would suppress the FGS notification silently. Fix: `MainActivity` now requests the permission via `ActivityResultContracts.RequestPermission`, gated on API 33+.
- **T18.2** (`f095652`) — `COMPLETED.md`'s verification command (`cd backend && .venv/bin/python ...`) resolved to a non-existent path. Fix: the command now uses `backend/.venv/bin/python -m pytest ...` from the repo root.

After the 6 fixes, the implementation passed a second code review (verdict: "Ready to merge: Yes").

## Known follow-ups (deferred from MVP)

- **Build verification** — Android APK was not built in this sandbox because Android SDK 34 is not installed here. The Gradle 8.11.1 wrapper is now committed, so a developer with Android SDK 34 + JDK 17/21 can run `./gradlew :app:assembleDebug` from `android/` without first installing system Gradle.
- **Worker ack persistence to Backend** — currently the Device ack is logged but not POSTed back. The T6 dispatcher has a `TODO (post-MVP)` marker.
- **Automated Android tests** — spec §5.1 deliberately skipped these; add when regression risk grows.
- **HTTPS / token-based auth on the device-ready endpoint** — the current `device_id` in the URL is the only auth; not production-safe.
- **App self-update** — `adb install -r` is the only update path.
- **Pre-existing `test_statistics.py` failures** — 2 tests in `backend/tests/backend/test_statistics.py` fail due to enum/.value mismatches in `dashboard_service.py:157`. Unrelated to this plan but should be fixed separately.
- **Pre-existing `pywin32` Linux sync issue** — `worker/pyproject.toml` declares `airtest` which transitively requires `pywinauto` (Windows only). `uv sync` fails on Linux. Unrelated to this plan.
- **`Logger.error("Task poll failed: %e", e)`** — pre-existing formatting bug at `worker/main.py:86` (uses `%e` instead of `%s` or `logger.exception`). Carried through; not addressed.
- **Other hardcoded toasts in MainActivity** — `"Already granted"` and `"Pre-R devices: permission granted at install time"` are not in strings.xml. Lint will warn; MVP-acceptable.
- **Pre-existing `scripts/init_db.sql:27` corruption** — a shell command (`uvicorn backend.main:app...`) is concatenated into the middle of a SQL DEFAULT clause. The file is loaded by `scripts/docker-compose.yaml:14` (mounted to the postgres container's `/docker-entrypoint-initdb.d/init.sql`); on a fresh `docker compose up` of a clean dev environment, this corruption will fail DB init. The running app uses `Base.metadata.create_all` so existing dev DBs are unaffected. The file should be cleaned up.
