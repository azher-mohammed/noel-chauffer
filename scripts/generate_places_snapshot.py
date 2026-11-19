"""Regenerate geo_places_snapshot.json from live Nominatim data.

Run from the repo root with the project venv (Nominatim must be
reachable from this machine — it is NOT reachable from Render's
shared egress IP, which is why the snapshot exists at all):

    ~/workspace/.venv-noel/bin/python scripts/generate_places_snapshot.py

Calls geo.search_places for each popular query (the same code path the
server uses, including airport terminal merging), paced at ~1.1s
between queries per Nominatim's usage policy, and writes the exact
search_places output to geo_places_snapshot.json. Queries that return
no live results are skipped with a warning (they keep working through
live search / the Photon fallback). Nothing is invented: every entry
is a real Nominatim response.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module

OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "geo_places_snapshot.json",
)


def main():
    queries = {}
    skipped = []
    for query in geo_module._POPULAR_SEARCH_QUERIES:
        # Bypass any cache so the snapshot is fresh live data.
        geo_module._search_cache.pop((query.lower(), 5), None)
        try:
            results = geo_module.search_places(query, 5)
        except Exception as exc:  # never crash the generator
            print(f"SKIP {query!r}: {exc}")
            skipped.append(query)
            time.sleep(1.1)
            continue
        if not results:
            print(f"SKIP {query!r}: live search returned no results")
            skipped.append(query)
        else:
            queries[query.lower()] = {"results": results}
            names = [r["display_name"].split(",")[0] for r in results]
            print(f"OK   {query!r}: {len(results)} results: {names}")
        time.sleep(1.1)
    payload = {
        "generated": time.strftime("%Y-%m-%d"),
        "source": "Nominatim via geo.search_places (see scripts/generate_places_snapshot.py)",
        "notes": "Regenerate with: ~/workspace/.venv-noel/bin/python scripts/generate_places_snapshot.py",
        "queries": queries,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUT_PATH}: {len(queries)} queries, skipped: {skipped or 'none'}")


if __name__ == "__main__":
    main()
