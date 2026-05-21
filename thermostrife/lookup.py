# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — lookup                                           ║
# ║  « tiered weather-archive resolver »                             ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Resolves (lat, lon, date) into either a single Tmax value or    ║
# ║  a (tmax_event, baseline_window) anomaly pair, cascading:        ║
# ║    1. GHCN-Daily / ECA&D / DWD via meteostat                     ║
# ║    2. Long-record observatories (HadCET, plus Paris/Berlin/      ║
# ║       Brera/Vienna to come)                                      ║
# ║    3. ERA5 grid cell via cdsapi (1940+)            [stub]        ║
# ║    4. 20CRv3 reanalysis grid cell (1806-1980)                    ║
# ║                                                                  ║
# ║  Each resolved row carries a temp_provenance flag so the         ║
# ║  analysis can downweight low-tier or mean-vs-max resolutions.    ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Tiered Tmax resolver across GHCN, observatory archives, and reanalysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class Resolution:
    """Result of a single (lat, lon, date) lookup (no baseline)."""

    tmax_c: float | None
    provenance: str
    source_id: str
    note: str = ""


@dataclass(frozen=True)
class AnomalyFetch:
    """Generic event-day + baseline-window result from any tier.

    By construction the baseline is built from the *same* underlying
    source / station / series that produced ``tmax_event_c``, so the
    anomaly ``tmax_event_c - baseline['tmax'].mean()`` is internally
    consistent.
    """

    tmax_event_c: float | None
    baseline: pd.DataFrame
    station_id: str
    provenance: str
    note: str = ""

    @classmethod
    def empty(cls, note: str = "") -> AnomalyFetch:
        import pandas as pd
        return cls(
            tmax_event_c=None,
            baseline=pd.DataFrame(columns=["tmax"]),
            station_id="",
            provenance="unverifiable",
            note=note,
        )


# ─────────────────────────────────────────────────────────────────
#  Single-day cascade
# ─────────────────────────────────────────────────────────────────


def resolve(
    lat: float,
    lon: float,
    when: date,
    *,
    station_hint: str | None = None,
    radius_km: float = 50.0,
) -> Resolution:
    """Resolve daily Tmax for ``when`` via the tier cascade."""
    # ── Tier 1: meteostat ────────────────────────────────────────
    try:
        from .sources.meteostat_src import fetch_daily_tmax
    except ImportError:  # meteostat not installed
        fetch_daily_tmax = None  # type: ignore[assignment]

    if fetch_daily_tmax is not None:
        tmax, source_id, note = fetch_daily_tmax(
            lat, lon, when, station_hint=station_hint, radius_km=radius_km
        )
        if tmax is not None:
            return Resolution(
                tmax_c=tmax, provenance="tier1_ghcn",
                source_id=source_id, note=note,
            )

    # ── Tier 2: HadCET (British Isles only for now) ──────────────
    try:
        from .sources.hadcet_src import covers as hadcet_covers
        from .sources.hadcet_src import fetch_daily_value
    except ImportError:
        hadcet_covers = None  # type: ignore[assignment]
        fetch_daily_value = None  # type: ignore[assignment]

    if hadcet_covers is not None and hadcet_covers(lat, lon):
        reading = fetch_daily_value(when)
        if reading is not None:
            return Resolution(
                tmax_c=reading.value_c,
                provenance=reading.provenance,
                source_id="HadCET",
                note=f"HadCET {reading.metric} reading",
            )

    # ── Tier 3: ERA5 reanalysis (stub) ───────────────────────────
    # ── Tier 4: 20CRv3 reanalysis (stub) ─────────────────────────

    return Resolution(
        tmax_c=None,
        provenance="unverifiable",
        source_id="",
        note="all available tiers returned no value",
    )


# ─────────────────────────────────────────────────────────────────
#  Anomaly-fetch cascade  « event + matching baseline, one source »
# ─────────────────────────────────────────────────────────────────


def resolve_event_anomaly(
    lat: float,
    lon: float,
    when: date,
    *,
    half_window_years: int = 5,
    event_buffer_days: int = 7,
    min_baseline_days: int = 20,
    radius_km: float = 50.0,
) -> AnomalyFetch:
    """Cascade through tiers until one returns a consistent (event, baseline) pair.

    The returned ``AnomalyFetch`` carries event-day Tmax and a baseline
    DataFrame drawn from the *same* underlying series — never mixed
    across tiers — so the anomaly is internally consistent.
    """
    # ── Tier 1: meteostat ────────────────────────────────────────
    try:
        from .sources import meteostat_src
    except ImportError:
        meteostat_src = None  # type: ignore[assignment]

    if meteostat_src is not None:
        r = meteostat_src.resolve_for_anomaly(
            lat, lon, when,
            half_window_years=half_window_years,
            event_buffer_days=event_buffer_days,
            min_baseline_days=min_baseline_days,
            radius_km=radius_km,
        )
        if r.tmax_event_c is not None:
            return AnomalyFetch(
                tmax_event_c=r.tmax_event_c,
                baseline=r.baseline,
                station_id=r.station_id,
                provenance="tier1_ghcn",
                note=r.note,
            )

    # ── Tier 2: HadCET (British Isles) ───────────────────────────
    try:
        from .sources import hadcet_src
    except ImportError:
        hadcet_src = None  # type: ignore[assignment]

    if hadcet_src is not None and hadcet_src.covers(lat, lon):
        r = hadcet_src.resolve_for_anomaly(
            lat, lon, when,
            half_window_years=half_window_years,
            event_buffer_days=event_buffer_days,
            min_baseline_days=min_baseline_days,
        )
        if r.tmax_event_c is not None:
            return AnomalyFetch(
                tmax_event_c=r.tmax_event_c,
                baseline=r.baseline,
                station_id=r.station_id,
                provenance=r.provenance,
                note=r.note,
            )

    # ── Tier 3: ERA5 (stub) ──────────────────────────────────────

    # ── Tier 4: 20CRv3 (1806-1980) ───────────────────────────────
    try:
        from .sources import twentycr_src
    except ImportError:
        twentycr_src = None  # type: ignore[assignment]

    if twentycr_src is not None and twentycr_src.covers(when):
        r = twentycr_src.resolve_for_anomaly(
            lat, lon, when,
            half_window_years=half_window_years,
            event_buffer_days=event_buffer_days,
            min_baseline_days=min_baseline_days,
        )
        if r.tmax_event_c is not None:
            return AnomalyFetch(
                tmax_event_c=r.tmax_event_c,
                baseline=r.baseline,
                station_id=r.station_id,
                provenance=r.provenance,
                note=r.note,
            )

    return AnomalyFetch.empty(note="all available tiers returned no anomaly fetch")
