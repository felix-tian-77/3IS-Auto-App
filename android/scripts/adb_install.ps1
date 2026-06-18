#Requires -Version 5.1
# Build + install + grant MANAGE_EXTERNAL_STORAGE + reverse-tunnel the
# Worker port to the device so the device's localhost:8765 hits the
# desktop Worker. Windows PowerShell equivalent of adb_install.sh.

$ErrorActionPreference = 'Stop'

function Verify-Env {
    if ($env:SKIP_ENV_VERIFY -eq '1') {
        Write-Host "[adb_install] SKIP_ENV_VERIFY=1, skipping env checks"
        return
    }

    $javaBin = $null
    if ($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\java.exe")) {
        $javaBin = "$env:JAVA_HOME\bin\java.exe"
    } elseif (Get-Command java -ErrorAction SilentlyContinue) {
        $javaBin = (Get-Command java).Source
    } else {
        Write-Error @"
[adb_install] No 'java' on PATH and JAVA_HOME unset.
Install Temurin 21:
  Download: https://adoptium.net/temurin/releases/?version=21&os=windows
  After install, ensure JAVA_HOME is set to its install directory.
"@
        exit 1
    }
    $verLine = cmd /c "`"$javaBin`" -version 2>&1" | Select-Object -First 1
    if ($verLine -notmatch '"([\d.]+)"') {
        Write-Error "[adb_install] could not parse 'java -version' output: $verLine"
        exit 1
    }
    $javaVerFull = $matches[1]
    $javaMajor = ($javaVerFull -split '\.')[0]
    if ($javaMajor -ne '17' -and $javaMajor -ne '21') {
        Write-Error @"
[adb_install] JDK 17 or 21 required (found: $javaVerFull). Download Temurin 21 from
  https://adoptium.net/temurin/releases/?version=21&os=windows
and ensure JAVA_HOME points to its install directory.
"@
        exit 1
    }

    $sdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { $null }
    if (-not $sdkRoot) {
        Write-Error @"
[adb_install] ANDROID_HOME (or ANDROID_SDK_ROOT) not set.
Install Android SDK and set ANDROID_HOME to its root.
  Android Studio: Settings -> SDK Manager -> "Android SDK Location"
  Standalone:     https://developer.android.com/tools/sdkmanager
"@
        exit 1
    }
    if (-not (Test-Path "$sdkRoot\platforms\android-34\android.jar")) {
        Write-Error @"
[adb_install] Android SDK platform 34 missing under $sdkRoot.
Run: sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"
"@
        exit 1
    }
    $btDir = Get-ChildItem "$sdkRoot\build-tools" -Directory -Filter '34.*' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $btDir) {
        Write-Error @"
[adb_install] Android SDK build-tools 34.x missing under $sdkRoot\build-tools\.
Run: sdkmanager "build-tools;34.0.0"
"@
        exit 1
    }

    if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
        Write-Error "[adb_install] adb not in PATH. Add `$env:ANDROID_HOME\platform-tools to PATH."
        exit 1
    }
    $adbVer = (& adb --version | Select-Object -First 1).Split()[-1]

    Write-Host "[adb_install] env OK: java=$javaVerFull  android_sdk=$sdkRoot (platform-34, build-tools $($btDir.Name))  adb=$adbVer"
}

Verify-Env

Set-Location (Join-Path $PSScriptRoot '..')

& .\gradlew.bat :app:assembleDebug --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$APK = "app\build\outputs\apk\debug\app-debug.apk"
& adb install -r $APK
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow
$global:LASTEXITCODE = 0

& adb reverse tcp:8765 tcp:8765
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& adb shell am start -n com.threeis.deviceagent/.MainActivity
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installed, MANAGE_EXTERNAL_STORAGE granted, :8765 reversed, MainActivity launched."
