from datetime import datetime
from pathlib import Path

import pytest

from backend.config import get_settings
from backend.schemas.transaction import (
    AttachmentMeta,
    BusinessType,
    TransactionCreateRequest,
)
from backend.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_storage_key_uses_date_and_transaction_id(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    get_settings.cache_clear()

    service = TransactionService(db_session)
    service.storage.base_path = str(tmp_path)

    request = TransactionCreateRequest(
        business_type=BusinessType.NEW,
        customer_phone="13800000000",
        customer_id_no="110101199001011234",
        attachments_meta=[
            AttachmentMeta(file_type="ID_FRONT", file_format="JPG"),
            AttachmentMeta(file_type="ID_BACK", file_format="PNG"),
            AttachmentMeta(file_type="CERTIFICATE", file_format="PDF"),
        ],
    )

    files = [
        (
            {
                "filename": "front.jpg",
                "content_type": "image/jpeg",
                "file_type": "ID_FRONT",
                "file_format": "JPG",
            },
            b"front-bytes",
        ),
        (
            {
                "filename": "back.PNG",
                "content_type": "image/png",
                "file_type": "ID_BACK",
                "file_format": "PNG",
            },
            b"back-bytes",
        ),
        (
            {
                "filename": "cert.pdf",
                "content_type": "application/pdf",
                "file_type": "CERTIFICATE",
                "file_format": "PDF",
            },
            b"cert-bytes",
        ),
    ]

    result = await service.create_transaction(request, files, customer_id="cust-1")

    transaction_id = result["transaction_id"]
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    expected_suffixes = ["_001.jpg", "_002.png", "_003.pdf"]
    expected_bodies = [b"front-bytes", b"back-bytes", b"cert-bytes"]

    assert len(result["attachments"]) == 3
    for idx, attachment in enumerate(result["attachments"]):
        storage_path = attachment["storage_path"]
        expected_filename = f"{transaction_id}{expected_suffixes[idx]}"
        expected_key = f"{date_str}/{transaction_id}/{expected_filename}"
        assert storage_path == expected_key, (
            f"attachment {idx} storage_path mismatch: "
            f"got {storage_path!r}, expected {expected_key!r}"
        )

        on_disk = tmp_path / storage_path
        assert on_disk.exists(), f"expected file on disk at {on_disk}"
        assert on_disk.read_bytes() == expected_bodies[idx]

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_storage_key_handles_missing_extension(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    get_settings.cache_clear()

    service = TransactionService(db_session)
    service.storage.base_path = str(tmp_path)

    request = TransactionCreateRequest(
        business_type=BusinessType.NEW,
        customer_phone="13800000000",
        customer_id_no="110101199001011234",
        attachments_meta=[
            AttachmentMeta(file_type="OTHER", file_format="OTHER"),
        ],
    )

    files = [
        (
            {
                "filename": "noext",
                "content_type": "application/octet-stream",
                "file_type": "OTHER",
                "file_format": "OTHER",
            },
            b"raw-bytes",
        ),
    ]

    result = await service.create_transaction(request, files, customer_id="cust-2")

    transaction_id = result["transaction_id"]
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    storage_path = result["attachments"][0]["storage_path"]
    expected_key = f"{date_str}/{transaction_id}/{transaction_id}_001"
    assert storage_path == expected_key, (
        f"storage_path mismatch: got {storage_path!r}, expected {expected_key!r}"
    )

    on_disk = tmp_path / storage_path
    assert on_disk.exists(), f"expected file on disk at {on_disk}"
    assert on_disk.read_bytes() == b"raw-bytes"

    get_settings.cache_clear()
