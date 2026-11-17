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

from PIL import Image


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
