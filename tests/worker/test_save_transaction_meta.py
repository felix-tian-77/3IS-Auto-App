import json
from pathlib import Path

from worker.file_downloader import FileDownloader


def test_save_transaction_meta_creates_file_with_expected_content(tmp_path):
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-0001"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13800138000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    assert out.exists(), f"expected {out} to exist"
    assert json.loads(out.read_text(encoding="utf-8")) == meta


def test_save_transaction_meta_writes_indented_ascii_safe_json(tmp_path):
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-0002"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13912345678",
        "business_type": "OLD_VEHICLE",
        "tax_exempt": False,
        "is_transfer": True,
    }
    fd.save_transaction_meta(txn_id, meta)
    raw = (Path(tmp_path) / txn_id / "transaction_meta.json").read_text(encoding="utf-8")
    assert "\n" in raw, "expected indented JSON (multi-line)"
    assert raw.count("\n") >= 4, "expected at least 4 newlines for 5 fields"


def test_save_transaction_meta_creates_txn_directory_if_missing(tmp_path):
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-0003"
    txn_dir = Path(tmp_path) / txn_id
    assert not txn_dir.exists()
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": None,
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    })
    assert txn_dir.is_dir()


def test_save_transaction_meta_overwrites_existing_file(tmp_path):
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-0004"
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": "111",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    })
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": "222",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": True,
        "is_transfer": True,
    })
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["holder_phone"] == "222"
    assert parsed["tax_exempt"] is True


def test_cleanup_removes_transaction_meta_file(tmp_path):
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-0005"
    fd.save_transaction_meta(txn_id, {
        "transaction_id": txn_id,
        "holder_phone": "13900000000",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    })
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    assert out.exists()
    fd.cleanup(txn_id)
    assert not out.exists(), "cleanup() should remove the meta file along with the txn dir"


def test_save_transaction_meta_includes_holder_phone_when_present(tmp_path):
    """holder_phone truthy values land in transaction_meta.json as the same string."""
    import json
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-PHONE"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": "13900001234",
        "business_type": "NEW_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["holder_phone"] == "13900001234"
    # Round-trip equality proves the full 5-field structure was written.
    assert parsed == meta


def test_save_transaction_meta_writes_null_when_holder_phone_is_none(tmp_path):
    """holder_phone=None is serialized as JSON null, NOT the string 'None' or empty string."""
    import json
    fd = FileDownloader(tmp_dir=str(tmp_path))
    txn_id = "T-META-NULL"
    meta = {
        "transaction_id": txn_id,
        "holder_phone": None,
        "business_type": "OLD_VEHICLE",
        "tax_exempt": False,
        "is_transfer": False,
    }
    fd.save_transaction_meta(txn_id, meta)
    out = Path(tmp_path) / txn_id / "transaction_meta.json"
    raw = out.read_text(encoding="utf-8")
    # JSON literal null must appear (not Python repr 'None' or empty string "").
    assert '"holder_phone": null' in raw or '"holder_phone":null' in raw, (
        f"expected JSON null for holder_phone, got: {raw!r}"
    )
    parsed = json.loads(raw)
    assert parsed["holder_phone"] is None
