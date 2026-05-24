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

import os
from pathlib import Path
from typing import TYPE_CHECKING

# Force the non-interactive backend before pyplot is touched.  This
# module is import-time loaded by run_inference.py and tests; if a Qt
# binding is present in the env (thermostrife conda env happens to
# ship PyQt5), matplotlib will otherwise try to grab a display and
# crash on headless runs.
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)

import matplotlib as mpl  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import gaussian_kde  # noqa: E402

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
#  Warming-stripes timeline with event markers (Hawkins 2018 idiom)
# ─────────────────────────────────────────────────────────────────


def plot_warming_stripes_timeline(
    annual_temp: pd.Series,
    panels: dict[str, pd.DataFrame],
    output_dir: Path,
    stem: str = "warming_stripes_timeline",
    cmap_name: str = "RdBu_r",
    stripe_clip_sigma: float = 2.6,
) -> Path:
    """Hawkins-style annual warming stripes + event markers per panel.

    Background: one stripe per year coloured by that year's deviation
    from the long-term mean of ``annual_temp`` (a Series indexed by
    year).  Foreground: a row per panel with one marker per event,
    coloured by the event's per-event anomaly.
    """
    if annual_temp.empty:
        raise ValueError("annual_temp is empty; no background to draw")
    if not panels:
        raise ValueError("panels dict is empty")

    years = annual_temp.index.to_numpy()
    deviations = (annual_temp - annual_temp.mean()).to_numpy()
    sd = float(np.std(deviations, ddof=1))
    vmax = stripe_clip_sigma * sd if sd > 0 else 1.0
    norm = mpl.colors.Normalize(vmin=-vmax, vmax=vmax)
    cmap = mpl.cm.get_cmap(cmap_name)

    n_panels = len(panels)
    fig = plt.figure(figsize=(FIGURE_SIZE_DOUBLE[0], 1.6 + 0.9 * n_panels))
    gs = fig.add_gridspec(
        n_panels + 1, 1,
        height_ratios=[1.2, *([1.0] * n_panels)],
        hspace=0.18,
    )

    ax_bg = fig.add_subplot(gs[0])
    for y, d in zip(years, deviations, strict=False):
        ax_bg.axvspan(y - 0.5, y + 0.5, facecolor=cmap(norm(d)), edgecolor="none")
    ax_bg.set_xlim(years.min() - 0.5, years.max() + 0.5)
    ax_bg.set_yticks([])
    ax_bg.set_xticks([])
    ax_bg.set_title(
        f"HadCET annual mean deviation from {annual_temp.mean():.2f} °C, "
        f"{int(years.min())}–{int(years.max())}",
        fontsize=9,
    )

    all_anom = np.concatenate([df["anomaly_C"].to_numpy() for df in panels.values()])
    anom_clip = max(1.0, float(np.nanpercentile(np.abs(all_anom), 95)))
    event_norm = mpl.colors.Normalize(vmin=-anom_clip, vmax=anom_clip)
    event_cmap = mpl.cm.get_cmap("RdBu_r")

    for i, (label, df) in enumerate(panels.items(), start=1):
        ax = fig.add_subplot(gs[i], sharex=ax_bg)
        sub = df.dropna(subset=["year", "anomaly_C"])
        for y, d in zip(years, deviations, strict=False):
            ax.axvspan(y - 0.5, y + 0.5, facecolor=cmap(norm(d)),
                       edgecolor="none", alpha=0.22)
        ax.scatter(
            sub["year"], np.zeros(len(sub)),
            c=[event_cmap(event_norm(a)) for a in sub["anomaly_C"]],
            s=44, edgecolor="black", linewidth=0.4, zorder=3,
        )
        ax.set_ylim(-0.45, 0.45)
        ax.set_yticks([])
        ax.set_ylabel(f"{label}\n(n={len(sub)})", rotation=0,
                      ha="right", va="center", fontsize=8.5)
        if i < n_panels:
            ax.set_xticks([])
        else:
            ax.set_xlabel("Year")

    cbar_ax = fig.add_axes([0.92, 0.16, 0.014, 0.62])
    sm = mpl.cm.ScalarMappable(norm=event_norm, cmap=event_cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cbar_ax, extend="both")
    cb.set_label("Event-day anomaly\nvs local same-month baseline (°C)",
                 fontsize=8.5)
    cb.ax.tick_params(labelsize=7.5)

    combined = pd.concat(
        [df.assign(panel=label) for label, df in panels.items()],
        ignore_index=True,
    )
    save_figure(fig, stem, output_dir, data_csv=combined)
    plt.close(fig)
    return output_dir / f"{stem}.png"


# ─────────────────────────────────────────────────────────────────
#  Superposed-epoch composite (heliophysics idiom)
# ─────────────────────────────────────────────────────────────────


