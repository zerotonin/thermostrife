# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — constants                                        ║
# ║  « era bins, station map, Wong palette, save_figure helper »     ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Central configuration for the historical-uprisings analysis.    ║
# ║  Era boundaries follow the dataset's five-era partition.         ║
# ║                                                                  ║
# ║  Wong (2011) colourblind-safe palette is the only colour source; ║
# ║  never import an ad-hoc hex value in another module.             ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Shared configuration: era bins, station lookup, palette, paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

if TYPE_CHECKING:
    import pandas as pd

# ─────────────────────────────────────────────────────────────────
#  Era boundaries  « match the dataset's five-era partition »
# ─────────────────────────────────────────────────────────────────

ERA_BINS: list[int] = [1750, 1850, 1920, 1970, 2000, 2027]
ERA_LABELS: list[str] = [
    "1750-1850",
    "1850-1920",
    "1920-1970",
    "1970-2000",
    "2000-2026",
]

# ─────────────────────────────────────────────────────────────────
#  Baseline window  « ±5-year same-station, same-month decadal »
# ─────────────────────────────────────────────────────────────────

BASELINE_HALF_WINDOW_YEARS: int = 5
EVENT_BUFFER_DAYS: int = 7  # exclude event ± buffer from control pool

# ─────────────────────────────────────────────────────────────────
#  Case-crossover control sampling
# ─────────────────────────────────────────────────────────────────

N_PERMUTATION: int = 10_000
N_BOOTSTRAP: int = 10_000
RNG_SEED: int = 20260521

# ┌────────────────────────────────────────────────────────────┐
# │ Wong (2011) palette  « colourblind-safe base colours »     │
# └────────────────────────────────────────────────────────────┘

WONG: dict[str, str] = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermilion": "#D55E00",
    "reddish_purple": "#CC79A7",
}

#: Semantic role mapping used across all ThermoStrife figures.
SEMANTIC_COLOURS: dict[str, str] = {
    "event": WONG["vermilion"],          # uprising-day anomaly
    "control": WONG["sky_blue"],         # matched non-event day
    "null": WONG["black"],               # permutation null distribution
    "indoor": WONG["bluish_green"],      # indoor / state-led subset
    "outdoor": WONG["orange"],           # outdoor / civilian subset
    "north_hemi": WONG["blue"],
    "south_hemi": WONG["yellow"],
    "anti_heat": WONG["reddish_purple"], # counter-examples (winter events)
}

#: Source-tier colours, applied per-event in scatter / strip plots.
#: Ordered by historical reach: green (modern stations) → purple (deep
#: historical reanalysis).
TIER_COLOURS: dict[str, str] = {
    "tier1_ghcn":        WONG["bluish_green"],
    "tier2_hadcet_max":  WONG["sky_blue"],
    "tier2_hadcet_mean": WONG["sky_blue"],
    "tier3_era5":        WONG["orange"],
    "tier4_20crv3":      WONG["reddish_purple"],
}

#: Human-readable labels for legends, keyed by provenance code.
TIER_LABELS: dict[str, str] = {
    "tier1_ghcn":        "Tier 1 — GHCN / meteostat",
    "tier2_hadcet_max":  "Tier 2 — HadCET (Tmax)",
    "tier2_hadcet_mean": "Tier 2 — HadCET (mean)",
    "tier3_era5":        "Tier 3 — ERA5 reanalysis",
    "tier4_20crv3":      "Tier 4 — 20CRv3 reanalysis",
}

# ─────────────────────────────────────────────────────────────────
#  Figure defaults
# ─────────────────────────────────────────────────────────────────

FIGURE_DPI: int = 200
FIGURE_SIZE_SINGLE: tuple[float, float] = (7.0, 4.2)
FIGURE_SIZE_DOUBLE: tuple[float, float] = (9.0, 4.5)

# ─────────────────────────────────────────────────────────────────
#  Repository paths
# ─────────────────────────────────────────────────────────────────

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = REPO_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
INTERIM_DIR: Path = DATA_DIR / "interim"
PROCESSED_DIR: Path = DATA_DIR / "processed"
CACHE_DIR: Path = DATA_DIR / "cache"
REPORTS_DIR: Path = REPO_ROOT / "reports"

