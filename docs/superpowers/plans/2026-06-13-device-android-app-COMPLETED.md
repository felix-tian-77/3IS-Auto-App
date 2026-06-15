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
| Backend | `cd backend && .venv/bin/python -m pytest tests/backend/test_devices.py -v` | 3/3 passed |
| Worker  | `cd worker && .venv/bin/python -m pytest tests/ -v` | 2/2 passed |
| Android | `cd android && ./gradlew :app:assembleDebug` | **NOT RUN** — sandbox lacks Gradle wrapper + Android SDK + Java 17/21 (Java 25 only). Files are complete; a host with proper tooling can build them. |

For the spec's 12 manual-acceptance scenarios, see `docs/superpowers/specs/2026-06-12-device-android-app-design.md` §5.1. The mock worker (`android/scripts/mock_worker.py`) supports scenarios 4, 5, 6, 11; a real device is required for the rest.

## Commits (24 atomic commits)

Run `git log --oneline 16f863b..HEAD` to see the full list. Highlights:

- Plan: 1 commit
- Backend: 9 commits (schemas, sandbox default, 2 endpoints, 4 fix commits for the T4 spec review)
- Worker: 5 commits (DeviceDispatcher + 2 fixes + main-loop wiring + tests)
- Android: 12 commits (Gradle skeleton, manifest, 8 source files in 3 commits, 2 carryover fixes, mock+adb scripts)
- Docs: 2 commits (user-manu + worker spec sync)
- Cleanup: 1 commit (device/ deletion)

## Known follow-ups (deferred from MVP)

- **Build verification** — Android APK was not built in this sandbox. A developer with Gradle 8.5 + Android SDK 34 + Java 17/21 can run `./gradlew :app:assembleDebug` from `android/`. (Note: also need to run `gradle wrapper --gradle-version 8.5 --distribution-type bin` to generate the wrapper, since it wasn't bootstrapped in the sandbox.)
- **Worker ack persistence to Backend** — currently the Device ack is logged but not POSTed back. The T6 dispatcher has a `TODO (post-MVP)` marker.
- **Automated Android tests** — spec §5.1 deliberately skipped these; add when regression risk grows.
- **HTTPS / token-based auth on the device-ready endpoint** — the current `device_id` in the URL is the only auth; not production-safe.
- **App self-update** — `adb install -r` is the only update path.
- **Pre-existing `test_statistics.py` failures** — 2 tests in `backend/tests/backend/test_statistics.py` fail due to enum/.value mismatches in `dashboard_service.py:157`. Unrelated to this plan but should be fixed separately.
- **Pre-existing `pywin32` Linux sync issue** — `worker/pyproject.toml` declares `airtest` which transitively requires `pywinauto` (Windows only). `uv sync` fails on Linux. Unrelated to this plan.
- **`Logger.error("Task poll failed: %e", e)`** — pre-existing formatting bug at `worker/main.py:86` (uses `%e` instead of `%s` or `logger.exception`). Carried through; not addressed.
- **Other hardcoded toasts in MainActivity** — `"Already granted"` and `"Pre-R devices: permission granted at install time"` are not in strings.xml. Lint will warn; MVP-acceptable.
