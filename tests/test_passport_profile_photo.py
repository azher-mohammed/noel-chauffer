"""Tests for the passport-style driver profile photo.

Owner decision 2026-11-17 (chat): "Profile photo should be passport
photo jaisa rehna chahiye. Nake kuch bhi dadlo accept nahi karna.
Bas face proper dikhna, jaise ke uper driver app pe hai." — the
profile photo must stay passport-style, just anything must not be
accepted, and the face must show properly like the preview at the
top of the driver app. The owner picked the LIGHT option: shape/size
check + passport frame, NOT face detection.

Rules (profile photo only; other document photos keep today's
rules): portrait orientation (taller than wide, after EXIF
orientation) and at least 300px on the short side. The floor is
deliberately low so normal phone portrait photos pass, including
tall 9:16 shots. Shape/size only — no check of whether a face is
actually in the photo.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
import uuid

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-passport-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "passport-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOC_FILES = {
    "doc_dmv_license": "license.png",
    "doc_tlc_license": "tlc.png",
    "doc_fh1": "fh1.png",
    "doc_registration": "reg.png",
    "doc_inspection": "insp.png",
    "doc_vehicle_permit": "permit.png",
}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class PassportProfilePhotoCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, profile_bytes, profile_name="photo.jpg", docs=None):
        self._seq += 1
        data = {
            "name": "Passport Driver", "phone": f"+1555007{self._seq:04d}",
            "email": "passport@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"PP{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(profile_bytes), profile_name),
        }
        for field, fname in (docs or DOC_FILES).items():
            data[field] = (io.BytesIO(b"fake doc"), fname)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def driver_count(self):
        with app_module.app.app_context():
            return app_module.Driver.query.count()

    # -- server shape/size gate ----------------------------------------------
    def test_landscape_profile_photo_rejected(self):
        resp = self.register(photo_factory.jpeg(500, 400))
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        error = resp.get_json()["error"]
        self.assertIn("portrait", error)
        self.assertIn("passport-style", error)
        self.assertEqual(self.driver_count(), 0)

    def test_square_profile_photo_rejected(self):
        resp = self.register(photo_factory.jpeg(400, 400))
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("portrait", resp.get_json()["error"])
        self.assertEqual(self.driver_count(), 0)

    def test_too_small_profile_photo_rejected(self):
        resp = self.register(photo_factory.jpeg(200, 250))
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        error = resp.get_json()["error"]
        self.assertIn("too small", error)
        self.assertIn("300 pixels", error)
        self.assertEqual(self.driver_count(), 0)

    def test_unreadable_profile_photo_rejected(self):
        resp = self.register(b"\xff\xd8\xff fake")
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("could not be read", resp.get_json()["error"])
        self.assertEqual(self.driver_count(), 0)

    def test_boundary_300px_wide_accepted_299px_rejected(self):
        resp = self.register(photo_factory.jpeg(300, 375))
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        resp = self.register(photo_factory.jpeg(299, 374))
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("too small", resp.get_json()["error"])

    def test_valid_portrait_ratios_accepted(self):
        # 4:5, 3:4 and tall 9:16 phone shots must all pass.
        for width, height in [(400, 500), (600, 800), (720, 1280)]:
            with self.subTest(width=width, height=height):
                resp = self.register(photo_factory.jpeg(width, height))
                self.assertEqual(resp.status_code, 201,
                                 resp.get_data(as_text=True)[:200])
        self.assertEqual(self.driver_count(), 3)

    def test_exif_orientation_honoured(self):
        # Pixels stored landscape (500x400) with EXIF orientation 6
        # (rotate 90 CW) display as portrait 400x500: accepted.
        resp = self.register(photo_factory.jpeg(500, 400, exif_orientation=6))
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        # Pixels stored portrait (400x500) with orientation 6 display
        # as landscape 500x400: rejected — raw pixels must not decide.
        resp = self.register(photo_factory.jpeg(400, 500, exif_orientation=6))
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("portrait", resp.get_json()["error"])

    def test_other_document_photos_unaffected(self):
        # A landscape image as a document photo is fine; only the
        # profile photo has shape rules.
        docs = dict(DOC_FILES)
        resp = self.register(photo_factory.VALID_PROFILE_PHOTO, docs=docs)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        self._seq += 1
        data = {
            "name": "Doc Driver", "phone": f"+1555007{self._seq:04d}",
            "email": "doc@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"DD{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(photo_factory.png(800, 600)), "license.png"),
            "doc_tlc_license": (io.BytesIO(b"fake doc"), "tlc.png"),
            "doc_fh1": (io.BytesIO(b"fake doc"), "fh1.png"),
            "doc_registration": (io.BytesIO(b"fake doc"), "reg.png"),
            "doc_inspection": (io.BytesIO(b"fake doc"), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(b"fake doc"), "permit.png"),
        }
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])

    # -- passport frame everywhere -------------------------------------------
    def test_passport_frame_in_all_three_views(self):
        # Registration preview (the owner's reference) stays 140x175.
        driver_css = read("static/css/driver.css")
        m = re.search(r"\.doc-preview\.passport-preview img \{([^}]*)\}", driver_css)
        self.assertIsNotNone(m, "passport preview rule missing")
        self.assertIn("width: 140px", m.group(1))
        self.assertIn("height: 175px", m.group(1))
        self.assertIn("object-fit: cover", m.group(1))
        # Driver profile view: 4:5 portrait, not a round crop.
        m = re.search(r"\.profile-card img \{([^}]*)\}", driver_css)
        self.assertIsNotNone(m, "profile-card img rule missing")
        self.assertIn("width: 76px", m.group(1))
        self.assertIn("height: 95px", m.group(1))
        self.assertIn("object-fit: cover", m.group(1))
        self.assertNotIn("50%", m.group(1))
        # Customer driver card: 4:5 portrait, not a round crop.
        customer_css = read("static/css/customer.css")
        m = re.search(r"\.driver-card img \{([^}]*)\}", customer_css)
        self.assertIsNotNone(m, "customer driver-card img rule missing")
        self.assertIn("width: 84px", m.group(1))
        self.assertIn("height: 105px", m.group(1))
        self.assertIn("object-fit: cover", m.group(1))
        self.assertNotIn("50%", m.group(1))
        # Owner dashboard driver card: 4:5 portrait, not a round crop.
        owner_css = read("static/css/owner.css")
        m = re.search(r"\.driver-card img \{([^}]*)\}", owner_css)
        self.assertIsNotNone(m, "owner driver-card img rule missing")
        self.assertIn("width: 64px", m.group(1))
        self.assertIn("height: 80px", m.group(1))
        self.assertIn("object-fit: cover", m.group(1))
        self.assertNotIn("50%", m.group(1))

    def test_instruction_text_and_client_precheck(self):
        html = read("static/driver.html")
        self.assertIn("Passport-style photo", html)
        self.assertIn("face forward", html)
        self.assertIn("head and shoulders", html)
        self.assertIn("face clearly visible", html)
        js = read("static/js/driver.js")
        self.assertIn("checkProfilePhoto", js)
        # Client wording matches the server messages.
        self.assertIn("must be a portrait photo (taller than it is wide)", js)
        self.assertIn("too small", js)
        self.assertIn("at least 300 pixels wide", js)


if __name__ == "__main__":
    unittest.main()
