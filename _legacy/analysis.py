"""
analysis.py - Heat-aggression analysis on historical uprisings.

Inputs:
    uprisings_temperature.csv with columns:
        date, city, country, lat, lon, deaths, injured,
        day_temp_C, decade_mean_temp_C, anomaly_C, ...

Outputs:
    outputs/figs/        - PNG figures (histogram, box-plot-by-era, scatter)
    outputs/results.json - all numerical results

Usage:
    python analysis.py uprisings_temperature.csv

Designed to run on partial data: tests are skipped (with a warning) if
their preconditions are not met, but the script will not crash.

Author: methods scaffold for Bart Geurten's heat-aggression project.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless backend so the script runs on servers / CI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ERA_BINS = [1750, 1850, 1920, 1970, 2000, 2027]
ERA_LABELS = ["1750-1850", "1850-1920", "1920-1970", "1970-2000", "2000-2026"]

N_BOOTSTRAP = 10_000
N_PERMUTATION = 10_000
RNG_SEED = 20260520  # today's date for reproducibility

OUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUT_DIR / "figs"
RESULTS_PATH = OUT_DIR / "results.json"


# ---------------------------------------------------------------------------
# Loading & cleaning
# ---------------------------------------------------------------------------

def load_uprisings(csv_path: str) -> pd.DataFrame:
    """Load the uprisings CSV and parse the date column.

    The CSV is expected to have at least: date, day_temp_C, anomaly_C.
    All other columns are passed through. Dates that fail to parse are
    coerced to NaT and the row is dropped with a warning.
    """
    df = pd.read_csv(csv_path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        bad_dates = df["date"].isna().sum()
        if bad_dates:
            warnings.warn(f"{bad_dates} rows had unparseable dates and were dropped.")
            df = df.dropna(subset=["date"])
        df["year"] = df["date"].dt.year
    return df


def drop_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows missing day_temp_C or anomaly_C and report counts."""
    n0 = len(df)
    required = [c for c in ("day_temp_C", "anomaly_C") if c in df.columns]
    if not required:
        warnings.warn("No day_temp_C or anomaly_C column present - returning df as-is.")
        return df
    clean = df.dropna(subset=required).copy()
    dropped = n0 - len(clean)
    print(f"[load] kept {len(clean)} / {n0} rows ({dropped} dropped for NA in {required})")
    return clean


def add_era(df: pd.DataFrame) -> pd.DataFrame:
    """Add an 'era' column based on ERA_BINS, requires a 'year' column."""
    if "year" not in df.columns:
        return df
    df = df.copy()
    df["era"] = pd.cut(df["year"], bins=ERA_BINS, labels=ERA_LABELS, right=False)
    return df


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def descriptive_by_era(df: pd.DataFrame) -> dict:
    """Per-era descriptive statistics on anomaly_C."""
    if "era" not in df.columns or "anomaly_C" not in df.columns:
        return {}
    grouped = df.groupby("era", observed=True)["anomaly_C"].agg(
        n="count", mean="mean", median="median", std="std", q25=lambda x: x.quantile(0.25),
        q75=lambda x: x.quantile(0.75),
    )
    return grouped.reset_index().to_dict(orient="records")


# ---------------------------------------------------------------------------
# Core inferential tests (H1)
# ---------------------------------------------------------------------------

def wilcoxon_signed_rank(anomaly: np.ndarray) -> dict:
    """One-sided Wilcoxon signed-rank that median(anomaly) > 0.

    Returns statistic, p-value, n, and the sample median.
    """
    anomaly = np.asarray(anomaly, dtype=float)
    anomaly = anomaly[~np.isnan(anomaly)]
    if len(anomaly) < 5:
        return {"skipped": True, "reason": f"n={len(anomaly)} too small"}
    # scipy.wilcoxon with alternative='greater' tests whether median > 0
    res = stats.wilcoxon(anomaly, alternative="greater", zero_method="wilcox")
    return {
        "n": int(len(anomaly)),
        "statistic": float(res.statistic),
        "pvalue": float(res.pvalue),
        "median": float(np.median(anomaly)),
    }


