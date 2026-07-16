import os
from unittest.mock import MagicMock, patch

from airtest_executor import AirtestExecutor


def _make_executor():
    """Build an AirtestExecutor without connecting to a device."""
    executor = AirtestExecutor.__new__(AirtestExecutor)
    executor.adb_serial = "test_serial"
    executor.device = None
    return executor


def test_run_script_injects_customer_phone():
    """CUSTOMER_PHONE env var is set during the airtest call and cleaned after."""
    executor = _make_executor()

    captured = {}

    def fake_run_script(args):
        captured["CUSTOMER_PHONE"] = os.environ.get("CUSTOMER_PHONE")
        captured["HOLDER_PHONE"] = os.environ.get("HOLDER_PHONE")

    with patch("airtest_executor._airtest_run_script", side_effect=fake_run_script):
        executor.run_script(
            "/tmp/fake.air",
            transaction_meta={
                "transaction_id": "T-1",
                "holder_phone": "13800138000",
                "customer_phone": "13900139000",
                "business_type": "NEW_VEHICLE",
                "tax_exempt": False,
                "is_transfer": True,
            },
        )

    assert captured["CUSTOMER_PHONE"] == "13900139000"
    assert captured["HOLDER_PHONE"] == "13800138000"
    assert "CUSTOMER_PHONE" not in os.environ
    assert "HOLDER_PHONE" not in os.environ
