# Android Gradle Env & Install Scripts — Design Spec

**Date:** 2026-06-17
**Author:** opencode (under @felixtian direction)
**Status:** Pending review
**Branch:** `release/v1.0`

## 1. Goal

Make the `android/` subproject **clone-and-build** on Linux/macOS/Windows. After this change:

- `git clone` then `cd android && ./gradlew :app:assembleDebug` works without first running `gradle wrapper`.
- Linux/macOS users run `bash android/scripts/adb_install.sh` end-to-end.
- Windows users run `pwsh android/scripts/adb_install.ps1` end-to-end.
- Both scripts verify JDK 17/21, Android SDK 34, and `adb` BEFORE building, with actionable error messages on failure.
- A new `android/README.md` documents prerequisites, per-platform install, and troubleshooting.

## 2. In-Scope

1. Generate Gradle 8.11.1 wrapper (`gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, `gradle/wrapper/gradle-wrapper.properties`) and commit.
2. Add `verify_env()` to existing `android/scripts/adb_install.sh`.
3. Create `android/scripts/adb_install.ps1` (PowerShell, Windows equivalent).
4. Create `android/README.md` (~80 lines: prerequisites, install per-OS, usage, troubleshooting).
5. Add cross-link from `docs/user-manu.md §5.1` to `android/README.md`.
6. Update `docs/superpowers/plans/2026-06-13-device-android-app-COMPLETED.md` verification table.

## 3. Out-of-Scope

- Auto-downloading JDK or Android SDK (per A1/A2: detect-and-prompt only).
- CI workflow — separate PR.
- macOS-specific scripts (`.sh` already works on macOS).
- `cmd.exe` (`.bat`) compatibility — PowerShell only per A4.
- Code signing the `.ps1`.

## 4. File Structure

```
android/
├── gradlew                              (NEW, commit, exec bit)
├── gradlew.bat                          (NEW, commit)
├── gradle/wrapper/
│   ├── gradle-wrapper.jar               (NEW, commit, ~63 KB)
│   └── gradle-wrapper.properties        (NEW, pinned to gradle-8.11.1-bin.zip)
├── README.md                            (NEW, ~80 lines)
├── scripts/
│   ├── adb_install.sh                   (MODIFY: prepend verify_env)
│   ├── adb_install.ps1                  (NEW, PowerShell)
│   └── mock_worker.py                   (unchanged)
└── (existing build.gradle.kts / settings.gradle.kts / gradle.properties / app/ / .gitignore)

docs/
├── user-manu.md                         (MODIFY: §5.1 cross-link)
└── superpowers/plans/2026-06-13-device-android-app-COMPLETED.md   (MODIFY: verification row)
```

## 5. `verify_env()` Behavioral Contract (both scripts identical)

### 5.1 Three checks, serial short-circuit (first failure exits)

#### Check 1 — JDK version

- Source: prefer `$JAVA_HOME/bin/java`; fallback to `java` on PATH.
- Parse `java -version` stderr first line (e.g. `openjdk version "21.0.5" 2024-10-15`); extract major version from the quoted token.
- Accept `17` or `21`; otherwise fail.
- Failure message (Linux/macOS):
  ```
  [adb_install] JDK 17 or 21 required (found: <ver>). Install via:
    Ubuntu/Debian: sudo apt install temurin-21-jdk
    Fedora:        sudo dnf install temurin-21-jdk
    macOS:         brew install --cask temurin@21
    Or download:   https://adoptium.net/temurin/releases/?version=21
  ```
- Failure message (Windows):
  ```
  [adb_install] JDK 17 or 21 required (found: <ver>). Download Temurin 21 from
    https://adoptium.net/temurin/releases/?version=21&os=windows
  and ensure JAVA_HOME points to its install directory.
  ```

#### Check 2 — Android SDK

- Read `ANDROID_HOME`, fallback to `ANDROID_SDK_ROOT`. Both unset → fail.
- Verify `$SDK_ROOT/platforms/android-34/android.jar` exists.
- Verify `$SDK_ROOT/build-tools/` has at least one `34.*` subdirectory.
- Failure (env vars unset):
  ```
  [adb_install] ANDROID_HOME (or ANDROID_SDK_ROOT) not set.
  Install Android SDK and set ANDROID_HOME to its root.
    Android Studio: Settings → SDK Manager → "Android SDK Location"
    Standalone:     https://developer.android.com/tools/sdkmanager
  ```
- Failure (platform 34 missing):
  ```
  [adb_install] Android SDK platform 34 missing under $SDK_ROOT.
  Run: sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"
  ```

#### Check 3 — adb

- `command -v adb` (sh) / `Get-Command adb -ErrorAction SilentlyContinue` (ps1).
- Not found → fail:
  ```
  [adb_install] adb not in PATH. Add $ANDROID_HOME/platform-tools to PATH.
  ```
- Do **not** check device connectivity here; let `adb install` handle that case.

### 5.2 Success output (single line)

```
[adb_install] env OK: java=21.0.5  android_sdk=/opt/android-sdk (platform-34, build-tools 34.0.0)  adb=1.0.41
```

Versions extracted from `java -version`, `adb --version`, and `ls $SDK_ROOT/build-tools/` (pick the 34.x.x dir).

### 5.3 Bypass

`SKIP_ENV_VERIFY=1` env var (Linux) or `$env:SKIP_ENV_VERIFY = '1'` (Windows) bypasses all 3 checks. Documented in README "Troubleshooting" only — not advertised in normal flow. Used as escape hatch for rare JDK/SDK layouts.

### 5.4 Exit codes

- `0` — full success.
- `1` — env verification failed.
- `2+` — Gradle build / adb install failure (transparent passthrough).

## 6. Success Path (after verify passes)

| Step | `adb_install.sh` (Linux/macOS) | `adb_install.ps1` (Windows) |
|---|---|---|
| 1. cd to android/ | `cd "$(dirname "$0")/.."` | `Set-Location (Join-Path $PSScriptRoot '..')` |
| 2. Build APK | `./gradlew :app:assembleDebug --quiet` | `& .\gradlew.bat :app:assembleDebug --quiet` |
| 3. Install APK | `adb install -r "$APK"` | `& adb install -r $APK` |
| 4. Grant MANAGE_EXTERNAL_STORAGE | `adb shell appops set ... \|\| true` | `& adb shell appops set ...; $LASTEXITCODE = 0` |
| 5. Reverse port | `adb reverse tcp:8765 tcp:8765` | (same command via `&`) |
| 6. Launch MainActivity | `adb shell am start -n com.threeis.deviceagent/.MainActivity` | (same) |
| 7. Final echo | `echo "Installed, ..."` | `Write-Host "Installed, ..."` |

### 6.1 Strict modes

- `.sh`: `set -euo pipefail` (already present).
- `.ps1`: `$ErrorActionPreference = 'Stop'` at top. Step 4 explicitly tolerates non-zero via `$LASTEXITCODE = 0`.

### 6.2 APK path

Hardcoded `app/build/outputs/apk/debug/app-debug.apk` — Gradle default for the `:app:assembleDebug` task. Matches existing `.sh`.

### 6.3 PowerShell quirks

- `#Requires -Version 5.1` shebang (Windows 10 default).
- No `Invoke-Expression` (security): always `& cmd args`.
- README documents `Set-ExecutionPolicy -Scope Process Bypass` for first run.

## 7. `android/README.md` Outline

~80 lines, 6 sections:

1. **Title + 1-paragraph description** — what the Android Foreground Service does, link to `docs/user-manu.md §5`.
2. **Prerequisites table** — JDK 17/21, Android SDK platform 34 + build-tools 34.x + platform-tools, adb on PATH.
3. **Install (Linux/macOS)** — apt/brew for JDK; cmdline-tools URL + `sdkmanager` recipe for SDK; env vars in shell rc.
4. **Install (Windows)** — Temurin URL; Android Studio recommended for SDK; `[Environment]::SetEnvironmentVariable(...)`; `Set-ExecutionPolicy` note.
5. **Build & Install** — one-liner per OS; bullet list of what the script does.
6. **Troubleshooting** — 7 common errors with fix:
   - `JDK 17 or 21 required (found: X)` → install Temurin
   - `ANDROID_HOME not set` → install SDK + set var
   - `Android SDK platform 34 missing` → `sdkmanager "platforms;android-34" ...`
   - `adb: no devices/emulators found` → check USB cable + `adb devices`
   - `adb: device unauthorized` → accept dialog on device
   - `MANAGE_EXTERNAL_STORAGE` silent fail on some ROMs → manual settings path
   - Android 13+ no notification → grant notification permission (cross-ref user-manu §5.1 ⑤)

## 8. Cross-Link in `docs/user-manu.md §5.1`

Insert one line at the very top of §5.1 (above the existing 方式 1 paragraph):

```
> 环境前提(JDK 17/21、Android SDK 34、adb)详见 [`android/README.md`](../android/README.md)。
```

## 9. `COMPLETED.md` Verification Table Update

Change the Android row from:
```
| Android | `cd android && ./gradlew :app:assembleDebug` | **NOT RUN** — sandbox lacks Gradle wrapper + Android SDK + Java 17/21 (Java 25 only). Files are complete; a host with proper tooling can build them. |
```
to:
```
| Android | `cd android && ./gradlew :app:assembleDebug` | **PASS** — Gradle 8.11.1 wrapper now in repo. Build verified locally with JDK 21 + Android SDK 34. See `android/README.md` for prerequisites. |
```

Also update the "follow-ups" bullet to remove the `gradle wrapper` bootstrap mention.

## 10. Implementation Sequence (skeleton — `writing-plans` will refine)

```
0. Local install: JDK 21 + Gradle 8.11.1 (one-time prep, not committed)
1. cd android && gradle wrapper --gradle-version 8.11.1 --distribution-type bin
2. chmod +x gradlew
3. commit: "chore(android): add Gradle 8.11.1 wrapper"
4. modify adb_install.sh — add verify_env()
5. commit: "feat(android): add env verification to adb_install.sh"
6. create adb_install.ps1
7. commit: "feat(android): add adb_install.ps1 (Windows equivalent)"
8. write android/README.md
9. commit: "docs(android): add README with prerequisites and install guide"
10. update user-manu.md §5.1 cross-link
11. commit: "docs(user-manu): cross-link to android/README.md from §5.1"
12. update COMPLETED.md verification row
13. commit: "docs(plan): mark Android wrapper as in-repo in COMPLETED.md"
```

7 atomic commits.

## 11. Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Local Gradle 8.11.1 install blocks (SDKMAN unavailable) | Fallback: download `gradle-8.11.1-bin.zip` directly, extract to `~/.gradle-8.11.1/`, run once, discard |
| 2 | `gradle wrapper` produces non-portable artifact | The 4-file output is officially platform-neutral by Gradle design; `gradle-wrapper.jar` is JVM bytecode |
| 3 | `verify_env()` false negatives on exotic JDK / SDK layouts | `SKIP_ENV_VERIFY=1` escape hatch documented in Troubleshooting |
| 4 | Windows ExecutionPolicy blocks `.ps1` | README "Quick start" first line: `Set-ExecutionPolicy -Scope Process Bypass` |
| 5 | Sandbox/CI runs script without device | `adb install` returns clear "no devices/emulators found"; not our problem to wrap |

## 12. Verification Checklist (must run after implementation)

| # | Check | Command | Expected |
|---|---|---|---|
| 1 | wrapper 4 files present | `ls android/gradlew android/gradlew.bat android/gradle/wrapper/*` | All present, gradlew has +x |
| 2 | wrapper self-test | `cd android && ./gradlew --version` | Prints Gradle 8.11.1 + JVM version |
| 3 | `.sh` verify rejects Java 25 | `JAVA_HOME=/opt/java/current bash android/scripts/adb_install.sh` | exit 1, "JDK 17 or 21 required (found: 25)" |
| 4 | **End-to-end build with JDK 21** (REQUIRED) | `JAVA_HOME=<path-to-jdk21> bash android/scripts/adb_install.sh` (no device OK; verify reaches `gradlew assembleDebug`, build succeeds) | APK produced at `app/build/outputs/apk/debug/app-debug.apk` |
| 5 | `.ps1` syntax valid | `pwsh -NoProfile -Command "Get-Content android/scripts/adb_install.ps1 \| Out-Null"` | No syntax error (Linux pwsh); on Windows host, full run reaches `gradlew.bat` |
| 6 | README cross-link works | Eye-check: `docs/user-manu.md §5.1` first line points to `../android/README.md` | Relative link resolves on GitHub |
| 7 | COMPLETED.md updated | `grep "NOT RUN" docs/superpowers/plans/2026-06-13-device-android-app-COMPLETED.md` for Android row | 0 matches in the Android row |

Item 4 is **required** — implementer must install JDK 21 if not already present and run the build to confirm.

## 13. Success Criteria

1. Fresh `git clone` → `cd android` → `./gradlew :app:assembleDebug` produces APK without any wrapper bootstrap step.
2. Both `adb_install.{sh,ps1}` print clear actionable error when JDK / SDK / adb is missing.
3. README is the single source of truth for "how to set up Android dev locally"; user-manu §5.1 only points to it.
4. Verification checklist items 1-7 all pass.
