"""Copy stored driver photo BLOBs to the disk store, once.

Owner decision 2026-11-25: driver document/profile photos move out
of the Neon database to the Render persistent disk, so they stop
burning the 5 GB/month transfer allowance. Run this ONCE, after the
December 1, 2026 Neon reset makes the database reachable again — it
cannot run while the transfer quota is exhausted (every query
errors). The same copy is also available as the PIN-gated owner
endpoint POST /api/owner/migrate-photos-to-disk.

Run from the repo root with DATABASE_URL pointing at the live
database (Render shell, or a local shell with the Neon connection
string) and DRIVER_PHOTOS_DIR pointing at the disk mount
(/var/data/driver-photos on Render):

    python scripts/migrate_photos_to_disk.py

Idempotent and safe to re-run: rows whose file is already on disk
are skipped, rows whose path is set but whose file is missing are
re-written from the BLOB. BLOBs are NEVER deleted — the disk is the
fast path, the database stays the fallback copy.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


def main():
    with app_module.app.app_context():
        counts = app_module.migrate_photos_to_disk()
    print("migrated driver photos to disk: %s" % (counts,))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
