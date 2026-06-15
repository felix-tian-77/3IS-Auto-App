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
