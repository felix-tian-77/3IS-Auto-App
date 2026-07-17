import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from file_downloader import FileDownloader, URLExpiredError


def _make_file(tmp_path, name, content):
    p = tmp_path / name
    p.write_bytes(content)
    return p


def test_download_success_md5_ok(tmp_path):
    content = b"hello world"
    md5 = hashlib.md5(content).hexdigest()
    downloader = FileDownloader(str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content = MagicMock(return_value=[content])
    mock_resp.raise_for_status = MagicMock()

    with patch("file_downloader.requests.get", return_value=mock_resp):
        result = downloader.download(
            url="http://example.com/file.jpg",
            attachment_id="att_001",
            transaction_id="TXN-001",
            expected_md5=md5,
            filename="ID_CARD_FRONT.jpg",
        )

    assert result.md5_ok is True
    assert result.attachment_id == "att_001"
    assert result.filename == "ID_CARD_FRONT.jpg"
    assert result.local_path == str(tmp_path / "TXN-001" / "ID_CARD_FRONT.jpg")
    assert os.path.exists(result.local_path)
    assert Path(result.local_path).read_bytes() == content


def test_download_md5_mismatch_deletes_file(tmp_path):
    content = b"hello world"
    wrong_md5 = "0" * 32
    downloader = FileDownloader(str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content = MagicMock(return_value=[content])
    mock_resp.raise_for_status = MagicMock()

    with patch("file_downloader.requests.get", return_value=mock_resp):
        result = downloader.download(
            url="http://example.com/file.jpg",
            attachment_id="att_002",
            transaction_id="TXN-002",
            expected_md5=wrong_md5,
            ext="jpg",
        )

    assert result.md5_ok is False
    assert not os.path.exists(result.local_path)


def test_download_url_expired_raises(tmp_path):
    downloader = FileDownloader(str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.close = MagicMock()

    with patch("file_downloader.requests.get", return_value=mock_resp):
        with pytest.raises(URLExpiredError):
            downloader.download(
                url="http://example.com/file.jpg",
                attachment_id="att_003",
                transaction_id="TXN-003",
                expected_md5="abc",
                ext="jpg",
            )


def test_verify_md5_correct(tmp_path):
    content = b"test data"
    md5 = hashlib.md5(content).hexdigest()
    f = _make_file(tmp_path, "test.bin", content)
    downloader = FileDownloader(str(tmp_path))
    assert downloader.verify_md5(str(f), md5) is True


def test_verify_md5_incorrect(tmp_path):
    content = b"test data"
    f = _make_file(tmp_path, "test.bin", content)
    downloader = FileDownloader(str(tmp_path))
    assert downloader.verify_md5(str(f), "0" * 32) is False


def test_download_all_serial(tmp_path):
    content_a = b"file A"
    content_b = b"file B"
    md5_a = hashlib.md5(content_a).hexdigest()
    md5_b = hashlib.md5(content_b).hexdigest()
    downloader = FileDownloader(str(tmp_path))

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "url-a" in url:
            resp.iter_content = MagicMock(return_value=[content_a])
        else:
            resp.iter_content = MagicMock(return_value=[content_b])
        return resp

    signed_urls = [
        {
            "attachment_id": "att_a",
            "url": "http://url-a",
            "md5": md5_a,
            "file_format": "JPG",
            "filename": "ID_CARD_FRONT.jpg",
        },
        {
            "attachment_id": "att_b",
            "url": "http://url-b",
            "md5": md5_b,
            "file_format": "PDF",
            "filename": "CERTIFICATE.pdf",
        },
    ]

    with patch("file_downloader.requests.get", side_effect=mock_get):
        results = downloader.download_all(signed_urls, "TXN-ALL")

    assert len(results) == 2
    assert all(r.md5_ok for r in results)
    assert results[0].attachment_id == "att_a"
    assert results[1].attachment_id == "att_b"
    assert results[0].filename == "ID_CARD_FRONT.jpg"
    assert results[1].filename == "CERTIFICATE.pdf"
    assert results[0].local_path == str(tmp_path / "TXN-ALL" / "ID_CARD_FRONT.jpg")
    assert results[1].local_path == str(tmp_path / "TXN-ALL" / "CERTIFICATE.pdf")


def test_download_all_stops_on_md5_failure(tmp_path):
    content_a = b"file A"
    wrong_md5 = "0" * 32
    downloader = FileDownloader(str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content = MagicMock(return_value=[content_a])
    mock_resp.raise_for_status = MagicMock()

    signed_urls = [
        {"attachment_id": "att_a", "url": "http://url-a", "md5": wrong_md5, "file_format": "JPG"},
        {"attachment_id": "att_b", "url": "http://url-b", "md5": "x", "file_format": "PDF"},
    ]

    with patch("file_downloader.requests.get", return_value=mock_resp):
        results = downloader.download_all(signed_urls, "TXN-FAIL")

    assert len(results) == 1
    assert results[0].md5_ok is False


def test_download_all_rejects_unsafe_filename(tmp_path):
    downloader = FileDownloader(str(tmp_path))

    with patch("file_downloader.requests.get") as mock_get:
        results = downloader.download_all([
            {
                "attachment_id": "att_unsafe",
                "url": "http://url-unsafe",
                "md5": "0" * 32,
                "filename": "../escape.jpg",
            }
        ], "TXN-UNSAFE")

    assert len(results) == 1
    assert results[0].md5_ok is False
    assert results[0].filename == ""
    assert results[0].local_path == ""
    mock_get.assert_not_called()
    assert not (tmp_path / "escape.jpg").exists()
    assert not (tmp_path / "TXN-UNSAFE").exists()


def test_download_all_rejects_filename_with_nul_byte(tmp_path):
    downloader = FileDownloader(str(tmp_path))

    with patch("file_downloader.requests.get") as mock_get:
        results = downloader.download_all([
            {
                "attachment_id": "att_nul",
                "url": "http://url-nul",
                "md5": "0" * 32,
                "filename": "safe\x00.jpg",
            }
        ], "TXN-NUL")

    assert len(results) == 1
    assert results[0].md5_ok is False
    assert results[0].filename == ""
    assert results[0].local_path == ""
    mock_get.assert_not_called()
    assert not (tmp_path / "TXN-NUL").exists()


def test_download_all_uses_legacy_filename_when_missing(tmp_path):
    content = b"legacy file"
    md5 = hashlib.md5(content).hexdigest()
    downloader = FileDownloader(str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content = MagicMock(return_value=[content])
    mock_resp.raise_for_status = MagicMock()

    with patch("file_downloader.requests.get", return_value=mock_resp):
        results = downloader.download_all([
            {
                "attachment_id": "att_legacy",
                "url": "http://url-legacy",
                "md5": md5,
                "file_format": "JPG",
            }
        ], "TXN-LEGACY")

    assert results[0].filename == "att_legacy.jpg"
    assert results[0].local_path == str(tmp_path / "TXN-LEGACY" / "att_legacy.jpg")


def test_cleanup_removes_transaction_dir(tmp_path):
    txn_dir = tmp_path / "TXN-CLEAN"
    txn_dir.mkdir()
    (txn_dir / "file.jpg").write_bytes(b"data")

    downloader = FileDownloader(str(tmp_path))
    downloader.cleanup("TXN-CLEAN")

    assert not txn_dir.exists()


def test_save_transaction_meta_writes_customer_phone(tmp_path):
    """save_transaction_meta persists customer_phone into the JSON file."""
    downloader = FileDownloader(str(tmp_path))
    downloader.save_transaction_meta(
        "T-1",
        {
            "transaction_id": "T-1",
            "holder_phone": "13800138000",
            "customer_phone": "13900139000",
            "business_type": "NEW_VEHICLE",
            "tax_exempt": False,
            "is_transfer": False,
        },
    )
    meta_path = tmp_path / "T-1" / "transaction_meta.json"
    with open(meta_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["customer_phone"] == "13900139000"
    assert data["holder_phone"] == "13800138000"
