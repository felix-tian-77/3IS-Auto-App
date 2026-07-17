import pytest

from backend.config import get_settings
from backend.schemas.transaction import (
    AttachmentMeta,
    BusinessType,
    TransactionCreateRequest,
)
from backend.services.transaction_service import TransactionService


@pytest.mark.asyncio
async def test_storage_key_uses_transaction_id_and_backend_filename(
    db_session, tmp_path, monkeypatch
):
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    get_settings.cache_clear()

    service = TransactionService(db_session)
    service.storage.base_path = str(tmp_path)

    request = TransactionCreateRequest(
        business_type=BusinessType.NEW_VEHICLE,
        customer_phone="13800000000",
        customer_id_no="110101199001011234",
        attachments_meta=[
            AttachmentMeta(file_type="ID_CARD_FRONT", file_format="JPG"),
            AttachmentMeta(file_type="ID_CARD_BACK", file_format="PNG"),
            AttachmentMeta(file_type="ELECTRONIC_INVOICE", file_format="PDF"),
            AttachmentMeta(file_type="CERTIFICATE", file_format="PDF"),
        ],
    )

    files = [
        (
            {
                "filename": "front.jpg",
                "content_type": "image/jpeg",
                "file_type": "ID_CARD_FRONT",
                "file_format": "JPG",
            },
            b"front-bytes",
        ),
        (
            {
                "filename": "back.PNG",
                "content_type": "image/png",
                "file_type": "ID_CARD_BACK",
                "file_format": "PNG",
            },
            b"back-bytes",
        ),
        (
            {
                "filename": "invoice.pdf",
                "content_type": "application/pdf",
                "file_type": "ELECTRONIC_INVOICE",
                "file_format": "PDF",
            },
            b"invoice-bytes",
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
    expected_names = [
        "ID_CARD_FRONT.jpg",
        "ID_CARD_BACK.png",
        "ELECTRONIC_INVOICE.pdf",
        "CERTIFICATE.pdf",
    ]
    expected_bodies = [
        b"front-bytes",
        b"back-bytes",
        b"invoice-bytes",
        b"cert-bytes",
    ]

    assert len(result["attachments"]) == 4
    for idx, attachment in enumerate(result["attachments"]):
        storage_path = attachment["storage_path"]
        expected_key = f"{transaction_id}/{expected_names[idx]}"
        assert storage_path == expected_key

        on_disk = tmp_path / storage_path
        assert on_disk.exists()
        assert on_disk.read_bytes() == expected_bodies[idx]

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_storage_key_handles_missing_extension(
    db_session, tmp_path, monkeypatch
):
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    get_settings.cache_clear()

    service = TransactionService(db_session)
    service.storage.base_path = str(tmp_path)

    request = TransactionCreateRequest(
        business_type=BusinessType.NEW_VEHICLE,
        customer_phone="13800000000",
        customer_id_no="110101199001011234",
        attachments_meta=[
            AttachmentMeta(file_type="ID_CARD_FRONT", file_format="JPG"),
            AttachmentMeta(file_type="ID_CARD_BACK", file_format="PNG"),
            AttachmentMeta(file_type="ELECTRONIC_INVOICE", file_format="PDF"),
            AttachmentMeta(file_type="CERTIFICATE", file_format="PDF"),
        ],
    )

    files = [
        (
            {
                "filename": "front",
                "content_type": "image/jpeg",
                "file_type": "ID_CARD_FRONT",
                "file_format": "JPG",
            },
            b"raw-bytes",
        ),
        (
            {
                "filename": "back.PNG",
                "content_type": "image/png",
                "file_type": "ID_CARD_BACK",
                "file_format": "PNG",
            },
            b"back-bytes",
        ),
        (
            {
                "filename": "invoice.pdf",
                "content_type": "application/pdf",
                "file_type": "ELECTRONIC_INVOICE",
                "file_format": "PDF",
            },
            b"invoice-bytes",
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

    result = await service.create_transaction(request, files, customer_id="cust-2")
    transaction_id = result["transaction_id"]
    storage_path = result["attachments"][0]["storage_path"]
    expected_key = f"{transaction_id}/ID_CARD_FRONT"

    assert storage_path == expected_key
    on_disk = tmp_path / storage_path
    assert on_disk.exists()
    assert on_disk.read_bytes() == b"raw-bytes"

    get_settings.cache_clear()
