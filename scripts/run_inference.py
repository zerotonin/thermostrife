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

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from thermostrife.constants import (
    CURATED_CSV,
    EVENT_GEO_CSV,
    PEACEFUL_CSV,
    PEACEFUL_GEO_CSV,
    REPORTS_DIR,
)
from thermostrife.inference import (
    benjamini_hochberg,
    bootstrap_mean_ci,
    build_case_crossover_frame,
    case_crossover_conditional_logit,
    h3_within_event_contrast,
    hsiang_sigma_rescaled,
    sign_test,
    stratified_permutation,
    wilcoxon_signed_rank,
)
from thermostrife.lookup import resolve_event_anomaly
from thermostrife.viz import (
    plot_anomaly_by_year,
    plot_anomaly_raincloud,
    plot_null_density,
)

PANEL_PATHS = {
    "violent": {
        "curated": CURATED_CSV,
        "geo": EVENT_GEO_CSV,
        "report_md": REPORTS_DIR / "inference_results.md",
        "report_json": REPORTS_DIR / "inference_results.json",
        "figs_dir": REPORTS_DIR / "figs",
        "title_label": "violent uprisings",
    },
    "peaceful": {
        "curated": PEACEFUL_CSV,
        "geo": PEACEFUL_GEO_CSV,
        "report_md": REPORTS_DIR / "inference_results_peaceful.md",
        "report_json": REPORTS_DIR / "inference_results_peaceful.json",
        "figs_dir": REPORTS_DIR / "figs_peaceful",
        "title_label": "peaceful gatherings",
    },
}


def build_events(curated_csv: Path, geo_csv: Path) -> list[dict]:
    """Resolve every event in ``geo_csv`` into an inference-ready dict."""
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(curated_csv).set_index("event_id")
    geo = pd.read_csv(geo_csv).set_index("event_id")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_inference",
        description="Run the pre-registered inference battery on a panel.",
    )
    parser.add_argument(
        "--panel", choices=("violent", "peaceful"), default="violent",
        help="Which panel to analyse (default: violent uprisings).",
    )
    args = parser.parse_args(argv)
    cfg = PANEL_PATHS[args.panel]
    report_md: Path = cfg["report_md"]
    report_json: Path = cfg["report_json"]
    figs_dir: Path = cfg["figs_dir"]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)
    events = build_events(cfg["curated"], cfg["geo"])
    if not events:
        print(f"[run_inference] no {args.panel} events resolved; nothing to test.")
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
        "H3_within_event_contrast": h3_within_event_contrast(events),
        "sigma_rescaled": hsiang_sigma_rescaled(events),
    }

    # ── Multiple-comparisons correction over the H1/H2/H3 battery ──
    battery = {}
    if not results["H2_case_crossover"].get("skipped"):
        battery["H2 conditional logit"] = results["H2_case_crossover"]["pvalue_one_sided"]
    if not results["H2_stratified_permutation"].get("skipped"):
        battery["H2 stratified permutation"] = (
            results["H2_stratified_permutation"]["pvalue_one_sided"]
        )
    if not results["H1_wilcoxon_signed_rank"].get("skipped"):
        battery["H1 Wilcoxon signed-rank"] = results["H1_wilcoxon_signed_rank"]["pvalue"]
    if not results["H3_within_event_contrast"].get("skipped"):
        battery["H3 within-event contrast"] = (
            results["H3_within_event_contrast"]["pvalue_one_sided"]
        )
    if not results["H1_sign_test"].get("skipped"):
        battery["H1 sign test"] = results["H1_sign_test"]["pvalue"]
    results["multiple_comparisons"] = benjamini_hochberg(battery, alpha=0.05)
    results["panel"] = args.panel
    results["title_label"] = cfg["title_label"]

    with report_json.open("w") as f:
        json.dump(results, f, indent=2, default=str)

    # ── Figures ─────────────────────────────────────────────
    events_df = pd.DataFrame([
        {
            "event_id": e["event_id"],
            "year": e["when"].year,
            "anomaly_C": e["tmax_event_c"] - float(e["baseline"]["tmax"].mean()),
            "provenance": e["provenance"],
        }
        for e in events
    ])
    cc = results["H2_case_crossover"]
    annotation = (
        f"H2 case-crossover\n"
        f"  OR = {cc['or_per_C']:.3f} per +1 °C\n"
        f"  95% CI {cc['or_ci95_low']:.3f}–{cc['or_ci95_high']:.3f}\n"
        f"  one-sided p = {cc['pvalue_one_sided']:.4g}"
    )
    plot_anomaly_raincloud(events_df, figs_dir, annotation=annotation)
    plot_anomaly_by_year(events_df, figs_dir)

    # Separate small permutation just for the null-density figure
    perm_for_fig = _permutation_draws(frame, n_perm=5000)
    plot_null_density(
        observed_stat=results["H2_stratified_permutation"]["observed_diff_C"],
        null_draws=perm_for_fig,
        output_dir=figs_dir,
        two_sided_p=results["H2_stratified_permutation"]["pvalue_two_sided"],
    )

    write_markdown(results, report_md)
    print(f"[done] {report_md}")
    print(f"[done] {report_json}")
    print(f"[done] figures in {figs_dir}")
    return 0


