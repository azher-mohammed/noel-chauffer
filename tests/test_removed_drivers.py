"""Tests for the owner dashboard "Removed drivers" list + Restore
(owner decision 2026-11-23, voice call): "if I remove drivers,
removed drivers should be there in [the] removed driver list" —
plus a Restore button per row ("List + restore button bhi").

Removal itself still hard-deletes the Driver row and every
DriverDocument row (ORM cascade), unlinks bookings and frees the
phone number. What is NEW here is the record left behind: at
removal time a RemovedDriver snapshot is taken (name, email, phone,
car, city/state, removed_at, original driver id), so the dashboard
shows removed drivers newest-first and the owner can restore one.

Restore re-creates the Driver row from the snapshot (same name,
phone, email, car). It FAILS cleanly with 409 if that phone or
email is registered to another driver by now — never overwriting
the other driver. Documents were deleted at removal and CANNOT
come back: the restored driver has NO documents and NO password —
he must re-upload all documents (the compulsory-document gate
blocks him from going available until then) and set a new password
via the forgot-password flow. Bookings stay unlinked. The snapshot
row is deleted on a successful restore. Drivers removed before
this shipped have no snapshot and stay gone.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import secrets
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-removed-drivers-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "removed_drivers.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "removed-drivers-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO_BYTES = photo_factory.VALID_PROFILE_PHOTO


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class RemovedDriversCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    # -- seed helpers ------------------------------------------------------
    def make_driver(self, name="Removed Driver", phone=None, email=None,
                    car_model="Cadillac CT6", car_year=2023,
                    car_colour="Black", plate=None, with_doc=False):
        self._seq += 1
        phone = phone or f"+1555040{self._seq:04d}"
        email = email if email is not None else f"rd{self._seq}@test.com"
        plate = plate or f"RD{self._seq:05d}"
        with app_module.app.app_context():
            d = app_module.Driver(
                name=name, phone=phone, email=email,
                state="New York", city="New York",
                car_model=car_model, car_year=car_year,
                vehicle_class="sedan", car_colour=car_colour,
                plate=plate, token=secrets.token_hex(16),
            )
            app_module.db.session.add(d)
            app_module.db.session.commit()
            if with_doc:
                app_module.db.session.add(app_module.DriverDocument(
                    driver_id=d.id, doc_type="dmv_license",
                    file=b"fake-doc-bytes", mime="image/jpeg",
                    original_name="dmv.jpg",
                    file_hash="ab" * 32,
                    expires_on=date(2030, 1, 1)))
                app_module.db.session.commit()
            return d.id

    def make_booking_for(self, driver_id):
        self._seq += 1
        with app_module.app.app_context():
            b = app_module.Booking(
                customer_name="Removed Drivers Customer",
                phone=f"+1555041{self._seq:04d}",
                email="removed@test.com", pickup="JFK Airport",
                dropoff="Times Square, New York",
                date="2026-11-23", time="12:00", ride_type="one_way",
                status="completed",
                fare_total=Decimal("100.00"),
                driver_earnings=Decimal("40.00"),
                accepted_driver_id=driver_id,
            )
            app_module.db.session.add(b)
            app_module.db.session.commit()
            return b.id

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def remove_driver(self, driver_id, pin="9999"):
        return self.client.post(
            f"/api/owner/drivers/{driver_id}/remove", json={"pin": pin})

    def removed_list(self):
        return self.client.get("/api/owner/removed-drivers")

    def restore(self, removed_id, pin="9999"):
        return self.client.post(
            f"/api/owner/removed-drivers/{removed_id}/restore",
            json={"pin": pin})

    # -- auth ---------------------------------------------------------------
    def test_list_requires_pin(self):
        resp = self.removed_list()
        self.assertEqual(resp.status_code, 401)

    def test_restore_requires_pin(self):
        did = self.make_driver()
        self.owner_login()
        resp = self.remove_driver(did)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        rid = self.removed_list().get_json()[0]["id"]
        # Not logged in at all: 401.
        fresh = app_module.app.test_client()
        resp = fresh.post(f"/api/owner/removed-drivers/{rid}/restore",
                          json={"pin": "9999"})
        self.assertEqual(resp.status_code, 401)
        # Logged in but wrong PIN: 401, snapshot still there.
        resp = self.restore(rid, pin="0000")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(len(self.removed_list().get_json()), 1)
        with app_module.app.app_context():
            self.assertIsNone(
                app_module.Driver.query.filter_by(phone="+15550400001").first())

    def test_restore_missing_snapshot_404(self):
        self.owner_login()
        resp = self.restore(9999)
        self.assertEqual(resp.status_code, 404)

    # -- snapshot on single remove ------------------------------------------
    def test_remove_single_creates_snapshot(self):
        did = self.make_driver(name="Single Removed", with_doc=True)
        self.owner_login()
        resp = self.remove_driver(did)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            self.assertIsNone(app_module.db.session.get(app_module.Driver, did))
            self.assertEqual(
                app_module.DriverDocument.query.filter_by(driver_id=did).count(), 0)
        resp = self.removed_list()
        self.assertEqual(resp.status_code, 200)
        rows = resp.get_json()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["original_driver_id"], did)
        self.assertEqual(row["removed_via"], "single")
        self.assertEqual(row["name"], "Single Removed")
        self.assertEqual(row["phone"], "+15550400001")
        self.assertEqual(row["email"], "rd1@test.com")
        self.assertEqual(row["state"], "New York")
        self.assertEqual(row["city"], "New York")
        self.assertEqual(row["car_model"], "Cadillac CT6")
        self.assertEqual(row["car_year"], 2023)
        self.assertEqual(row["car_colour"], "Black")
        self.assertEqual(row["plate"], "RD00001")
        self.assertTrue(row["removed_at"])

    # -- snapshot on bulk clear ---------------------------------------------
    def test_bulk_clear_snapshots_each_driver(self):
        self.make_driver(name="Bulk One")
        self.make_driver(name="Bulk Two")
        self.owner_login()
        resp = self.client.post("/api/owner/clear-drivers",
                                json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)
        rows = self.removed_list().get_json()
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["removed_via"] for r in rows}, {"bulk"})
        self.assertEqual({r["name"] for r in rows}, {"Bulk One", "Bulk Two"})

    # -- list ordering --------------------------------------------------------
    def test_list_newest_first(self):
        first = self.make_driver(name="Older Removed")
        second = self.make_driver(name="Newer Removed")
        self.owner_login()
        self.assertEqual(self.remove_driver(first).status_code, 200)
        self.assertEqual(self.remove_driver(second).status_code, 200)
        with app_module.app.app_context():
            rows = app_module.RemovedDriver.query.all()
            self.assertEqual(len(rows), 2)
            # Force distinct removed_at values: the newer removal is
            # the later one.
            rows[0].removed_at = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
            rows[1].removed_at = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
            app_module.db.session.commit()
        names = [r["name"] for r in self.removed_list().get_json()]
        self.assertEqual(names, ["Newer Removed", "Older Removed"])

    # -- restore --------------------------------------------------------------
    def test_restore_recreates_driver_no_docs_no_password(self):
        did = self.make_driver(name="Restore Me", with_doc=True)
        self.owner_login()
        self.assertEqual(self.remove_driver(did).status_code, 200)
        rid = self.removed_list().get_json()[0]["id"]
        resp = self.restore(rid)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["restored"])
        with app_module.app.app_context():
            # Snapshot row is gone.
            self.assertEqual(app_module.RemovedDriver.query.count(), 0)
            drivers = app_module.Driver.query.all()
            self.assertEqual(len(drivers), 1)
            d = drivers[0]
            self.assertEqual(d.name, "Restore Me")
            self.assertEqual(d.phone, "+15550400001")
            self.assertEqual(d.email, "rd1@test.com")
            self.assertEqual(d.car_model, "Cadillac CT6")
            self.assertEqual(d.car_year, 2023)
            self.assertEqual(d.car_colour, "Black")
            self.assertEqual(d.plate, "RD00001")
            self.assertEqual(d.state, "New York")
            self.assertEqual(d.city, "New York")
            # Documents do NOT come back, and there is no password:
            # the driver must re-upload documents and reset it.
            self.assertEqual(d.documents, [])
            self.assertIsNone(d.password_hash)
            self.assertFalse(d.available)
        # List is empty after restore.
        self.assertEqual(self.removed_list().get_json(), [])

    def test_restore_conflict_phone(self):
        did = self.make_driver(name="Phone Clash", phone="+15550409999",
                               email="clash@test.com")
        self.owner_login()
        self.assertEqual(self.remove_driver(did).status_code, 200)
        rid = self.removed_list().get_json()[0]["id"]
        # Someone else re-registers with the same phone.
        self.make_driver(name="New Owner Of Phone", phone="+15550409999",
                         email="other@test.com")
        resp = self.restore(rid)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("phone", resp.get_json()["error"])
        # Nothing changed: snapshot still there, only the new driver.
        self.assertEqual(len(self.removed_list().get_json()), 1)
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 1)
            self.assertEqual(app_module.Driver.query.first().name,
                             "New Owner Of Phone")

    def test_restore_conflict_email(self):
        did = self.make_driver(name="Email Clash", email="clash@test.com")
        self.owner_login()
        self.assertEqual(self.remove_driver(did).status_code, 200)
        rid = self.removed_list().get_json()[0]["id"]
        # Same email, different case and phone: still a conflict.
        self.make_driver(name="New Owner Of Email", email="CLASH@test.com")
        resp = self.restore(rid)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("email", resp.get_json()["error"])
        self.assertEqual(len(self.removed_list().get_json()), 1)

    def test_bookings_stay_unlinked_after_restore(self):
        did = self.make_driver(name="Linked Driver")
        bid = self.make_booking_for(did)
        self.owner_login()
        self.assertEqual(self.remove_driver(did).status_code, 200)
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, bid)
            self.assertIsNone(b.accepted_driver_id)
        rid = self.removed_list().get_json()[0]["id"]
        resp = self.restore(rid)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            # The booking is NOT re-linked to the restored driver.
            b = app_module.db.session.get(app_module.Booking, bid)
            self.assertIsNone(b.accepted_driver_id)
            self.assertEqual(app_module.Driver.query.count(), 1)

    def test_phone_freed_for_fresh_registration(self):
        self._seq += 1
        phone = f"+1555042{self._seq:04d}"
        email = f"rereg{self._seq}@test.com"
        did = self.make_driver(name="ReRegister", phone=phone, email=email)
        self.owner_login()
        self.assertEqual(self.remove_driver(did).status_code, 200)
        # The same phone registers fresh through the real endpoint.
        resp = self.client.post("/api/drivers/register", data={
            "name": "ReRegister Again", "phone": phone,
            "email": email,
            "car_model": "Cadillac CT6", "car_year": "2023",
            "car_colour": "Black", "plate": f"RR{self._seq:05d}",
            "state": "New York", "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
            "profile_photo": (io.BytesIO(PHOTO_BYTES), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(photo_factory.doc_photo()), "dmv.jpg"),
            "doc_tlc_license": (io.BytesIO(photo_factory.doc_photo()), "tlc.jpg"),
            "doc_fh1": (io.BytesIO(photo_factory.doc_photo()), "fh1.jpg"),
            "doc_registration": (io.BytesIO(photo_factory.doc_photo()), "reg.jpg"),
            "doc_inspection": (io.BytesIO(photo_factory.doc_photo()), "insp.jpg"),
            "doc_vehicle_permit": (io.BytesIO(photo_factory.doc_photo()), "permit.jpg"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])

    # -- dashboard markup -----------------------------------------------------
    def test_removed_section_markup(self):
        html = read("static/owner.html")
        self.assertIn("Removed drivers", html)
        self.assertIn('id="removed-feed"', html)
        self.assertIn('id="removed-count"', html)
        js = read("static/js/owner.js")
        self.assertIn("/api/owner/removed-drivers", js)
        self.assertIn("loadRemovedDrivers", js)
        self.assertIn("restoreRemovedDriver", js)
        # The Restore button itself is built in JS per row.
        self.assertIn("Restore driver", js)


if __name__ == "__main__":
    unittest.main()
