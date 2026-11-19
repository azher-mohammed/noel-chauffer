"""Generate small valid images for registration fixtures.

The server enforces passport-style shape/size rules on the profile
photo (owner decision 2026-11-17), so registration fixtures must
upload real parseable images, not fake bytes. Other document uploads
keep accepting any bytes (extension check only).

Importable from every test module: unittest discover inserts the
tests/ directory into sys.path, and running a test file directly
does the same via sys.path[0].
"""

import io
import os
import random

from PIL import Image, ImageDraw


def doc_photo(width=800, height=600):
    """Return JPEG bytes of a distinct valid document photo.

    Every call returns DIFFERENT bytes (random base colour + random
    strokes), so a registration fixture that uploads one per document
    slot never trips the duplicate-file check, and two drivers
    registered by the same helper never share a file hash. High
    pixel variance, so it also passes the blank-photo check.
    """
    rnd = random.Random(int.from_bytes(os.urandom(8), "little"))
    img = Image.new("RGB", (width, height),
                    (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)))
    draw = ImageDraw.Draw(img)
    for _ in range(60):
        x0, y0 = rnd.randint(0, width - 1), rnd.randint(0, height - 1)
        x1, y1 = rnd.randint(0, width - 1), rnd.randint(0, height - 1)
        draw.line([(x0, y0), (x1, y1)],
                  fill=(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
                  width=rnd.randint(1, 6))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def doc_pdf():
    """Return bytes of a distinct minimal PDF (FH-1 accepts PDFs).

    Every call returns DIFFERENT bytes (random comment line), so
    fixtures never trip the duplicate-file check on the PDF.
    """
    rnd = random.Random(int.from_bytes(os.urandom(8), "little"))
    return ("%%PDF-1.4\n%% fixture %d\n1 0 obj\n<<>>\nendobj\n%%%%EOF\n"
            % rnd.randint(0, 10 ** 9)).encode("ascii")


def jpeg(width, height, color=(200, 30, 30), exif_orientation=None):
    """Return JPEG bytes of a solid image of the given pixel size.

    exif_orientation: if given, the pixels are stored as-is with that
    EXIF orientation tag (e.g. 6 = rotate 90 CW, the way phones store
    portrait shots taken sideways).
    """
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def png(width, height, color=(30, 60, 200)):
    """Return PNG bytes of a solid image of the given pixel size."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


# A valid profile photo: portrait, comfortably above the 300px floor.
VALID_PROFILE_PHOTO = jpeg(400, 500)
