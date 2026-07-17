import pytest
from io import BytesIO
from PIL import Image

from backend.config import get_settings
from backend.schemas.transaction import (
    AttachmentMeta,
    BusinessType,
    TransactionCreateRequest,
)
from backend.services.transaction_service import TransactionService


def _make_png_bytes(mode: str = "RGB", size=(2, 2), color=(200, 0, 0)) -> bytes:
    buf = BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


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

    png_bytes = _make_png_bytes("RGB")

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
            png_bytes,
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
        "ID_CARD_BACK.jpg",
        "ELECTRONIC_INVOICE.pdf",
        "CERTIFICATE.pdf",
    ]

    assert len(result["attachments"]) == 4
    for idx, attachment in enumerate(result["attachments"]):
        storage_path = attachment["storage_path"]
        expected_key = f"{transaction_id}/{expected_names[idx]}"
        assert storage_path == expected_key

        on_disk = tmp_path / storage_path
        assert on_disk.exists()

        if idx == 1:
            assert attachment["file_format"] == "JPG"
            assert attachment["file_size"] == len(on_disk.read_bytes())
            with Image.open(on_disk) as im:
                assert im.format == "JPEG"
                assert im.mode == "RGB"
        else:
            original_body = [
                b"front-bytes",
                png_bytes,
                b"invoice-bytes",
                b"cert-bytes",
            ][idx]
            assert on_disk.read_bytes() == original_body

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

    png_bytes = _make_png_bytes("RGB")

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
            png_bytes,
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

    back_path = result["attachments"][1]["storage_path"]
    assert back_path == f"{transaction_id}/ID_CARD_BACK.jpg"
    assert result["attachments"][1]["file_format"] == "JPG"
    back_on_disk = tmp_path / back_path
    assert back_on_disk.exists()
    with Image.open(back_on_disk) as im:
        assert im.format == "JPEG"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_png_conversion_failure_aborts_transaction(
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
                "filename": "back.png",
                "content_type": "image/png",
                "file_type": "ID_CARD_BACK",
                "file_format": "PNG",
            },
            b"not-a-real-png",
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

    with pytest.raises(ValueError, match="PNG conversion failed"):
        await service.create_transaction(request, files, customer_id="cust-3")

    assert not any(tmp_path.rglob("ID_CARD_BACK.*"))

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_rgba_png_composited_on_white(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    get_settings.cache_clear()

    service = TransactionService(db_session)
    service.storage.base_path = str(tmp_path)

    rgba_png = _make_rgba_png_with_transparent_corners()

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
                "filename": "back.png",
                "content_type": "image/png",
                "file_type": "ID_CARD_BACK",
                "file_format": "PNG",
            },
            rgba_png,
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

    result = await service.create_transaction(request, files, customer_id="cust-4")
    transaction_id = result["transaction_id"]
    back_path = result["attachments"][1]["storage_path"]
    assert back_path == f"{transaction_id}/ID_CARD_BACK.jpg"

    on_disk = tmp_path / back_path
    with Image.open(on_disk) as im:
        assert im.format == "JPEG"
        assert im.mode == "RGB"
        top_left = im.getpixel((0, 0))
        center = im.getpixel((32, 32))
        assert all(abs(c - 255) <= 30 for c in top_left), top_left
        assert center[0] > 150 and center[1] < 100 and center[2] < 100, center

    get_settings.cache_clear()


def _make_rgba_png_with_transparent_corners() -> bytes:
    img = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
    transparent = (255, 0, 0, 0)
    for x in range(20):
        for y in range(20):
            img.putpixel((x, y), transparent)
            img.putpixel((63 - x, y), transparent)
            img.putpixel((x, 63 - y), transparent)
            img.putpixel((63 - x, 63 - y), transparent)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
