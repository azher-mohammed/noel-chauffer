"""Tests for driver photos on the Render disk instead of the database.

Owner decision 2026-11-25 (voice call, "Haan"): driver document and
profile photos move out of the Neon database to the persistent disk
declared in render.yaml, because re-serving the photo BLOBs from the
database burned the Neon Free 5 GB/month transfer allowance in two
days (the whole database is only 35 MB; the photos are 22 MB of it).
Booking/accept rows are tiny and untouched.

Pinned here:
- new uploads land on disk (path recorded, file bytes match) AND the
  DB BLOB stays as the fallback copy;
- photo endpoints serve from disk first (the BLOB can be nulled and
  the photo still serves) and fall back to the BLOB for rows stored
  before the disk existed;
- photo responses carry long public caching, and the BLOB fallback
  answers 304 on a matching If-None-Match;
- re-upload writes the new bytes to disk;
- the migration copies BLOBs to disk without deleting them, and a
  second run is a no-op;
- a disk failure never breaks registration;
- render.yaml declares the disk.

Run:  python -m unittest tests.test_driver_photos_out_of_db -v
"""

import hashlib
import io
import os
import sys
import tempfile
import unittest
import uuid
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-photos-disk-")
_photos_dir = os.path.join(_tmpdir, "photos")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "photos-disk-secret-key"
os.environ["DRIVER_PHOTOS_DIR"] = _photos_dir
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_tlc_license", "TLC License", "tlc.png"),
    ("doc_fh1", "FH-1 Insurance Card", "fh1.png"),
    ("doc_registration", "Commercial Vehicle Registration", "reg.png"),
    ("doc_inspection", "NYS DMV Inspection", "insp.png"),
    ("doc_vehicle_permit", "TLC-for-hire Vehicle Permit", "permit.png"),
]


class PhotosOutOfDbCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0
        self._profile_bytes = photo_factory.VALID_PROFILE_PHOTO

    # -- helpers -------------------------------------------------------------
    def register(self, phone_suffix=1):
        self._seq += 1
        data = {
            "name": "Photo Driver", "phone": f"+1555010{phone_suffix:04d}",
            "email": "photo@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"PH{self._seq:05d}",
            "state": "New York", "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
        }
        files = {}
        for field, _label, fname in FIELDS:
            payload = (self._profile_bytes if field == "profile_photo"
                       else photo_factory.doc_photo())
            files[field] = (io.BytesIO(payload), fname)
        data.update(files)
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        return resp.get_json()["driver"], resp.get_json()["token"]

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def driver_row(self, driver_id):
        with app_module.app.app_context():
            return app_module.db.session.get(app_module.Driver, driver_id)

    def doc_row(self, driver_id, doc_type):
        with app_module.app.app_context():
            return (app_module.DriverDocument.query
                    .filter_by(driver_id=driver_id, doc_type=doc_type).first())

    def seed_booking(self, driver_id):
        with app_module.app.app_context():
            booking = app_module.Booking(
                customer_name="Photo Customer", phone="+15550009999",
                email="cust@test.com", pickup="1 Test Way",
                dropoff="2 Test Ave", date="2030-06-01", time="12:00",
                ride_type="one_way", accepted_driver_id=driver_id,
                fare_total=Decimal("154.78"), fare=Decimal("139.29"),
                driver_earnings=Decimal("102.46"), tax=Decimal("12.01"))
            app_module.db.session.add(booking)
            app_module.db.session.commit()
            return booking.id

    def strip_to_pre_migration(self, driver_id):
        """Forget every disk path, keeping the BLOBs — the shape of a
        row stored before the disk existed."""
        with app_module.app.app_context():
            driver = app_module.db.session.get(app_module.Driver, driver_id)
            driver.profile_photo_path = None
            driver.profile_photo_hash = None
            for doc in driver.documents:
                doc.file_path = None
            app_module.db.session.commit()

    # -- new uploads land on disk, BLOB stays as fallback -------------------
    def test_registration_uploads_land_on_disk(self):
        driver, _token = self.register()
        row = self.driver_row(driver["id"])
        self.assertTrue(row.profile_photo_path.startswith("profile/"))
        self.assertEqual(row.profile_photo_hash,
                         hashlib.sha256(self._profile_bytes).hexdigest())
        disk_path = os.path.join(_photos_dir, row.profile_photo_path)
        with open(disk_path, "rb") as fh:
            self.assertEqual(fh.read(), self._profile_bytes)
        # The BLOB is still stored as the fallback copy.
        self.assertEqual(row.profile_photo, self._profile_bytes)
        for field, _label, _fname in FIELDS[1:]:
            doc_type = {"doc_dmv_license": "dmv_license",
                        "doc_tlc_license": "tlc_license",
                        "doc_fh1": "fh1_insurance",
                        "doc_registration": "registration",
                        "doc_inspection": "inspection",
                        "doc_vehicle_permit": "vehicle_permit"}[field]
            doc = self.doc_row(driver["id"], doc_type)
            self.assertIsNotNone(doc, doc_type)
            self.assertTrue(doc.file_path.startswith("docs/"),
                            doc.file_path)
            with open(os.path.join(_photos_dir, doc.file_path), "rb") as fh:
                self.assertEqual(fh.read(), doc.file)

    # -- photo endpoints: disk first, BLOB fallback, caching ----------------
    def test_booking_driver_photo_served_from_disk(self):
        driver, _token = self.register()
        booking_id = self.seed_booking(driver["id"])
        resp = self.client.get(f"/api/bookings/{booking_id}/driver-photo")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, self._profile_bytes)
        self.assertIn("public", resp.headers.get("Cache-Control", ""))
        self.assertIn("max-age=31536000", resp.headers.get("Cache-Control", ""))
        self.assertIn("immutable", resp.headers.get("Cache-Control", ""))
        self.assertTrue(resp.headers.get("ETag"))
        # Null the BLOB: the photo still serves, from disk.
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Driver, driver["id"])
            row.profile_photo = None
            app_module.db.session.commit()
        resp = self.client.get(f"/api/bookings/{booking_id}/driver-photo")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, self._profile_bytes)

    def test_booking_driver_photo_db_fallback_and_304(self):
        driver, _token = self.register()
        self.strip_to_pre_migration(driver["id"])
        booking_id = self.seed_booking(driver["id"])
        resp = self.client.get(f"/api/bookings/{booking_id}/driver-photo")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, self._profile_bytes)
        self.assertIn("max-age=31536000", resp.headers.get("Cache-Control", ""))
        etag = resp.headers.get("ETag")
        self.assertEqual(etag, '"%s"' % hashlib.sha256(
            self._profile_bytes).hexdigest())
        resp = self.client.get(f"/api/bookings/{booking_id}/driver-photo",
                               headers={"If-None-Match": etag})
        self.assertEqual(resp.status_code, 304)
        self.assertEqual(resp.data, b"")

    def test_booking_driver_photo_404_when_no_photo(self):
        driver, _token = self.register()
        self.strip_to_pre_migration(driver["id"])
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Driver, driver["id"])
            row.profile_photo = None
            app_module.db.session.commit()
        booking_id = self.seed_booking(driver["id"])
        resp = self.client.get(f"/api/bookings/{booking_id}/driver-photo")
        self.assertEqual(resp.status_code, 404)

    def test_owner_document_disk_first_and_fallback(self):
        driver, _token = self.register()
        self.owner_login()
        doc = self.doc_row(driver["id"], "dmv_license")
        original = doc.file
        resp = self.client.get(f"/api/owner/documents/{doc.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, original)
        self.assertIn("max-age=31536000", resp.headers.get("Cache-Control", ""))
        # Empty out the BLOB: the document still serves, from disk.
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.DriverDocument, doc.id)
            row.file = b""
            app_module.db.session.commit()
        resp = self.client.get(f"/api/owner/documents/{doc.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, original)

    def test_owner_document_db_fallback_and_304(self):
        driver, _token = self.register()
        self.strip_to_pre_migration(driver["id"])
        self.owner_login()
        doc = self.doc_row(driver["id"], "dmv_license")
        resp = self.client.get(f"/api/owner/documents/{doc.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, doc.file)
        etag = resp.headers.get("ETag")
        self.assertEqual(etag, '"%s"' % doc.file_hash)
        resp = self.client.get(f"/api/owner/documents/{doc.id}",
                               headers={"If-None-Match": etag})
        self.assertEqual(resp.status_code, 304)

    def test_owner_driver_photo_endpoint(self):
        driver, _token = self.register()
        resp = self.client.get(f"/api/owner/drivers/{driver['id']}/photo")
        self.assertEqual(resp.status_code, 401)
        self.owner_login()
        resp = self.client.get(f"/api/owner/drivers/{driver['id']}/photo")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, self._profile_bytes)
        self.assertIn("max-age=31536000", resp.headers.get("Cache-Control", ""))

    # -- re-upload writes the new bytes to disk ------------------------------
    def test_reupload_updates_disk_path(self):
        driver, token = self.register()
        old = self.doc_row(driver["id"], "dmv_license")
        old_path = old.file_path
        new_bytes = photo_factory.doc_photo()
        resp = self.client.post(
            "/api/drivers/me/documents",
            data={"doc_type": "dmv_license",
                  "expiry_dmv_license": "2031-01-01",
                  "document": (io.BytesIO(new_bytes), "new-license.jpg")},
            content_type="multipart/form-data",
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:300])
        new = self.doc_row(driver["id"], "dmv_license")
        self.assertNotEqual(new.file_path, old_path)
        self.assertEqual(new.file, new_bytes)
        with open(os.path.join(_photos_dir, new.file_path), "rb") as fh:
            self.assertEqual(fh.read(), new_bytes)
        self.owner_login()
        resp = self.client.get(f"/api/owner/documents/{new.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, new_bytes)

    # -- migration copies BLOBs to disk without deleting them ----------------
    def test_migrate_photos_to_disk_copies_without_deleting(self):
        driver, _token = self.register()
        self.strip_to_pre_migration(driver["id"])
        with app_module.app.app_context():
            counts = app_module.migrate_photos_to_disk()
        self.assertEqual(counts["documents_copied"], 6)
        self.assertEqual(counts["profiles_copied"], 1)
        self.assertEqual(counts["already_on_disk"], 0)
        self.assertEqual(counts["failed"], 0)
        row = self.driver_row(driver["id"])
        self.assertTrue(row.profile_photo_path.startswith("profile/"))
        self.assertEqual(row.profile_photo, self._profile_bytes)
        with open(os.path.join(_photos_dir, row.profile_photo_path),
                  "rb") as fh:
            self.assertEqual(fh.read(), self._profile_bytes)
        with app_module.app.app_context():
            docs = list(app_module.db.session.get(
                app_module.Driver, driver["id"]).documents)
        for doc in docs:
            self.assertTrue(doc.file_path.startswith("docs/"))
            with open(os.path.join(_photos_dir, doc.file_path), "rb") as fh:
                self.assertEqual(fh.read(), doc.file)
        # A second run is a no-op.
        with app_module.app.app_context():
            counts = app_module.migrate_photos_to_disk()
        self.assertEqual(counts["documents_copied"], 0)
        self.assertEqual(counts["profiles_copied"], 0)
        self.assertEqual(counts["already_on_disk"], 7)
        self.assertEqual(counts["failed"], 0)

    def test_migrate_endpoint_requires_owner(self):
        driver, _token = self.register()
        self.strip_to_pre_migration(driver["id"])
        resp = self.client.post("/api/owner/migrate-photos-to-disk")
        self.assertEqual(resp.status_code, 401)
        self.owner_login()
        resp = self.client.post("/api/owner/migrate-photos-to-disk")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["migrated"])
        self.assertEqual(body["documents_copied"], 6)
        self.assertEqual(body["profiles_copied"], 1)

    # -- disk failure never breaks registration ------------------------------
    def test_disk_failure_does_not_break_registration(self):
        blocker = os.path.join(_tmpdir, "blocker")
        with open(blocker, "wb") as fh:
            fh.write(b"not a directory")
        original = app_module.DRIVER_PHOTOS_DIR
        app_module.DRIVER_PHOTOS_DIR = os.path.join(blocker, "photos")
        try:
            driver, _token = self.register(phone_suffix=7)
        finally:
            app_module.DRIVER_PHOTOS_DIR = original
        row = self.driver_row(driver["id"])
        self.assertIsNone(row.profile_photo_path)
        self.assertEqual(row.profile_photo, self._profile_bytes)
        doc = self.doc_row(driver["id"], "dmv_license")
        self.assertIsNone(doc.file_path)
        self.assertTrue(doc.file)

    # -- owner drivers list stays metadata-only ------------------------------
    def test_owner_drivers_list_stays_metadata_only(self):
        driver, _token = self.register()
        self.owner_login()
        resp = self.client.get("/api/owner/drivers")
        self.assertEqual(resp.status_code, 200)
        rows = resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["docs"]["profile_picture"], "completed")
        self.assertEqual(set(rows[0]["doc_ids"]), {
            "dmv_license", "tlc_license", "fh1_insurance", "registration",
            "inspection", "vehicle_permit"})
        self.assertNotIn("profile_photo", rows[0])

    # -- render.yaml declares the disk ----------------------------------------
    def test_render_yaml_declares_photo_disk(self):
        with open(os.path.join(REPO_DIR, "render.yaml"),
                  encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("plan: starter", text)
        self.assertIn("disk:", text)
        self.assertIn("name: driver-photos", text)
        self.assertIn("mountPath: /var/data/driver-photos", text)
        self.assertIn("sizeGB: 1", text)
        self.assertIn("DRIVER_PHOTOS_DIR", text)


if __name__ == "__main__":
    unittest.main()
