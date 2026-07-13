from device_dispatcher import build_instruction


def _att(att_id: str, url: str, md5: str, fmt: str) -> dict:
    return {
        "attachment_id": att_id,
        "url": url,
        "md5": md5,
        "file_format": fmt,
    }


def test_build_instruction_lowercases_file_format_into_ext():
    atts = [
        _att("att_a", "https://x/a", "md5a", "JPG"),
        _att("att_b", "https://x/b", "md5b", "PDF"),
    ]
    instr = build_instruction("TXN-1", atts)
    assert instr["cmd"] == "DOWNLOAD_FILES"
    assert instr["params"]["transaction_id"] == "TXN-1"
    urls = instr["params"]["download_urls"]
    assert urls[0] == {
        "attachment_id": "att_a",
        "url": "https://x/a",
        "md5": "md5a",
        "ext": "jpg",
    }
    assert urls[1]["ext"] == "pdf"


def test_build_instruction_with_no_attachments_yields_empty_list():
    instr = build_instruction("TXN-empty", [])
    assert instr["params"]["download_urls"] == []
