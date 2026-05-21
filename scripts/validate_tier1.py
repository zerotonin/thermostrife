#!/usr/bin/env python3
"""Run Tier-1 (meteostat) against every hand-verified row and produce a report.

Reads the curated CSV + event_geo.csv, calls `thermostrife.lookup.resolve`
for each row that has a non-NA ``day_temp_C`` (the validation set), and
writes a markdown report to ``reports/tier1_validation.md`` with manual
vs. resolved values, station IDs, and signed deltas.

Run from the repo root:

    python scripts/validate_tier1.py

Expected first-pass outcome (May 2026): ~10 of 13 rows resolve; misses are
pre-1920 events where meteostat coverage is thin (Paris 1871, Chicago 1919,
LAX 1965).  Discrepancies > 2 °C are flagged for manual station-hint
curation in Sprint 1.5.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from thermostrife.constants import CURATED_CSV, EVENT_GEO_CSV, REPORTS_DIR
from thermostrife.lookup import resolve

REPORT_PATH = REPORTS_DIR / "tier1_validation.md"


def run() -> pd.DataFrame:
    """Resolve every verified row and return the comparison frame."""
    warnings.filterwarnings("ignore")

    curated = pd.read_csv(CURATED_CSV).set_index("event_id")
    geo = pd.read_csv(EVENT_GEO_CSV).set_index("event_id")

    rows = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        manual = float(crow["day_temp_C"])
        when = pd.to_datetime(crow["start_date"]).date()
        res = resolve(grow["lat"], grow["lon"], when, radius_km=60)
        rows.append(
            {
                "event_id": event_id,
                "date": when.isoformat(),
                "manual_C": manual,
                "tier1_C": res.tmax_c,
                "delta_C": (res.tmax_c - manual) if res.tmax_c is not None else None,
                "station": res.source_id,
                "provenance": res.provenance,
                "note": res.note,
            }
        )
    return pd.DataFrame(rows)


def write_report(df: pd.DataFrame, out: Path = REPORT_PATH) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    n_total = len(df)
    n_resolved = df["tier1_C"].notna().sum()
    deltas = df["delta_C"].dropna()
    mae = deltas.abs().mean() if not deltas.empty else float("nan")
    median_abs = deltas.abs().median() if not deltas.empty else float("nan")
    within_05 = (deltas.abs() < 0.5).sum() if not deltas.empty else 0
    within_15 = (deltas.abs() < 1.5).sum() if not deltas.empty else 0

    with out.open("w") as f:
        f.write("# Tier-1 (meteostat) validation against hand-verified rows\n\n")
        f.write(f"- Validation set size: **{n_total}**\n")
        f.write(f"- Resolved at Tier 1: **{n_resolved} / {n_total}**\n")
        f.write(f"- MAE on resolved rows: **{mae:.2f} °C**\n")
        f.write(f"- Median |Δ| on resolved rows: **{median_abs:.2f} °C**\n")
        f.write(f"- Within 0.5 °C: **{within_05}** · within 1.5 °C: **{within_15}**\n\n")
        f.write("## Per-row results\n\n")
        f.write("| event_id | date | manual | Tier 1 | Δ | station | note |\n")
        f.write("|----------|------|-------:|-------:|--:|---------|------|\n")
        for _, r in df.iterrows():
            t1 = f"{r['tier1_C']:.1f}" if pd.notna(r["tier1_C"]) else "—"
            dl = f"{r['delta_C']:+.2f}" if pd.notna(r["delta_C"]) else "—"
            station = r["station"] or "—"
            note = r["note"]
            f.write(
                f"| `{r['event_id']}` | {r['date']} | {r['manual_C']:.1f} | {t1} "
                f"| {dl} | `{station}` | {note} |\n"
            )
        f.write("\n## Outliers (|Δ| > 2 °C)\n\n")
        outliers = df[df["delta_C"].abs() > 2.0]
        if outliers.empty:
            f.write("None.\n")
        else:
            for _, r in outliers.iterrows():
                f.write(
                    f"- `{r['event_id']}` ({r['date']}): manual {r['manual_C']:.1f} °C, "
                    f"Tier 1 {r['tier1_C']:.1f} °C at `{r['station']}` "
                    f"(Δ {r['delta_C']:+.2f} °C).\n"
                )
            f.write(
                "\nInvestigation actions: confirm the manual value's primary "
                "source, then either add a `station_hint` to `event_geo.csv` "
                "to pin the canonical station, or update the manual value in "
                "the curated CSV if the original citation does not survive "
                "scrutiny.\n"
            )


def main() -> int:
    df = run()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(REPORTS_DIR / "tier1_validation.csv", index=False)
    write_report(df)
    print(f"[done] {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
