import sys
import types
from unittest.mock import MagicMock

airtest_stub = types.ModuleType("airtest")
airtest_core = types.ModuleType("airtest.core")
airtest_android = types.ModuleType("airtest.core.android")
airtest_adb = types.ModuleType("airtest.core.android.adb")
airtest_android2 = types.ModuleType("airtest.core.android.android")
airtest_adb.ADB = MagicMock
airtest_android2.Android = MagicMock
sys.modules["airtest"] = airtest_stub
sys.modules["airtest.core"] = airtest_core
sys.modules["airtest.core.android"] = airtest_android
sys.modules["airtest.core.android.adb"] = airtest_adb
sys.modules["airtest.core.android.android"] = airtest_android2

from device_controller import DeviceController


def _make_controller(shell_returns):
    ctrl = DeviceController.__new__(DeviceController)
    ctrl.adb_serial = "fake"
    ctrl.adb = MagicMock()
    ctrl.device = MagicMock()
    ctrl.shell = MagicMock(side_effect=shell_returns)
    return ctrl


def test_get_status_parses_battery_and_storage():
    shell_returns = [
        "  level: 75",
        "Filesystem     3G  2G  1G 50% /sdcard",
        "  mWakefulness=Awake",
        "Xiaomi 13",
        "14",
    ]
    ctrl = _make_controller(shell_returns)
    status = ctrl.get_status()

    assert status["battery_level"] == 75
    assert status["storage_free_mb"] >= 0
    assert status["screen_locked"] is False
    assert status["model"] == "Xiaomi 13"
    assert status["android_version"] == "14"


def test_get_status_screen_locked_when_asleep():
    shell_returns = [
        "  level: 50",
        "Filesystem     3G  2G  1G 50% /sdcard",
        "  mWakefulness=Asleep",
        "OPPO",
        "13",
    ]
    ctrl = _make_controller(shell_returns)
    status = ctrl.get_status()

    assert status["screen_locked"] is True


def test_get_status_handles_bad_battery_output():
    shell_returns = [
        "garbage",
        "Filesystem     3G  2G  1G 50% /sdcard",
        "  mWakefulness=Awake",
        "Pixel",
        "14",
    ]
    ctrl = _make_controller(shell_returns)
    status = ctrl.get_status()

    assert status["battery_level"] == 0


def test_get_device_info_returns_basic_fields():
    shell_returns = [
        "  level: 90",
        "Samsung S24",
        "14",
    ]
    ctrl = _make_controller(shell_returns)
    info = ctrl.get_device_info()

    assert info["battery_level"] == 90
    assert info["model"] == "Samsung S24"
