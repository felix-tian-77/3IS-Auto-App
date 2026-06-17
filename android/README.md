# 3IS Device Agent (Android)

Android Foreground Service that connects to the desktop Worker over TCP, downloads attachments via HTTP, and ACKs completion. Replaces the legacy Python `device/` simulator. See `docs/user-manu.md` §5 for end-user docs.

## Prerequisites

- **JDK 17 or 21** (Temurin recommended). JDK 25 is NOT supported by Android Gradle Plugin 8.2.2.
- **Android SDK** with platform 34 + build-tools 34.x + platform-tools (`adb`). Set `ANDROID_HOME` (or `ANDROID_SDK_ROOT`) to the SDK root.
- **adb** on PATH (ships in `$ANDROID_HOME/platform-tools`).
- A real Android device (Android 7.0+, USB debugging enabled) or emulator running API 24+.

The install scripts run `verify_env` first and abort with actionable hints if any prerequisite is missing. Set `SKIP_ENV_VERIFY=1` to bypass (escape hatch for exotic JDK/SDK layouts).

## Quick Start

### Linux / macOS

```bash
cd android
JAVA_HOME=/path/to/jdk21 bash scripts/adb_install.sh
```

### Windows

```powershell
cd android
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.x-hotspot'
pwsh scripts\adb_install.ps1
```

If PowerShell blocks the script, allow it for this session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Both scripts:

1. Verify env (JDK 17/21, Android SDK 34, adb)
2. Build debug APK via `./gradlew :app:assembleDebug`
3. Install + grant `MANAGE_EXTERNAL_STORAGE`
4. `adb reverse tcp:8765 tcp:8765` (so device's `localhost:8765` hits desktop Worker)
5. Launch `MainActivity`

## Manual Build

```bash
cd android
JAVA_HOME=/path/to/jdk21 ./gradlew :app:assembleDebug
```

APK output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Project Layout

- `app/src/main/java/com/threeis/deviceagent/` — Kotlin sources
  - `service/DeviceAgentService.kt` — Foreground Service, 4-state machine
  - `net/SocketClient.kt` — bidirectional TCP (read `DOWNLOAD_FILES`, write `DOWNLOAD_COMPLETE`)
  - `net/HttpDownloader.kt` — OkHttp file download
  - `data/Config.kt` — singleton, persisted via SharedPreferences
  - `MainActivity.kt` — minimal UI
- `app/src/main/AndroidManifest.xml` — declares `MANAGE_EXTERNAL_STORAGE`
- `scripts/` — install scripts + `mock_worker.py` for local E2E

## Troubleshooting

**`gradlew: command not found`** — you're not in `android/`. `cd android` first.

**`Unsupported class file major version 69`** — JDK 25 detected. AGP 8.2.2 needs JDK 17 or 21. Set `JAVA_HOME` and re-run.

**`SDK location not found`** — `ANDROID_HOME` unset. Point it at the Android SDK root (the directory containing `platforms/`, `build-tools/`, `platform-tools/`).

**Gradle download is slow on first run** — the wrapper downloads `gradle-8.11.1-bin.zip` into `~/.gradle/wrapper/dists/` once. Subsequent invocations reuse it.

**Skipping env verification** — set `SKIP_ENV_VERIFY=1` (Linux/macOS) or `$env:SKIP_ENV_VERIFY = '1'` (Windows). Use only when the verifier mis-detects a working setup; report a bug if it does.

## End-User Docs

See `docs/user-manu.md` §5 for operator-facing setup, install, and troubleshooting (Chinese).
