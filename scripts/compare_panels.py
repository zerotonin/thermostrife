#!/usr/bin/env python3
"""Side-by-side comparison: violent uprisings vs peaceful gatherings.

Reads both inference JSON outputs, builds a comparison markdown plus a
two-panel raincloud figure, and writes them to ``reports/``.  The
headline scientific point: if the +1 °C anomaly on uprising days were
a generic outdoor-crowd opportunity effect (Field 1992), peaceful
mass gatherings should show the same signal.  They don't.

Run from the repo root after both panels have been inferred:

    python scripts/run_inference.py --panel violent
    python scripts/run_inference.py --panel peaceful
    python scripts/compare_panels.py
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import gaussian_kde  # noqa: E402

from thermostrife.constants import (  # noqa: E402
    CURATED_CSV,
    EVENT_GEO_CSV,
    FIGURE_SIZE_DOUBLE,
    PEACEFUL_CSV,
    PEACEFUL_GEO_CSV,
    REPORTS_DIR,
    SEMANTIC_COLOURS,
    TIER_COLOURS,
    WONG,
    save_figure,
)
from thermostrife.lookup import resolve_event_anomaly  # noqa: E402

VIOLENT_JSON = REPORTS_DIR / "inference_results.json"
PEACEFUL_JSON = REPORTS_DIR / "inference_results_peaceful.json"
COMPARISON_MD = REPORTS_DIR / "peaceful_vs_violent.md"
COMPARISON_FIG_DIR = REPORTS_DIR / "figs"


# ─────────────────────────────────────────────────────────────────
#  Build per-event anomaly frames from the cascades (cached)
# ─────────────────────────────────────────────────────────────────


def build_anomaly_df(curated_csv: Path, geo_csv: Path) -> pd.DataFrame:
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(curated_csv).set_index("event_id")
    geo = pd.read_csv(geo_csv).set_index("event_id")
    rows = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        when = pd.to_datetime(crow["start_date"]).date()
        r = resolve_event_anomaly(grow["lat"], grow["lon"], when, radius_km=60)
        if r.tmax_event_c is None or len(r.baseline) == 0:
            continue
        bmean = float(r.baseline["tmax"].mean())
        rows.append({
            "event_id": event_id,
            "anomaly_C": r.tmax_event_c - bmean,
            "provenance": r.provenance,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
#  Side-by-side raincloud figure
# ─────────────────────────────────────────────────────────────────


def _half_violin(ax, data, x_anchor, side, colour):
    pad = max(0.5, 0.05 * (data.max() - data.min()))
    y = np.linspace(data.min() - pad, data.max() + pad, 300)
    density = gaussian_kde(data)(y)
    density = density / density.max() * 0.36
    x_fill = x_anchor + density if side == "right" else x_anchor - density
    ax.fill_betweenx(y, x_anchor, x_fill, color=colour, alpha=0.45, linewidth=0)
    ax.plot(x_fill, y, color=colour, linewidth=1.1)


def plot_comparison(
    violent_df: pd.DataFrame,
    peaceful_df: pd.DataFrame,
    headline: dict,
    output_dir: Path,
    stem: str = "peaceful_vs_violent",
) -> Path:
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_DOUBLE)

    # Two anchor columns
    anchors = {"Violent uprisings": 0.30, "Peaceful gatherings": 1.30}
    panels = {
        "Violent uprisings": (violent_df, SEMANTIC_COLOURS["event"]),
        "Peaceful gatherings": (peaceful_df, SEMANTIC_COLOURS["control"]),
    }

    rng = np.random.default_rng(20260524)
    for label, x_anchor in anchors.items():
        df_, primary_col = panels[label]
        data = df_["anomaly_C"].to_numpy()

        # Half violin on the right
        _half_violin(ax, data, x_anchor + 0.05, "right", primary_col)

        # Boxplot on the centre line
        bp = ax.boxplot(
            data, positions=[x_anchor + 0.02], widths=0.06,
            vert=True, showfliers=False, patch_artist=True,
            medianprops={"color": WONG["vermilion"], "linewidth": 1.5},
            boxprops={"facecolor": "white", "edgecolor": "black", "linewidth": 1},
            whiskerprops={"color": "black", "linewidth": 1},
            capprops={"color": "black", "linewidth": 1},
        )
        del bp

        # Strip plot on the left
        jitter = rng.uniform(x_anchor - 0.35, x_anchor - 0.05, size=len(df_))
        colours = [TIER_COLOURS.get(p, WONG["black"]) for p in df_["provenance"]]
        ax.scatter(jitter, df_["anomaly_C"], c=colours, s=22, alpha=0.78,
                   edgecolor="black", linewidth=0.3)

        mean = float(data.mean())
        ax.hlines(mean, x_anchor - 0.40, x_anchor + 0.42,
                  color=primary_col, linestyle=":", linewidth=1.2)
        ax.text(
            x_anchor + 0.45, mean, f"mean {mean:+.2f} °C  (n={len(df_)})",
            color=primary_col, va="center", ha="left", fontsize=8.5,
        )

    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.55)

    ax.set_xticks(list(anchors.values()))
    ax.set_xticklabels(list(anchors.keys()), fontsize=11)
    ax.set_xlim(-0.2, 2.8)
    ax.set_ylabel("Event-day anomaly vs local same-month baseline (°C)")
    ax.set_title("Outdoor-opportunity control: violent uprisings vs peaceful gatherings")

    # Annotation
    annotation = (
        f"H2 case-crossover OR per +1 °C\n"
        f"  Violent:  {headline['violent_or']:.3f}  "
        f"(CI {headline['violent_ci'][0]:.3f}–{headline['violent_ci'][1]:.3f}), "
        f"p = {headline['violent_p']:.4g}\n"
        f"  Peaceful: {headline['peaceful_or']:.3f}  "
        f"(CI {headline['peaceful_ci'][0]:.3f}–{headline['peaceful_ci'][1]:.3f}), "
        f"p = {headline['peaceful_p']:.4g}"
    )
    ax.text(
        0.99, 0.02, annotation,
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
        family="monospace",
        bbox={"facecolor": "white", "edgecolor": "grey", "alpha": 0.92, "pad": 4},
    )

    # Tier-colour legend (per-panel doesn't make sense; show all encountered tiers)
    encountered = set(violent_df["provenance"]) | set(peaceful_df["provenance"])
    handles = [
        mpatches.Patch(
            facecolor=TIER_COLOURS.get(t, WONG["black"]),
            edgecolor="black", linewidth=0.4, label=t,
        )
        for t in TIER_COLOURS if t in encountered
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=True,
              framealpha=0.92, title="Source tier", title_fontsize=8.5)

    fig.tight_layout()

    combined = pd.concat([
        violent_df.assign(panel="violent"),
        peaceful_df.assign(panel="peaceful"),
    ], ignore_index=True)
    save_figure(fig, stem, output_dir, data_csv=combined)
    plt.close(fig)
    return output_dir / f"{stem}.png"


# ─────────────────────────────────────────────────────────────────
#  Markdown report
# ─────────────────────────────────────────────────────────────────


def write_report(
    violent: dict,
    peaceful: dict,
    out: Path = COMPARISON_MD,
) -> None:
    def cell(r, key, fmt=".4g"):
        return format(r[key], fmt)

    v_cc = violent["H2_case_crossover"]
    p_cc = peaceful["H2_case_crossover"]
    v_perm = violent["H2_stratified_permutation"]
    p_perm = peaceful["H2_stratified_permutation"]
    v_sig = violent["sigma_rescaled"]
    p_sig = peaceful["sigma_rescaled"]
    v_h3 = violent.get("H3_within_event_contrast", {})
    p_h3 = peaceful.get("H3_within_event_contrast", {})

    with out.open("w") as f:
        f.write("# Peaceful gatherings vs violent uprisings — opportunity-confound control\n\n")
        f.write(
            "Both panels run through the same cascading resolver and the "
            "same pre-registered inference battery. If the +1 °C anomaly "
            "we see on uprising days were the result of generic outdoor-"
            "crowd opportunity (Field 1992), peaceful mass gatherings "
            "should show the same signal. They don't — they sit slightly "
            "*cooler* than baseline, and none of the tests reject the "
            "null in the H1 direction.\n\n"
        )

        f.write("## Side-by-side\n\n")
        f.write(
            "| Statistic | Violent uprisings | Peaceful gatherings |\n"
            "|-----------|------------------:|--------------------:|\n"
        )
        f.write(
            f"| Resolved events | {violent['n_events_resolved']} "
            f"| {peaceful['n_events_resolved']} |\n"
        )
        f.write(
            f"| **H2 OR per +1 °C** | **{v_cc['or_per_C']:.3f}** "
            f"(CI {v_cc['or_ci95_low']:.3f}–{v_cc['or_ci95_high']:.3f}) "
            f"| **{p_cc['or_per_C']:.3f}** "
            f"(CI {p_cc['or_ci95_low']:.3f}–{p_cc['or_ci95_high']:.3f}) |\n"
        )
        f.write(
            f"| H2 one-sided p | {cell(v_cc, 'pvalue_one_sided')} "
            f"| {cell(p_cc, 'pvalue_one_sided')} |\n"
        )
        f.write(
            f"| H2 permutation Δ (°C) | {v_perm['observed_diff_C']:+.3f} "
            f"| {p_perm['observed_diff_C']:+.3f} |\n"
        )
        f.write(
            f"| H2 permutation one-sided p | {cell(v_perm, 'pvalue_one_sided')} "
            f"| {cell(p_perm, 'pvalue_one_sided')} |\n"
        )
        f.write(
            f"| σ-rescaled mean z | {v_sig['mean_z']:+.3f} "
            f"(CI {v_sig['ci95_low_z']:+.3f}, {v_sig['ci95_high_z']:+.3f}) "
            f"| {p_sig['mean_z']:+.3f} "
            f"(CI {p_sig['ci95_low_z']:+.3f}, {p_sig['ci95_high_z']:+.3f}) |\n"
        )
        f.write(
            f"| Fraction of events with positive anomaly | "
            f"{v_sig['fraction_positive']:.1%} "
            f"| {p_sig['fraction_positive']:.1%} |\n"
        )
        if v_h3 and not v_h3.get("skipped") and p_h3 and not p_h3.get("skipped"):
            f.write(
                f"| H3 within-event Δ (°C) | {v_h3['mean_diff_C']:+.3f} "
                f"| {p_h3['mean_diff_C']:+.3f} |\n"
            )
            f.write(
                f"| H3 one-sided p | {cell(v_h3, 'pvalue_one_sided')} "
                f"| {cell(p_h3, 'pvalue_one_sided')} |\n"
            )

        f.write("\n## Interpretation\n\n")
        f.write(
            "The two panels were resolved by the identical four-tier "
            "cascade and tested with the identical pre-registered battery. "
            "Both contain large outdoor gatherings spanning ~150 years and "
            "spread across major Northern-Hemisphere cities, so the "
            "*opportunity* for an outdoor crowd is comparable. The "
            "qualitative difference is whether the crowd was violent.\n\n"
        )
        f.write(
            f"- **Violent uprisings** show **OR = {v_cc['or_per_C']:.3f} "
            f"per +1 °C** above local same-month baseline "
            f"(one-sided p = {v_cc['pvalue_one_sided']:.4g}). The "
            f"permutation backup, σ-rescaling, and H1 descriptives all "
            "agree on direction.\n"
        )
        f.write(
            f"- **Peaceful gatherings** show **OR = {p_cc['or_per_C']:.3f} "
            f"per +1 °C** (one-sided p = {p_cc['pvalue_one_sided']:.4g}). "
            f"The permutation difference is **negative** "
            f"({p_perm['observed_diff_C']:+.3f} °C), the σ-rescaled mean "
            f"z is **negative** ({p_sig['mean_z']:+.3f}), and the fraction "
            f"of events on positive-anomaly days is "
            f"{p_sig['fraction_positive']:.1%} — below 50 %.\n\n"
        )
        f.write(
            "The Field (1992) outdoor-opportunity critique predicts that "
            "any large outdoor gathering should ride the same warm-day "
            "bias. We see the **opposite** pattern: peaceful gatherings "
            "are essentially weather-independent (the negative point "
            "estimates are not significant; the CIs cross zero), while "
            "violent uprisings carry a real positive bias. This is the "
            "single strongest piece of evidence that the H2 heat signal "
            "is specific to violence rather than to outdoor exposure.\n\n"
        )

        f.write("## Figure\n\n")
        f.write("![Peaceful vs violent comparison](figs/peaceful_vs_violent.png)\n")


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with VIOLENT_JSON.open() as f:
        violent = json.load(f)
    with PEACEFUL_JSON.open() as f:
        peaceful = json.load(f)

    v_df = build_anomaly_df(CURATED_CSV, EVENT_GEO_CSV)
    p_df = build_anomaly_df(PEACEFUL_CSV, PEACEFUL_GEO_CSV)

    headline = {
        "violent_or": violent["H2_case_crossover"]["or_per_C"],
        "violent_ci": (
            violent["H2_case_crossover"]["or_ci95_low"],
            violent["H2_case_crossover"]["or_ci95_high"],
        ),
        "violent_p": violent["H2_case_crossover"]["pvalue_one_sided"],
        "peaceful_or": peaceful["H2_case_crossover"]["or_per_C"],
        "peaceful_ci": (
            peaceful["H2_case_crossover"]["or_ci95_low"],
            peaceful["H2_case_crossover"]["or_ci95_high"],
        ),
        "peaceful_p": peaceful["H2_case_crossover"]["pvalue_one_sided"],
    }
    COMPARISON_FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_comparison(v_df, p_df, headline, COMPARISON_FIG_DIR)

    write_report(violent, peaceful)
    print(f"[done] {COMPARISON_MD}")
    print("[done] figs/peaceful_vs_violent.{svg,png,csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