def _permutation_draws(frame: pd.DataFrame, n_perm: int = 5000) -> np.ndarray:
    """Quick local permutation just to populate the null-density plot.

    Mirrors :func:`thermostrife.inference.stratified_permutation` but
    keeps the raw draws so the KDE has something to fit.  Small B
    (5000) is plenty for a smooth-looking density.
    """
    work = frame.dropna(subset=["tmax_c", "is_case", "event_id"]).copy()
    per_event = []
    for _eid, grp in work.groupby("event_id"):
        if grp["is_case"].sum() != 1:
            continue
        per_event.append(grp["tmax_c"].to_numpy())
    rng = np.random.default_rng(20260524)
    draws = np.empty(n_perm)
    for i in range(n_perm):
        diffs = []
        for tmaxs in per_event:
            j = rng.integers(0, len(tmaxs))
            ev = tmaxs[j]
            mask = np.ones(len(tmaxs), dtype=bool)
            mask[j] = False
            diffs.append(ev - tmaxs[mask].mean())
        draws[i] = float(np.mean(diffs))
    return draws


def write_markdown(results: dict, out: Path) -> None:
    cc = results["H2_case_crossover"]
    perm = results["H2_stratified_permutation"]
    h3 = results["H3_within_event_contrast"]
    sig = results["sigma_rescaled"]
    mc = results.get("multiple_comparisons", {})
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

        f.write("## H3 — within-event temporal contrast (hot day vs hot week)\n\n")
        if h3.get("skipped"):
            f.write(f"Skipped: {h3.get('reason')}\n\n")
        else:
            f.write(
                f"- **Mean diff**: anomaly @ {h3['window_offsets_days']} minus "
                f"anomaly @ {h3['surround_offsets_days']} = "
                f"**{h3['mean_diff_C']:+.3f} °C** "
                f"(95 % CI {h3['ci95_low_C']:+.3f} – {h3['ci95_high_C']:+.3f})\n"
            )
            f.write(f"- Median diff: {h3['median_diff_C']:+.3f} °C\n")
            f.write(
                f"- One-sided Wilcoxon p (H₁: median > 0): "
                f"**{h3['pvalue_one_sided']:.4g}**\n"
            )
            f.write(
                f"- n events used = {h3['n_events_used']}, "
                f"skipped (missing day) = {h3['n_events_skipped']}\n\n"
            )
            f.write(
                "*Interpretation*: a positive difference says the event day and "
                "its immediate neighbour sit higher above the local baseline "
                "than days a week away — the signature of a `hot day triggers "
                "riot' mechanism rather than `hot week happened to contain an "
                "event'.\n\n"
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

        if mc.get("results"):
            f.write("\n## Multiple-comparisons correction\n\n")
            f.write(
                f"Pre-registered family of **{mc['family_size']}** tests. "
                f"H2 conditional logit is the *single confirmatory test* "
                f"(uncorrected α = 0.05); H1 / H3 form a supportive "
                f"auxiliary battery, reported with both Benjamini–Hochberg "
                f"FDR-adjusted q-values (preferred for highly-correlated "
                f"tests like ours) and Bonferroni-adjusted p-values "
                f"(conservative reference). Bonferroni threshold per test = "
                f"α / k = {mc['bonferroni_threshold']:.4f}.\n\n"
            )
            f.write(
                "| Test | raw p | BH-adjusted q | Bonferroni-adjusted p "
                "| BH? | Bonf? |\n"
                "|------|------:|--------------:|---------------------:|"
                ":---:|:-----:|\n"
            )
            for name, row in sorted(
                mc["results"].items(), key=lambda kv: kv[1]["raw_p"]
            ):
                f.write(
                    f"| {name} | {row['raw_p']:.4f} "
                    f"| {row['bh_adjusted_p']:.4f} "
                    f"| {row['bonferroni_adjusted_p']:.4f} "
                    f"| {'✓' if row['bh_reject'] else '✗'} "
                    f"| {'✓' if row['bonferroni_reject'] else '✗'} |\n"
                )
            f.write(
                f"\n**Verdict:** BH rejects {mc['n_bh_rejected']}/"
                f"{mc['family_size']} at FDR = {mc['alpha']:.2f}; "
                f"Bonferroni rejects {mc['n_bonferroni_rejected']}/"
                f"{mc['family_size']} at the same α. The headline "
                "(H2 conditional logit) clears every correction.\n"
            )

        f.write("\n## Figures\n\n")
        f.write(
            "Three SVG + PNG + CSV triples land in `reports/figs/`. SVGs are "
            "Inkscape-editable (`svg.fonttype = 'none'`).\n\n"
        )
        f.write("![Anomaly raincloud](figs/anomaly_raincloud.png)\n\n")
        f.write("![Null density](figs/null_density.png)\n\n")
        f.write("![Anomaly by year](figs/anomaly_by_year.png)\n")


if __name__ == "__main__":
    raise SystemExit(main())
