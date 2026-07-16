import argparse
import logging
import os
from airtest.core.api import connect_device, start_app, stop_app, text, touch, snapshot, sleep
from airtest.core.error import TargetNotFoundError
from airtest.cli.runner import run_script as _airtest_run_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapping from snake_case keys in `transaction_meta` to their SCREAMING_SNAKE
# env-var names that airtest scripts will read.
_META_TO_ENV = {
    "transaction_id": "TRANSACTION_ID",
    "holder_phone":   "HOLDER_PHONE",
    "business_type":  "BUSINESS_TYPE",
    "tax_exempt":     "TAX_EXEMPT",
    "is_transfer":    "IS_TRANSFER",
}

# The set of env-var names that this module owns. Used for snapshot/restore.
_ENV_KEYS = frozenset(_META_TO_ENV.values())

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

    def run_script(self, script_path: str, transaction_meta: dict | None = None) -> bool:
        """Run an Airtest .air script directory.

        Uses airtest.cli.runner.run_script under the hood. Airtest manages its own
        device connection via auto_setup(), so this method does NOT reuse
        self.device — it constructs an android:/// URI from self.adb_serial.

        If ``transaction_meta`` is provided, the 5 known keys are injected into
        ``os.environ`` for the duration of the airtest call so that the .air
        script can read them via ``os.environ.get("HOLDER_PHONE")`` etc., then
        restored to their pre-call values via ``try/finally`` (so the keys are
        removed if they didn't previously exist, or set back to their old
        values if they did).

        Values that are ``None`` in ``transaction_meta`` are NOT written to
        ``os.environ`` (the key is left absent). Booleans are encoded as the
        lower-case strings ``"true"`` / ``"false"``.

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

        env_snapshot = {k: os.environ.get(k) for k in _ENV_KEYS}

        if transaction_meta is not None:
            for key_in_meta, key_in_env in _META_TO_ENV.items():
                value = transaction_meta.get(key_in_meta)
                if value is None:
                    # Leave os.environ untouched for None values (don't pop,
                    # don't write empty string). The script will see "key
                    # absent" → os.environ.get(...) is None.
                    continue
                if isinstance(value, bool):
                    os.environ[key_in_env] = "true" if value else "false"
                else:
                    os.environ[key_in_env] = str(value)

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
        finally:
            for key_in_env, prior_value in env_snapshot.items():
                if prior_value is None:
                    os.environ.pop(key_in_env, None)
                else:
                    os.environ[key_in_env] = prior_value