def sign_test(anomaly: np.ndarray) -> dict:
    """Binomial sign test on P(anomaly > 0) > 0.5."""
    anomaly = np.asarray(anomaly, dtype=float)
    anomaly = anomaly[~np.isnan(anomaly)]
    positives = int(np.sum(anomaly > 0))
    n_nonzero = int(np.sum(anomaly != 0))
    if n_nonzero < 5:
        return {"skipped": True, "reason": f"only {n_nonzero} non-zero anomalies"}
    res = stats.binomtest(positives, n_nonzero, p=0.5, alternative="greater")
    return {
        "n_nonzero": n_nonzero,
        "n_positive": positives,
        "proportion_positive": positives / n_nonzero,
        "pvalue": float(res.pvalue),
    }


def bootstrap_mean_ci(
    anomaly: np.ndarray, n_boot: int = N_BOOTSTRAP, alpha: float = 0.05,
    rng: Optional[np.random.Generator] = None,
) -> dict:
    """Bootstrap percentile CI for the mean anomaly."""
    if rng is None:
        rng = np.random.default_rng(RNG_SEED)
    anomaly = np.asarray(anomaly, dtype=float)
    anomaly = anomaly[~np.isnan(anomaly)]
    if len(anomaly) < 5:
        return {"skipped": True, "reason": f"n={len(anomaly)} too small"}
    n = len(anomaly)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = anomaly[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {
        "n": n,
        "mean": float(anomaly.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_boot": n_boot,
    }


# ---------------------------------------------------------------------------
# H2: matched-control placebo test
# ---------------------------------------------------------------------------

def synthetic_control_anomaly(
    event_anomaly: np.ndarray, n_controls_per_event: int = 20,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Generate a *placeholder* control distribution.

    PLACEHOLDER until the user can pull real control-day temperatures from a
    weather archive (ECMWF ERA5, Berkeley Earth, NOAA GHCN). The placeholder
    draws N(0, observed_SD) - i.e. it assumes that a random day in the same
    month-and-place has zero expected anomaly relative to the decade mean.
    That is true by construction of the decade-mean reference, so this
    placeholder represents the *null* against which the event-day distribution
    is contrasted. Once real control days are available, replace this function
    with one that loads matched-day temperatures and computes their anomalies.
    """
    if rng is None:
        rng = np.random.default_rng(RNG_SEED + 1)
    sd = float(np.nanstd(event_anomaly, ddof=1))
    n_total = len(event_anomaly) * n_controls_per_event
    return rng.normal(loc=0.0, scale=sd, size=n_total)


def matched_control_test(event_anomaly: np.ndarray) -> dict:
    """Mann-Whitney U comparing event-day vs (synthetic) control-day anomaly."""
    event = np.asarray(event_anomaly, dtype=float)
    event = event[~np.isnan(event)]
    if len(event) < 5:
        return {"skipped": True, "reason": "too few events"}
    controls = synthetic_control_anomaly(event)
    res = stats.mannwhitneyu(event, controls, alternative="greater")
    return {
        "n_event": int(len(event)),
        "n_control": int(len(controls)),
        "U": float(res.statistic),
        "pvalue": float(res.pvalue),
        "mean_event": float(event.mean()),
        "mean_control": float(controls.mean()),
        "note": "controls are SYNTHETIC placeholder N(0, sd_event); replace once real matched days available",
    }


# ---------------------------------------------------------------------------
# Permutation test
# ---------------------------------------------------------------------------

def permutation_test(
    event_anomaly: np.ndarray, n_perm: int = N_PERMUTATION,
    rng: Optional[np.random.Generator] = None,
) -> dict:
    """Permutation test on (event vs synthetic-control) pooled labels.

    Statistic: difference of means. Two-sided p = fraction of permutations with
    |stat_perm| >= |stat_observed|.
    """
    if rng is None:
        rng = np.random.default_rng(RNG_SEED + 2)
    event = np.asarray(event_anomaly, dtype=float)
    event = event[~np.isnan(event)]
    if len(event) < 5:
        return {"skipped": True, "reason": "too few events"}
    controls = synthetic_control_anomaly(event, rng=rng)
    pooled = np.concatenate([event, controls])
    n_e = len(event)
    observed = event.mean() - controls.mean()
    perm_stats = np.empty(n_perm)
    for i in range(n_perm):
        rng.shuffle(pooled)
        perm_stats[i] = pooled[:n_e].mean() - pooled[n_e:].mean()
    p = float((np.abs(perm_stats) >= abs(observed)).mean())
    return {
        "n_perm": n_perm,
        "observed_stat": float(observed),
        "pvalue_two_sided": p,
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_histogram(df: pd.DataFrame, fig_dir: Path) -> Optional[Path]:
    if "anomaly_C" not in df.columns or df["anomaly_C"].dropna().empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = df["anomaly_C"].dropna().to_numpy()
    ax.hist(x, bins=20, edgecolor="black", alpha=0.75)
    ax.axvline(0, color="black", linestyle="--", lw=1, label="zero anomaly")
    ax.axvline(x.mean(), color="red", linestyle="-", lw=1.5,
               label=f"mean = {x.mean():.2f} C")
    ax.set_xlabel("Temperature anomaly on event day (C)")
    ax.set_ylabel("Count")
    ax.set_title(f"Anomaly distribution, N={len(x)} uprisings")
    ax.legend()
    out = fig_dir / "hist_anomaly.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_box_by_era(df: pd.DataFrame, fig_dir: Path) -> Optional[Path]:
    if "era" not in df.columns or "anomaly_C" not in df.columns:
        return None
    groups, labels = [], []
    for era in ERA_LABELS:
        sub = df.loc[df["era"] == era, "anomaly_C"].dropna().to_numpy()
        if len(sub) >= 2:
            groups.append(sub)
            labels.append(f"{era}\n(n={len(sub)})")
    if not groups:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.boxplot(groups, labels=labels, showmeans=True)
    ax.axhline(0, color="black", linestyle="--", lw=1)
    ax.set_ylabel("Anomaly (C)")
    ax.set_title("Anomaly by era")
    out = fig_dir / "box_by_era.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_anomaly_vs_lat(df: pd.DataFrame, fig_dir: Path) -> Optional[Path]:
    if not {"lat", "anomaly_C"}.issubset(df.columns):
        return None
    sub = df[["lat", "anomaly_C"]].dropna()
    if sub.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.scatter(sub["lat"], sub["anomaly_C"], alpha=0.7)
    ax.axhline(0, color="black", linestyle="--", lw=1)
    ax.set_xlabel("Latitude (degrees)")
    ax.set_ylabel("Anomaly (C)")
    ax.set_title("Anomaly vs latitude")
    out = fig_dir / "scatter_anomaly_lat.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_all(csv_path: str) -> dict:
    """End-to-end pipeline. Returns the results dict and writes it to disk."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    df_raw = load_uprisings(csv_path)
    df = drop_missing(df_raw)
    df = add_era(df)

    anomaly = df["anomaly_C"].to_numpy() if "anomaly_C" in df.columns else np.array([])

    results = {
        "input_csv": str(csv_path),
        "n_rows_input": int(len(df_raw)),
        "n_rows_clean": int(len(df)),
        "descriptive_by_era": descriptive_by_era(df),
        "H1_wilcoxon_signed_rank": wilcoxon_signed_rank(anomaly),
        "H1_sign_test": sign_test(anomaly),
        "bootstrap_mean_ci": bootstrap_mean_ci(anomaly),
        "H2_matched_control_placebo": matched_control_test(anomaly),
        "permutation_test": permutation_test(anomaly),
        "figures": {},
    }

    h = plot_histogram(df, FIG_DIR)
    b = plot_box_by_era(df, FIG_DIR)
    s = plot_anomaly_vs_lat(df, FIG_DIR)
    results["figures"]["histogram"] = str(h) if h else None
    results["figures"]["box_by_era"] = str(b) if b else None
    results["figures"]["scatter_lat"] = str(s) if s else None

    # JSON cannot serialize numpy / pandas Timestamp; cast defensively
    def _to_jsonable(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        if isinstance(o, pd.Timestamp):
            return o.isoformat()
        raise TypeError(f"not jsonable: {type(o)}")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=_to_jsonable)
    print(f"[done] results written to {RESULTS_PATH}")
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python analysis.py uprisings_temperature.csv")
        sys.exit(1)
    csv_path = sys.argv[1]
    if not Path(csv_path).exists():
        print(f"[warn] {csv_path} does not exist yet - exiting cleanly.")
        sys.exit(0)
    run_all(csv_path)
