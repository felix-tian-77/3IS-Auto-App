import subprocess
import time
from airtest.core.android.adb import ADB
from airtest.core.android.android import Android

class DeviceController:
    def __init__(self, adb_serial: str):
        self.adb_serial = adb_serial
        self.adb = ADB()
        self.device = None

    def connect(self) -> bool:
        """Connect to device via ADB"""
        try:
            self.device = Android(self.adb_serial)
            self.adb.connect()
            return True
        except Exception as e:
            print(f"ADB connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from device"""
        if self.device:
            self.device.disconnect()

    def shell(self, cmd: str) -> str:
        """Execute shell command on device"""
        return self.device.shell(cmd)

    def push_file(self, local_path: str, remote_path: str):
        """Push file to device"""
        self.device.push(local_path, remote_path)

    def pull_file(self, remote_path: str, local_path: str):
        """Pull file from device"""
        self.device.pull(remote_path, local_path)

    def get_device_info(self) -> dict:
        """Get device info"""
        try:
            battery_output = self.shell("dumpsys battery | grep level")
            battery_level = int(battery_output.split(":")[1].strip()) if ":" in battery_output else 0
        except (IndexError, ValueError):
            battery_level = 0

        return {
            "model": self.shell("getprop ro.product.model"),
            "android_version": self.shell("getprop ro.build.version.release"),
            "battery_level": battery_level,
        }