def plot_superposed_epoch(
    profiles: dict[str, pd.DataFrame],
    output_dir: Path,
    stem: str = "superposed_epoch",
    panel_colours: dict | None = None,
    ci_level: float = 0.95,
) -> Path:
    """Superposed-epoch overlay: mean anomaly vs offset_days per panel.

    Each panel's DataFrame has columns ``event_id``, ``offset_days``,
    ``anomaly_C``.  Bootstrap CI per offset; flat profile near zero
    = null; bump centred on offset 0 = heat-aggression signature.
    """
    if not profiles:
        raise ValueError("profiles dict is empty")
    if panel_colours is None:
        panel_colours = {
            "Violent uprisings": SEMANTIC_COLOURS["event"],
            "Peaceful gatherings": SEMANTIC_COLOURS["control"],
        }

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_SINGLE)
    rng = np.random.default_rng(20260525)

    for label, df in profiles.items():
        if df.empty:
            continue
        col = panel_colours.get(label, SEMANTIC_COLOURS["null"])
        offsets = sorted(df["offset_days"].unique())
        means, ci_lo, ci_hi, ns = [], [], [], []
        for off in offsets:
            vals = df.loc[df["offset_days"] == off, "anomaly_C"].dropna().to_numpy()
            if len(vals) < 3:
                means.append(np.nan)
                ci_lo.append(np.nan)
                ci_hi.append(np.nan)
                ns.append(len(vals))
                continue
            means.append(float(vals.mean()))
            ns.append(len(vals))
            boot = rng.choice(vals, size=(2000, len(vals)), replace=True).mean(axis=1)
            lo, hi = np.quantile(boot, [(1 - ci_level) / 2, 0.5 + ci_level / 2])
            ci_lo.append(float(lo))
            ci_hi.append(float(hi))
        ax.plot(offsets, means, color=col, linewidth=2.0,
                marker="o", markersize=5,
                label=f"{label} (n={int(max(ns))})")
        ax.fill_between(offsets, ci_lo, ci_hi, color=col, alpha=0.18,
                        linewidth=0)

    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.55)
    ax.axvline(0, color="black", linestyle=":", linewidth=0.8, alpha=0.55)
    ax.set_xlabel("Days from event (t = 0)")
    ax.set_ylabel("Mean anomaly vs local same-month baseline (°C)")
    ax.set_title("Superposed-epoch composite — concentration of warm anomaly on event day")
    ax.legend(loc="upper left", fontsize=8.5, frameon=True, framealpha=0.92)
    fig.tight_layout()

    combined = pd.concat(
        [df.assign(panel=label) for label, df in profiles.items()],
        ignore_index=True,
    )
    save_figure(fig, stem, output_dir, data_csv=combined)
    plt.close(fig)
    return output_dir / f"{stem}.png"


# ─────────────────────────────────────────────────────────────────
#  Forest plot (Hsiang/Burke/Miguel idiom)
# ─────────────────────────────────────────────────────────────────


def plot_forest_h2(
    rows: list[dict],
    output_dir: Path,
    stem: str = "forest_h2",
    ref_x: float = 1.0,
) -> Path:
    """Forest plot of H2 OR-per-+1 °C estimates with 95 % CI whiskers.

    ``rows`` is a list of dicts with keys ``label``, ``or``, ``ci_low``,
    ``ci_high``, optional ``colour``, optional ``n``.  Plotted bottom-up.
    """
    if not rows:
        raise ValueError("rows empty")
    n = len(rows)
    fig, ax = plt.subplots(figsize=(FIGURE_SIZE_SINGLE[0], 0.55 + 0.35 * n))

    y = np.arange(n)
    for i, r in enumerate(rows):
        col = r.get("colour", SEMANTIC_COLOURS["event"])
        ax.hlines(y[i], r["ci_low"], r["ci_high"], color=col, linewidth=1.8)
        ax.plot(r["or"], y[i], marker="o", markersize=8, color=col,
                markeredgecolor="black", markeredgewidth=0.5)
        label = r["label"]
        if r.get("n") is not None:
            label = f"{label}  (n={int(r['n'])})"
        ax.text(0.012, y[i], label, transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=9)
        ax.text(0.99, y[i],
                f"{r['or']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]",
                transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=8.5, family="monospace")

    ax.axvline(ref_x, color="black", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.set_yticks([])
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlabel("Odds ratio per +1 °C above local same-month baseline (95 % CI)")
    ax.set_title("Case-crossover effect estimates — forest plot")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    fig.tight_layout()

    df_csv = pd.DataFrame(rows)
    save_figure(fig, stem, output_dir, data_csv=df_csv)
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
