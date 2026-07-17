from io import BytesIO

from PIL import Image

from backend.services.image_convert import png_to_jpeg_bytes


def _make_png_bytes(mode: str, size=(2, 2)) -> bytes:
    buf = BytesIO()
    Image.new(mode, size, (200, 0, 0, 0) if mode == "RGBA" else (200, 0, 0)).save(
        buf, format="PNG"
    )
    return buf.getvalue()


def test_png_to_jpeg_bytes_returns_decodable_jpeg():
    png = _make_png_bytes("RGB")
    out = png_to_jpeg_bytes(png)
    assert out is not None
    with Image.open(BytesIO(out)) as im:
        assert im.format == "JPEG"
        assert im.mode == "RGB"


def test_png_to_jpeg_bytes_returns_none_for_corrupt_input():
    assert png_to_jpeg_bytes(b"not-a-real-png") is None
