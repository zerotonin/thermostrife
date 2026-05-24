#!/usr/bin/env python3
"""Sensitivity stratifications on the violent-uprisings panel.

Splits the resolved event set along four pre-registered axes and
re-fits the H2 case-crossover conditional-logit estimator per stratum:

- **Era**: era1_1750_1850 / era2_1850_1920 / era3_1920_1970 /
  era4_1970_2000 / era5_2000_2026 (matches the curated CSV's `era`
  column).
- **Hemisphere**: Northern vs Southern (event latitude sign).
- **Duration**: single-day (start == end) vs multi-day (> 1 day) vs
  long (> 3 days).
- **Event type**: civilian uprising vs military coup vs state-led
  massacre / genocide vs prison riot.  Heuristic on `event_name` /
  `notes` columns.

Writes ``reports/stratification.md`` plus a multi-row forest plot at
``reports/figs/forest_strata.{svg,png,csv}``.

Run from the repo root, ideally after the cascade cache is warm:

    python scripts/run_stratifications.py
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)

import pandas as pd  # noqa: E402

from thermostrife.constants import (  # noqa: E402
    CURATED_CSV,
    EVENT_GEO_CSV,
    REPORTS_DIR,
)
from thermostrife.inference import stratify_case_crossover  # noqa: E402
from thermostrife.lookup import resolve_event_anomaly  # noqa: E402
from thermostrife.viz import plot_forest_h2  # noqa: E402

REPORT_MD = REPORTS_DIR / "stratification.md"
REPORT_JSON = REPORTS_DIR / "stratification.json"
FIGS_DIR = REPORTS_DIR / "figs"


# ─────────────────────────────────────────────────────────────────
#  Event-type heuristic over the curated event_name / notes columns
# ─────────────────────────────────────────────────────────────────

COUP_KEYWORDS = (
    "putsch", "coup", "decembrist", "kapp", "beer hall", "blanqui",
)
MASSACRE_KEYWORDS = (
    "massacre", "genocide", "purge", "kristallnacht", "tlatelolco",
    "bloody sunday", "bibighar", "sharpeville", "hama",
    "warsaw ghetto", "rwandan", "shanghai", "mogadishu",
)
PRISON_KEYWORDS = (
    "prison", "penitentiary", "attica",
)


def classify_event_type(name: str, notes: str) -> str:
    blob = f"{name} {notes}".lower()
    if any(k in blob for k in PRISON_KEYWORDS):
        return "prison_riot"
    if any(k in blob for k in COUP_KEYWORDS):
        return "military_coup_or_putsch"
    if any(k in blob for k in MASSACRE_KEYWORDS):
        return "state_massacre_or_genocide"
    return "civilian_uprising_or_riot"


# ─────────────────────────────────────────────────────────────────
#  Build the resolved-event list with metadata for stratification
# ─────────────────────────────────────────────────────────────────


def build_events_with_meta() -> list[dict]:
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(CURATED_CSV).set_index("event_id")
    geo = pd.read_csv(EVENT_GEO_CSV).set_index("event_id")
    out = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        when = pd.to_datetime(crow["start_date"]).date()
        end = pd.to_datetime(crow["end_date"]).date()
        duration_days = max(1, (end - when).days + 1)
        r = resolve_event_anomaly(grow["lat"], grow["lon"], when, radius_km=60)
        if r.tmax_event_c is None or len(r.baseline) == 0:
            continue
        out.append({
            "event_id": event_id,
            "lat": float(grow["lat"]),
            "lon": float(grow["lon"]),
            "when": when,
            "tmax_event_c": float(r.tmax_event_c),
            "baseline": r.baseline,
            "provenance": r.provenance,
            "station_id": r.station_id,
            "era": crow.get("era", ""),
            "duration_days": int(duration_days),
            "event_type": classify_event_type(
                str(crow.get("event_name", "")),
                str(crow.get("notes", "")),
            ),
        })
    return out


# ─────────────────────────────────────────────────────────────────
#  Stratifier key functions
# ─────────────────────────────────────────────────────────────────


def key_era(e: dict) -> str:
    return e["era"] or "unknown"


def key_hemisphere(e: dict) -> str:
    return "Northern" if e["lat"] >= 0 else "Southern"


def key_duration_bin(e: dict) -> str:
    d = e["duration_days"]
    if d == 1:
        return "single_day"
    if d <= 3:
        return "short_multi_day_2_3"
    return "long_multi_day_4_plus"


def key_event_type(e: dict) -> str:
    return e["event_type"]


STRATIFIERS = {
    "Era": key_era,
    "Hemisphere": key_hemisphere,
    "Duration": key_duration_bin,
    "Event type": key_event_type,
}


# ─────────────────────────────────────────────────────────────────
#  Headline overall row for the forest plot
# ─────────────────────────────────────────────────────────────────


def overall_row(events: list[dict]) -> dict:
    from thermostrife.inference import (
        build_case_crossover_frame,
        case_crossover_conditional_logit,
    )
    frame = build_case_crossover_frame(events)
    res = case_crossover_conditional_logit(frame, covariates=[])
    res["n_events"] = len(events)
    return res


# ─────────────────────────────────────────────────────────────────
#  Report writers
# ─────────────────────────────────────────────────────────────────


def write_report(
    overall: dict,
    strata: dict[str, dict[str, dict]],
    out_md: Path,
) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with out_md.open("w") as f:
        f.write("# Stratified H2 case-crossover — sensitivity analysis\n\n")
        f.write(
            "All rows are independent re-fits of the conditional-logit "
            "case-crossover estimator restricted to the named stratum; "
            "the daylight covariate is dropped in stratified fits to "
            "avoid the collinearity it picks up at small n.\n\n"
        )

        f.write("## Headline (all resolved violent uprisings)\n\n")
        if not overall.get("skipped"):
            f.write(
                f"- OR per +1 °C: **{overall['or_per_C']:.3f}** "
                f"(95 % CI {overall['or_ci95_low']:.3f}–"
                f"{overall['or_ci95_high']:.3f})\n"
            )
            f.write(
                f"- one-sided p = **{overall['pvalue_one_sided']:.4g}**, "
                f"two-sided p = {overall['pvalue_two_sided']:.4g}\n"
            )
            f.write(
                f"- n events = {overall['n_events']}, "
                f"n rows = {overall['n_rows']}\n\n"
            )

        for axis_name, results in strata.items():
            f.write(f"## Stratified by {axis_name}\n\n")
            f.write(
                "| Stratum | n events | OR per +1 °C (95 % CI) "
                "| one-sided p |\n"
                "|---------|---------:|------------------------|"
                "------------:|\n"
            )
            for label, res in results.items():
                if res.get("skipped"):
                    f.write(
                        f"| {label} | {res.get('n_events', 0)} | "
                        f"— ({res.get('reason')}) | — |\n"
                    )
                    continue
                f.write(
                    f"| {label} | {res['n_events']} | "
                    f"{res['or_per_C']:.3f} "
                    f"({res['or_ci95_low']:.3f}–"
                    f"{res['or_ci95_high']:.3f}) "
                    f"| {res['pvalue_one_sided']:.4g} |\n"
                )
            f.write("\n")


def build_forest_rows(
    overall: dict,
    strata: dict[str, dict[str, dict]],
) -> list[dict]:
    """Order: overall on top, then stratifiers in turn (label-prefixed)."""
    rows: list[dict] = []
    if not overall.get("skipped"):
        rows.append({
            "label": "All resolved (n="
                     f"{overall['n_events']})",
            "or": overall["or_per_C"],
            "ci_low": overall["or_ci95_low"],
            "ci_high": overall["or_ci95_high"],
            "n": overall["n_events"],
        })
    for axis_name, results in strata.items():
        for label, res in results.items():
            if res.get("skipped"):
                continue
            rows.append({
                "label": f"{axis_name}: {label}",
                "or": res["or_per_C"],
                "ci_low": res["or_ci95_low"],
                "ci_high": res["or_ci95_high"],
                "n": res["n_events"],
            })
    # Forest plot draws bottom-up; reverse so the headline overall sits at top.
    rows.reverse()
    return rows


def main() -> int:
    events = build_events_with_meta()
    if not events:
        print("[stratification] no events resolved; aborting.")
        return 1

    print(f"[stratification] {len(events)} resolved events")
    overall = overall_row(events)
    strata = {
        axis: stratify_case_crossover(events, key_fn)
        for axis, key_fn in STRATIFIERS.items()
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = {
        "overall": overall,
        "strata": strata,
    }
    with REPORT_JSON.open("w") as f:
        json.dump(out_json, f, indent=2, default=str)
    write_report(overall, strata, REPORT_MD)

    forest_rows = build_forest_rows(overall, strata)
    plot_forest_h2(forest_rows, FIGS_DIR, stem="forest_strata")

    print(f"[done] {REPORT_MD}")
    print(f"[done] {REPORT_JSON}")
    print("[done] figs/forest_strata.{svg,png,csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
