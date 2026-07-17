from io import BytesIO
from typing import Optional

from PIL import Image

JPEG_QUALITY = 92
WHITE_BG = (255, 255, 255)


def png_to_jpeg_bytes(data: bytes) -> Optional[bytes]:
    try:
        with Image.open(BytesIO(data)) as im:
            if im.mode in ("RGBA", "LA") or (
                im.mode == "P" and "transparency" in im.info
            ):
                bg = Image.new("RGB", im.size, WHITE_BG)
                bg.paste(im.convert("RGBA"), mask=im.split()[-1])
                out = bg
            else:
                out = im.convert("RGB")
            buf = BytesIO()
            out.save(buf, format="JPEG", quality=JPEG_QUALITY)
            return buf.getvalue()
    except Exception:
        return None
