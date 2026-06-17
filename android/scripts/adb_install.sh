#!/usr/bin/env bash
# Build + install + grant MANAGE_EXTERNAL_STORAGE + reverse-tunnel the
# Worker port to the device so the device's localhost:8765 hits the
# desktop Worker.
set -euo pipefail

verify_env() {
  if [ "${SKIP_ENV_VERIFY:-}" = "1" ]; then
    echo "[adb_install] SKIP_ENV_VERIFY=1, skipping env checks"
    return 0
  fi

  local java_bin
  if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/java" ]; then
    java_bin="$JAVA_HOME/bin/java"
  elif command -v java >/dev/null 2>&1; then
    java_bin="$(command -v java)"
  else
    echo "[adb_install] No 'java' on PATH and JAVA_HOME unset." >&2
    echo "  Install Temurin 21:" >&2
    echo "    Ubuntu/Debian: sudo apt install temurin-21-jdk" >&2
    echo "    Fedora:        sudo dnf install temurin-21-jdk" >&2
    echo "    macOS:         brew install --cask temurin@21" >&2
    echo "    Or download:   https://adoptium.net/temurin/releases/?version=21" >&2
    return 1
  fi
  local java_ver_full
  java_ver_full=$("$java_bin" -version 2>&1 | awk -F'"' 'NR==1 {print $2}')
  local java_major
  java_major=$(printf '%s' "$java_ver_full" | awk -F'.' '{print $1}')
  if [ "$java_major" != "17" ] && [ "$java_major" != "21" ]; then
    echo "[adb_install] JDK 17 or 21 required (found: $java_ver_full). Install via:" >&2
    echo "  Ubuntu/Debian: sudo apt install temurin-21-jdk" >&2
    echo "  Fedora:        sudo dnf install temurin-21-jdk" >&2
    echo "  macOS:         brew install --cask temurin@21" >&2
    echo "  Or download:   https://adoptium.net/temurin/releases/?version=21" >&2
    return 1
  fi

  local sdk_root="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
  if [ -z "$sdk_root" ]; then
    echo "[adb_install] ANDROID_HOME (or ANDROID_SDK_ROOT) not set." >&2
    echo "Install Android SDK and set ANDROID_HOME to its root." >&2
    echo "  Android Studio: Settings → SDK Manager → \"Android SDK Location\"" >&2
    echo "  Standalone:     https://developer.android.com/tools/sdkmanager" >&2
    return 1
  fi
  if [ ! -f "$sdk_root/platforms/android-34/android.jar" ]; then
    echo "[adb_install] Android SDK platform 34 missing under $sdk_root." >&2
    echo "Run: sdkmanager \"platforms;android-34\" \"build-tools;34.0.0\" \"platform-tools\"" >&2
    return 1
  fi
  local bt_dir
  bt_dir=$(ls -d "$sdk_root"/build-tools/34.* 2>/dev/null | head -1 || true)
  if [ -z "$bt_dir" ]; then
    echo "[adb_install] Android SDK build-tools 34.x missing under $sdk_root/build-tools/." >&2
    echo "Run: sdkmanager \"build-tools;34.0.0\"" >&2
    return 1
  fi

  if ! command -v adb >/dev/null 2>&1; then
    echo "[adb_install] adb not in PATH. Add \$ANDROID_HOME/platform-tools to PATH." >&2
    return 1
  fi
  local adb_ver
  adb_ver=$(adb --version | awk 'NR==1 {print $NF}')

  echo "[adb_install] env OK: java=$java_ver_full  android_sdk=$sdk_root (platform-34, build-tools $(basename "$bt_dir"))  adb=$adb_ver"
}

verify_env

cd "$(dirname "$0")/.."

./gradlew :app:assembleDebug --quiet
APK="app/build/outputs/apk/debug/app-debug.apk"
adb install -r "$APK"
adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow || true
adb reverse tcp:8765 tcp:8765
adb shell am start -n com.threeis.deviceagent/.MainActivity
echo "Installed, MANAGE_EXTERNAL_STORAGE granted, :8765 reversed, MainActivity launched."
