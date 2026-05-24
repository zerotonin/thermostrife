# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — viz                                              ║
# ║  « Wong-palette rainclouds + null densities for the deck »       ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Three figures, each triple-output (SVG + PNG + CSV):            ║
# ║                                                                  ║
# ║    plot_anomaly_raincloud   — headline event-anomaly figure;     ║
# ║                                points coloured by source tier    ║
# ║                                                                  ║
# ║    plot_null_density        — permutation null with observed     ║
# ║                                statistic; visual H2 proof        ║
# ║                                                                  ║
# ║    plot_anomaly_by_year     — anomaly vs event year with         ║
# ║                                rolling mean; era visualiser      ║
# ║                                                                  ║
# ║  SVGs use svg.fonttype='none' (see constants.save_figure) so all ║
# ║  text remains editable in Inkscape.                              ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Plotting helpers.  Rainclouds, not bar charts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

from .constants import (
    FIGURE_SIZE_DOUBLE,
    FIGURE_SIZE_SINGLE,
    SEMANTIC_COLOURS,
    TIER_COLOURS,
    TIER_LABELS,
    WONG,
    save_figure,
)

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────
#  Headline raincloud: per-event anomaly distribution
# ─────────────────────────────────────────────────────────────────


def plot_anomaly_raincloud(
    events_df: pd.DataFrame,
    output_dir: Path,
    stem: str = "anomaly_raincloud",
    annotation: str | None = None,
) -> Path:
    """Half-violin + jittered strip + boxplot of per-event anomalies.

    ``events_df`` must have at least the columns ``event_id``,
    ``anomaly_C``, and ``provenance``.  Points are coloured by the
    ``TIER_COLOURS`` mapping.  ``annotation`` (e.g. the H2 OR / p-value
    string) is overlaid in the lower right.
    """
    events_df = events_df.dropna(subset=["anomaly_C"]).copy()
    if events_df.empty:
        raise ValueError("no events with non-NA anomaly_C to plot")
    anom = events_df["anomaly_C"].to_numpy()

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_SINGLE)

    # ── Half-violin on the right ──────────────────────────────
    pad = max(0.5, 0.05 * (anom.max() - anom.min()))
    y_grid = np.linspace(anom.min() - pad, anom.max() + pad, 300)
    kde = gaussian_kde(anom)
    density = kde(y_grid)
    density = density / density.max() * 0.42
    ax.fill_betweenx(
        y_grid, 0.5, 0.5 + density,
        color=WONG["sky_blue"], alpha=0.45, linewidth=0,
    )
    ax.plot(0.5 + density, y_grid, color=WONG["sky_blue"], linewidth=1.2)

    # ── Box plot on the centre line ───────────────────────────
    bp = ax.boxplot(
        anom, positions=[0.46], widths=0.08, vert=True, showfliers=False,
        patch_artist=True, medianprops={"color": WONG["vermilion"], "linewidth": 1.5},
        boxprops={"facecolor": "white", "edgecolor": "black", "linewidth": 1},
        whiskerprops={"color": "black", "linewidth": 1},
        capprops={"color": "black", "linewidth": 1},
    )
    del bp  # silence unused-name lint; matplotlib draws by side-effect

    # ── Jittered strip plot on the left ───────────────────────
    rng = np.random.default_rng(20260524)
    jitter = rng.uniform(0.05, 0.38, size=len(events_df))
    colours = [TIER_COLOURS.get(p, WONG["black"]) for p in events_df["provenance"]]
    ax.scatter(
        jitter, events_df["anomaly_C"],
        c=colours, s=24, alpha=0.78,
        edgecolor="black", linewidth=0.35,
    )

    # ── Reference line and mean marker ────────────────────────
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.55)
    mean = float(anom.mean())
    ax.axhline(
        mean, color=SEMANTIC_COLOURS["event"], linestyle=":", linewidth=1.1,
        alpha=0.85,
    )
    ax.text(
        0.98, mean, f"mean = {mean:+.2f} °C",
        color=SEMANTIC_COLOURS["event"], va="bottom", ha="right", fontsize=8.5,
    )

    # ── Annotation (headline result) ──────────────────────────
    if annotation:
        ax.text(
            0.98, 0.02, annotation,
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
            family="monospace",
            bbox={"facecolor": "white", "edgecolor": "grey", "alpha": 0.92, "pad": 4},
        )

    # ── Per-tier legend (only tiers actually present) ────────
    present_tiers = list(events_df["provenance"].dropna().unique())
    handles = [
        mpatches.Patch(
            facecolor=TIER_COLOURS.get(t, WONG["black"]),
            edgecolor="black", linewidth=0.4,
            label=TIER_LABELS.get(t, t),
        )
        for t in TIER_COLOURS if t in present_tiers
    ]
    ax.legend(
        handles=handles, loc="upper left",
        fontsize=8, frameon=True, framealpha=0.92, title_fontsize=8.5,
    )

    ax.set_xlim(-0.05, 1.05)
    ax.set_xticks([])
    ax.set_ylabel("Event-day anomaly vs local same-month baseline (°C)")
    ax.set_title(f"Violent uprisings ride positive temperature anomalies (n = {len(events_df)})")
    fig.tight_layout()

    save_figure(fig, stem, output_dir,
                data_csv=events_df[["event_id", "anomaly_C", "provenance"]])
    plt.close(fig)
    return output_dir / f"{stem}.png"


