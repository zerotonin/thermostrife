#!/usr/bin/env python3
"""Expand data/raw/event_geo.csv to cover every event via geopy Nominatim.

For each row in ``data/raw/uprisings_temperature.csv`` that is not yet
present in ``data/raw/event_geo.csv``, this script geocodes the
(``city``, ``country``) pair via OpenStreetMap's Nominatim and appends
the result.  Hand-curated rows (the 13 verified events) are preserved
verbatim.

Nominatim's anonymous-use policy caps traffic at 1 request per second
and requires a descriptive ``User-Agent``.  Responses are cached in
``scripts/.geocode_cache.json`` so re-runs are free.

Run from the repo root:

    python scripts/build_geo_map.py

Spot-check the new rows in ``event_geo.csv`` afterwards — Nominatim
occasionally resolves to a same-name town in another country
(e.g. "Springfield, USA"), which a manual review catches in seconds.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Nominatim
from tqdm import tqdm

from thermostrife.constants import (
    CURATED_CSV,
    EVENT_GEO_CSV,
    PEACEFUL_CSV,
    PEACEFUL_GEO_CSV,
)

CACHE_PATH = Path(__file__).resolve().parent / ".geocode_cache.json"
USER_AGENT = "thermostrife-build-geo-map/0.1 (bart.geurten@otago.ac.nz)"
NOMINATIM_PAUSE_S = 1.1  # Nominatim policy: <=1 req/s; pad a touch for safety


def load_cache() -> dict[str, dict]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def geocode(geolocator: Nominatim, city: str, country: str, cache: dict) -> dict:
    """Return ``{lat, lon, display_name}`` for ``(city, country)``."""
    key = f"{city}|{country}"
    if key in cache:
        return cache[key]
    query = f"{city}, {country}"
    try:
        loc = geolocator.geocode(query, timeout=15)
    except GeocoderTimedOut:
        time.sleep(2)
        loc = geolocator.geocode(query, timeout=30)
    if loc is None:
        cache[key] = {"lat": None, "lon": None, "display_name": None}
    else:
        cache[key] = {
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "display_name": loc.address,
        }
    time.sleep(NOMINATIM_PAUSE_S)
    return cache[key]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_geo_map",
        description="Expand a geo CSV to cover every event from a curated CSV.",
    )
    parser.add_argument(
        "--panel", choices=("violent", "peaceful"), default="violent",
        help="Which panel to geocode (default: violent uprisings).",
    )
    parser.add_argument("--input", type=Path, default=None,
                        help="Override input curated CSV.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Override output geo CSV.")
    args = parser.parse_args(argv)

    if args.panel == "peaceful":
        input_csv = args.input or PEACEFUL_CSV
        output_csv = args.output or PEACEFUL_GEO_CSV
    else:
        input_csv = args.input or CURATED_CSV
        output_csv = args.output or EVENT_GEO_CSV

    curated = pd.read_csv(input_csv)
    existing = (
        pd.read_csv(output_csv)
        if output_csv.exists()
        else pd.DataFrame(columns=["event_id", "lat", "lon", "note"])
    )
    have = set(existing["event_id"])
    missing = curated[~curated["event_id"].isin(have)]
    if missing.empty:
        print(f"[done] {output_csv.name} already covers all {len(curated)} events.")
        return 0

    print(f"[start] geocoding {len(missing)} new events from {input_csv.name} via Nominatim …")
    cache = load_cache()
    geolocator = Nominatim(user_agent=USER_AGENT)

    new_rows = []
    bad = []
    try:
        for _, row in tqdm(missing.iterrows(), total=len(missing)):
            res = geocode(geolocator, str(row["city"]), str(row["country"]), cache)
            if res["lat"] is None:
                bad.append(row["event_id"])
                continue
            new_rows.append(
                {
                    "event_id": row["event_id"],
                    "lat": round(res["lat"], 4),
                    "lon": round(res["lon"], 4),
                    "note": f"Nominatim: {res['display_name']}",
                }
            )
    finally:
        save_cache(cache)

    out = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
    out = out.drop_duplicates(subset="event_id", keep="first").sort_values("event_id")
    out.to_csv(output_csv, index=False)
    print(f"[done] wrote {len(out)} rows to {output_csv}")
    if bad:
        print(f"[warn] {len(bad)} events failed to geocode: {bad}")
        print(f"       hand-curate these in {output_csv} and re-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
