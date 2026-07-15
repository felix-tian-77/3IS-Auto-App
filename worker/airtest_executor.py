import argparse
import logging
from airtest.core.api import connect_device, start_app, stop_app, text, touch, snapshot, sleep
from airtest.core.error import TargetNotFoundError
from airtest.cli.runner import run_script as _airtest_run_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirtestExecutor:
    def __init__(self, adb_serial: str):
        self.adb_serial = adb_serial
        self.device = None

    def connect(self):
        """Connect to device with Airtest"""
        self.device = connect_device(f"android:///{self.adb_serial}")

    def execute_step(self, action_type: str, params: dict) -> dict:
        """Execute a single Airtest step"""
        try:
            if action_type == "OPEN_APP":
                package = params.get("package")
                start_app(self.device, package)
                return {"status": "success", "action": action_type}

            elif action_type == "INPUT":
                content = params.get("content", "")
                text(self.device, content)
                return {"status": "success", "action": action_type}

            elif action_type == "CLICK":
                pos = params.get("position")
                if pos:
                    touch(self.device, pos)
                else:
                    touch(self.device)
                return {"status": "success", "action": action_type}

            elif action_type == "SCREENSHOT":
                screenshot_path = params.get("screenshot_path", "screenshot.png")
                snapshot(self.device, screenshot=screenshot_path)
                return {"status": "success", "action": action_type, "path": screenshot_path}

            elif action_type == "WAIT":
                seconds = params.get("seconds", 1)
                sleep(seconds)
                return {"status": "success", "action": action_type}

            else:
                return {"status": "fail", "error": f"Unknown action type: {action_type}"}

        except TargetNotFoundError as e:
            logger.error(f"Target not found: {e}")
            return {"status": "fail", "error": str(e)}
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return {"status": "fail", "error": str(e)}

    def disconnect(self):
        """Disconnect from device"""
        if self.device:
            self.device = None

    def run_script(self, script_path: str) -> bool:
        """Run an Airtest .air script directory.

        Uses airtest.cli.runner.run_script under the hood. Airtest manages its own
        device connection via auto_setup(), so this method does NOT reuse
        self.device — it constructs an android:/// URI from self.adb_serial.

        Returns True on clean exit, False on assertion failure (SystemExit 20),
        other failure (SystemExit -1), or any other exception. Never raises.
        """
        args = argparse.Namespace(
            script=script_path,
            device=f"android:///{self.adb_serial}",
            log=True,
            recording=None,
            compress=None,
            no_image=False,
        )
        try:
            _airtest_run_script(args)
            return True
        except SystemExit as e:
            logger.error(
                "Airtest script %s exited with code %s", script_path, e.code
            )
            return False
        except Exception as e:
            logger.error(
                "Airtest script %s raised exception: %s", script_path, e
            )
            return False