CURATED_CSV: Path = RAW_DIR / "uprisings_temperature.csv"
EVENT_GEO_CSV: Path = RAW_DIR / "event_geo.csv"
STATION_MAP_CSV: Path = RAW_DIR / "station_map.csv"

# Peaceful-crowd parallel-control panel (Methods § 3b).
PEACEFUL_CSV: Path = RAW_DIR / "peaceful_gatherings.csv"
PEACEFUL_GEO_CSV: Path = RAW_DIR / "peaceful_geo.csv"

# ─────────────────────────────────────────────────────────────────
#  Type aliases
# ─────────────────────────────────────────────────────────────────

Anomaly: TypeAlias = float           # temperature anomaly, °C
Provenance: TypeAlias = str          # tier flag: tier1_ghcn ... tier4_20crv3 / NA

# ┌────────────────────────────────────────────────────────────┐
# │ Provenance tiers  « how a temperature row was resolved »   │
# └────────────────────────────────────────────────────────────┘

@dataclass(frozen=True)
class ProvenanceTier:
    code: str
    label: str
    rank: int   # lower = better

PROVENANCE_TIERS: dict[str, ProvenanceTier] = {
    "tier1_ghcn": ProvenanceTier("tier1_ghcn", "GHCN-Daily / ECA&D / DWD station", 1),
    "tier2_obs": ProvenanceTier("tier2_obs", "Long-record observatory", 2),
    "tier3_era5": ProvenanceTier("tier3_era5", "ERA5 reanalysis (1940+)", 3),
    "tier4_20crv3": ProvenanceTier("tier4_20crv3", "20CRv3 reanalysis (1836+)", 4),
    "unverifiable": ProvenanceTier("unverifiable", "No archival source available", 99),
    "curated_manual": ProvenanceTier("curated_manual", "Hand-curated value from primary source", 1),
}


# ─────────────────────────────────────────────────────────────────
#  save_figure helper  « triple output: SVG + PNG + CSV »
# ─────────────────────────────────────────────────────────────────

def save_figure(
    fig: Figure,
    stem: str,
    output_dir: Path,
    data_csv: pd.DataFrame | None = None,
    dpi: int = FIGURE_DPI,
) -> None:
    """Export figure as SVG + PNG with optional CSV data companion.

    Args:
        fig:        Matplotlib figure to save.
        stem:       Filename stem (no extension).
        output_dir: Target directory (created if needed).
        data_csv:   Optional DataFrame written alongside as ``<stem>.csv``.
        dpi:        Raster DPI for the PNG (default ``FIGURE_DPI``).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    with mpl.rc_context({"svg.fonttype": "none"}):
        fig.savefig(output_dir / f"{stem}.svg")
    fig.savefig(output_dir / f"{stem}.png", dpi=dpi)
    if data_csv is not None:
        data_csv.to_csv(output_dir / f"{stem}.csv", index=False)


__all__ = [
    "ERA_BINS",
    "ERA_LABELS",
    "BASELINE_HALF_WINDOW_YEARS",
    "EVENT_BUFFER_DAYS",
    "N_PERMUTATION",
    "N_BOOTSTRAP",
    "RNG_SEED",
    "WONG",
    "SEMANTIC_COLOURS",
    "TIER_COLOURS",
    "TIER_LABELS",
    "FIGURE_DPI",
    "FIGURE_SIZE_SINGLE",
    "FIGURE_SIZE_DOUBLE",
    "REPO_ROOT",
    "DATA_DIR",
    "RAW_DIR",
    "INTERIM_DIR",
    "PROCESSED_DIR",
    "CACHE_DIR",
    "REPORTS_DIR",
    "CURATED_CSV",
    "EVENT_GEO_CSV",
    "STATION_MAP_CSV",
    "PEACEFUL_CSV",
    "PEACEFUL_GEO_CSV",
    "PROVENANCE_TIERS",
    "ProvenanceTier",
    "save_figure",
    "plt",
]
