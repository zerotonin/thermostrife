#!/usr/bin/env python3
"""End-to-end inference on the resolved-event cascade output.

For every row in ``data/raw/event_geo.csv``, this script:

1. Calls ``thermostrife.lookup.resolve_event_anomaly`` to obtain
   the single-source (event_day, baseline_window) pair.
2. Builds the long case-crossover frame
   (``thermostrife.inference.build_case_crossover_frame``).
3. Runs the three pre-registered tests:

   - **H1** Wilcoxon signed-rank + sign test + bootstrap CI on the
     per-event anomalies.
   - **H2** Conditional-logit case-crossover with the ``daylight_h``
     covariate; reports OR per °C and one- and two-sided p-values.
   - **H2-perm** Stratified permutation test as a non-parametric
     backup.
   - **σ-rescaled** Burke-2015-style 1 σ effect for cross-study
     comparison.

4. Writes ``reports/inference_results.{md,json}``.

Run from the repo root:

    python scripts/run_inference.py
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from thermostrife.constants import CURATED_CSV, EVENT_GEO_CSV, REPORTS_DIR
from thermostrife.inference import (
    bootstrap_mean_ci,
    build_case_crossover_frame,
    case_crossover_conditional_logit,
    hsiang_sigma_rescaled,
    sign_test,
    stratified_permutation,
    wilcoxon_signed_rank,
)
from thermostrife.lookup import resolve_event_anomaly

REPORT_MD = REPORTS_DIR / "inference_results.md"
REPORT_JSON = REPORTS_DIR / "inference_results.json"


def build_events() -> list[dict]:
    """Resolve every event in event_geo.csv into an inference-ready dict."""
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(CURATED_CSV).set_index("event_id")
    geo = pd.read_csv(EVENT_GEO_CSV).set_index("event_id")
    out = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        when = pd.to_datetime(crow["start_date"]).date()
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
        })
    return out


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    events = build_events()
    if not events:
        print("[run_inference] no events resolved; nothing to test.")
        return 1

    # Per-event anomaly array for H1
    anomalies = np.array([
        e["tmax_event_c"] - float(e["baseline"]["tmax"].mean())
        for e in events
    ])

    # Long case-crossover frame for H2
    frame = build_case_crossover_frame(events)

    results = {
        "n_events_resolved": len(events),
        "n_case_crossover_rows": int(len(frame)),
        "provenance_counts": pd.Series(
            [e["provenance"] for e in events]
        ).value_counts().to_dict(),
        "H1_wilcoxon_signed_rank": wilcoxon_signed_rank(anomalies),
        "H1_sign_test": sign_test(anomalies),
        "H1_bootstrap_mean_ci": bootstrap_mean_ci(anomalies),
        "H2_case_crossover": case_crossover_conditional_logit(frame),
        "H2_stratified_permutation": stratified_permutation(frame),
        "sigma_rescaled": hsiang_sigma_rescaled(events),
    }

    with REPORT_JSON.open("w") as f:
        json.dump(results, f, indent=2, default=str)

    write_markdown(results, REPORT_MD)
    print(f"[done] {REPORT_MD}")
    print(f"[done] {REPORT_JSON}")
    return 0


def write_markdown(results: dict, out: Path) -> None:
    cc = results["H2_case_crossover"]
    perm = results["H2_stratified_permutation"]
    sig = results["sigma_rescaled"]
    wilc = results["H1_wilcoxon_signed_rank"]
    sign = results["H1_sign_test"]
    boot = results["H1_bootstrap_mean_ci"]

    with out.open("w") as f:
        f.write("# ThermoStrife — inference results\n\n")
        f.write(
            "Pre-registered hypothesis tests on the cascade-resolved "
            f"events (**N = {results['n_events_resolved']}** of 112). "
            "See `docs/methods.md` for the pre-registered protocol and "
            "the data-coverage limitations behind the missing rows.\n\n"
        )
        f.write("## Source-tier breakdown\n\n")
        for prov, n in results["provenance_counts"].items():
            f.write(f"- `{prov}`: **{n}**\n")
        f.write("\n")

        f.write("## H2 — case-crossover conditional logit (headline)\n\n")
        if cc.get("skipped"):
            f.write(f"Skipped: {cc.get('reason')}\n\n")
        else:
            f.write(
                f"- **OR per +1 °C** above local same-month baseline: "
                f"**{cc['or_per_C']:.3f}** "
                f"(95 % CI {cc['or_ci95_low']:.3f} – {cc['or_ci95_high']:.3f})\n"
            )
            f.write(
                f"- β (log-OR) per °C: {cc['beta_per_C']:+.4f} "
                f"(SE {cc['se_per_C']:.4f})\n"
            )
            f.write(
                f"- p-value: one-sided **{cc['pvalue_one_sided']:.4g}**, "
                f"two-sided {cc['pvalue_two_sided']:.4g}\n"
            )
            f.write(
                f"- n strata = {cc['n_events']}, n rows = {cc['n_rows']}\n"
            )
            if cc.get("covariate_betas"):
                f.write("- Covariate β values:\n")
                for name, b in cc["covariate_betas"].items():
                    f.write(f"  - `{name}`: {b:+.4f}\n")
            f.write("\n")

        f.write("## H2 — stratified permutation (non-parametric backup)\n\n")
        if perm.get("skipped"):
            f.write(f"Skipped: {perm.get('reason')}\n\n")
        else:
            f.write(
                f"- Observed (mean of event-day Tmax minus mean of "
                f"control Tmax, averaged across events): "
                f"**{perm['observed_diff_C']:+.3f} °C**\n"
            )
            f.write(
                f"- p-value: one-sided **{perm['pvalue_one_sided']:.4g}**, "
                f"two-sided {perm['pvalue_two_sided']:.4g}\n"
            )
            f.write(
                f"- n events = {perm['n_events']}, n permutations = "
                f"{perm['n_perm']}\n\n"
            )

        f.write("## σ-rescaled effect (Burke et al. 2015 currency)\n\n")
        if sig.get("skipped"):
            f.write(f"Skipped: {sig.get('reason')}\n\n")
        else:
            f.write(
                f"- Mean z-score across events: **{sig['mean_z']:+.3f} σ** "
                f"(95 % CI {sig['ci95_low_z']:+.3f} – "
                f"{sig['ci95_high_z']:+.3f})\n"
            )
            f.write(f"- Median z: {sig['median_z']:+.3f} σ\n")
            f.write(
                f"- Fraction of events with z > 0: "
                f"**{sig['fraction_positive']:.1%}**\n"
            )
            f.write(
                "- Burke, Hsiang & Miguel (2015) report +2.4 % "
                "interpersonal violence per 1 σ contemporaneous warming as "
                "the pooled cross-study estimate.\n\n"
            )

        f.write("## H1 — descriptive (per-event anomalies)\n\n")
        if not wilc.get("skipped"):
            f.write(
                f"- **Wilcoxon signed-rank** (one-sided, H1: median > 0): "
                f"p = **{wilc['pvalue']:.4g}**, median = "
                f"{wilc['median']:+.3f} °C, n = {wilc['n']}\n"
            )
        if not sign.get("skipped"):
            f.write(
                f"- **Sign test** (one-sided, H1: P(anomaly > 0) > 0.5): "
                f"{sign['n_positive']}/{sign['n_nonzero']} positive = "
                f"{sign['proportion_positive']:.1%}; p = "
                f"**{sign['pvalue']:.4g}**\n"
            )
        if not boot.get("skipped"):
            f.write(
                f"- **Bootstrap mean anomaly**: "
                f"**{boot['mean']:+.3f} °C** "
                f"(95 % CI {boot['ci_low']:+.3f} – {boot['ci_high']:+.3f}), "
                f"n = {boot['n']}, B = {boot['n_boot']}\n"
            )


if __name__ == "__main__":
    raise SystemExit(main())
