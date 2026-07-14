import re

import pytest

from backend.services.transaction_service import TransactionService


class _FakeDB:
    pass


@pytest.fixture
def service() -> TransactionService:
    return TransactionService(_FakeDB())


def test_generate_id_transaction_format(service: TransactionService) -> None:
    txn_id = service._generate_id("T")
    assert re.fullmatch(r"T-\d{8}-[0-9a-f]{8}", txn_id), f"unexpected format: {txn_id}"
    prefix, date_part, unique = txn_id.split("-")
    assert prefix == "T"
    assert len(date_part) == 8
    assert len(unique) == 8


def test_generate_id_attachment_format(service: TransactionService) -> None:
    att_id = service._generate_id("A")
    assert re.fullmatch(r"A-\d{8}-[0-9a-f]{8}", att_id), f"unexpected format: {att_id}"
    prefix, date_part, unique = att_id.split("-")
    assert prefix == "A"
    assert len(date_part) == 8
    assert len(unique) == 8


def test_generate_id_no_collision_in_batch(service: TransactionService) -> None:
    ids = {service._generate_id("T") for _ in range(1000)}
    assert len(ids) == 1000, "duplicate ids detected in 1000 calls"


def test_generate_id_today_date(service: TransactionService) -> None:
    from datetime import datetime

    txn_id = service._generate_id("T")
    expected_prefix = datetime.now().strftime("%Y%m%d")
    assert txn_id.startswith(f"T-{expected_prefix}-"), f"date mismatch: {txn_id}"