# ─────────────────────────────────────────────────────────────────
#  Permutation null density with observed statistic
# ─────────────────────────────────────────────────────────────────


def plot_null_density(
    observed_stat: float,
    null_draws: np.ndarray,
    output_dir: Path,
    stem: str = "null_density",
    two_sided_p: float | None = None,
) -> Path:
    """Permutation-null KDE with the observed statistic marked."""
    null_draws = np.asarray(null_draws, dtype=float)
    null_draws = null_draws[~np.isnan(null_draws)]
    if null_draws.size < 50:
        raise ValueError(f"need ≥ 50 null draws for a sensible KDE; got {null_draws.size}")

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_SINGLE)

    lo = min(null_draws.min(), observed_stat) - 0.5
    hi = max(null_draws.max(), observed_stat) + 0.5
    x = np.linspace(lo, hi, 400)
    kde = gaussian_kde(null_draws)
    y = kde(x)

    ax.fill_between(x, 0, y, color=SEMANTIC_COLOURS["null"], alpha=0.18,
                    label=f"Permutation null (B={null_draws.size})")
    ax.plot(x, y, color=SEMANTIC_COLOURS["null"], linewidth=1.2)
    ax.axvline(0, color="black", linestyle="--", linewidth=0.7, alpha=0.5)
    ax.axvline(
        observed_stat, color=SEMANTIC_COLOURS["event"], linewidth=2.0,
        label=f"Observed = {observed_stat:+.3f} °C",
    )

    if two_sided_p is not None:
        ax.text(
            0.02, 0.98, f"two-sided p = {two_sided_p:.4g}",
            transform=ax.transAxes, va="top", ha="left", fontsize=9,
            family="monospace",
            bbox={"facecolor": "white", "edgecolor": "grey", "alpha": 0.92, "pad": 4},
        )

    ax.set_xlabel("Mean event Tmax − mean control Tmax (°C)")
    ax.set_ylabel("Permutation density")
    ax.set_title("H2 permutation null vs observed statistic")
    ax.legend(loc="upper right", fontsize=8.5, frameon=True, framealpha=0.92)
    fig.tight_layout()

    save_figure(
        fig, stem, output_dir,
        data_csv=pd.DataFrame({"null_draw_C": null_draws}),
    )
    plt.close(fig)
    return output_dir / f"{stem}.png"


# ─────────────────────────────────────────────────────────────────
#  Anomaly vs event year — era-stratification visualiser
# ─────────────────────────────────────────────────────────────────


def plot_anomaly_by_year(
    events_df: pd.DataFrame,
    output_dir: Path,
    stem: str = "anomaly_by_year",
    rolling_window: int = 11,
) -> Path:
    """Scatter of per-event anomaly vs event year + rolling mean.

    ``events_df`` must have ``event_id``, ``year``, ``anomaly_C``,
    ``provenance`` columns.
    """
    events_df = events_df.dropna(subset=["year", "anomaly_C"]).copy()
    events_df = events_df.sort_values("year").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_DOUBLE)

    colours = [TIER_COLOURS.get(p, WONG["black"]) for p in events_df["provenance"]]
    ax.scatter(
        events_df["year"], events_df["anomaly_C"],
        c=colours, s=28, alpha=0.78,
        edgecolor="black", linewidth=0.35,
    )

    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.55)

    # Rolling mean over consecutive events (irregular year spacing is fine
    # for a smoother; it gives a sense of trend across the panel)
    smoothed = (
        events_df["anomaly_C"]
        .rolling(window=rolling_window, center=True, min_periods=3).mean()
    )
    ax.plot(
        events_df["year"], smoothed,
        color=SEMANTIC_COLOURS["event"], linewidth=2.0,
        label=f"{rolling_window}-event rolling mean",
    )

    present_tiers = list(events_df["provenance"].dropna().unique())
    handles = [
        mpatches.Patch(
            facecolor=TIER_COLOURS.get(t, WONG["black"]),
            edgecolor="black", linewidth=0.4,
            label=TIER_LABELS.get(t, t),
        )
        for t in TIER_COLOURS if t in present_tiers
    ]
    handles.append(plt.Line2D(
        [], [], color=SEMANTIC_COLOURS["event"], linewidth=2.0,
        label=f"{rolling_window}-event rolling mean",
    ))

    ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=True,
              framealpha=0.92)

    ax.set_xlabel("Event year")
    ax.set_ylabel("Anomaly vs local same-month baseline (°C)")
    ax.set_title(f"Per-event anomaly across the 1750–2024 panel (n = {len(events_df)})")
    fig.tight_layout()

    save_figure(
        fig, stem, output_dir,
        data_csv=events_df[["event_id", "year", "anomaly_C", "provenance"]],
    )
    plt.close(fig)
    return output_dir / f"{stem}.png"
