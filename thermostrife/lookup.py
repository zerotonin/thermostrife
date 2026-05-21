# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — lookup                                           ║
# ║  « tiered weather-archive resolver »                             ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Resolves a (lat, lon, date) request through Tiers 1-4:          ║
# ║    1. GHCN-Daily / ECA&D / DWD via meteostat                     ║
# ║    2. Long-record observatories (HadCET, Paris, Berlin, Brera)   ║
# ║    3. ERA5 grid cell via cdsapi (1940+)                          ║
# ║    4. 20CRv3 reanalysis grid cell (1836+)                        ║
# ║  Each row carries a temp_provenance flag so analysis can         ║
# ║  downweight low-tier resolutions.                                ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Tiered Tmax resolver across GHCN, observatory archives, and reanalysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Resolution:
    """Result of a single (lat, lon, date) lookup."""

    tmax_c: float | None
    provenance: str
    source_id: str
    note: str = ""


def resolve(
    lat: float,
    lon: float,
    when: date,
    *,
    station_hint: str | None = None,
    radius_km: float = 50.0,
) -> Resolution:
    """Resolve daily Tmax for ``when`` at (``lat``, ``lon``) via tier cascade.

    Order: Tier 1 (meteostat) → Tier 2 (observatories) → Tier 3 (ERA5) →
    Tier 4 (20CRv3).  The first tier to return a value wins; the rest of
    the cascade is short-circuited.

    Args:
        lat:           Latitude in decimal degrees.
        lon:           Longitude in decimal degrees.
        when:          Event date.
        station_hint:  Optional preferred GHCN station ID (Tier 1 only).
        radius_km:     Search radius for nearest-station lookup.

    Returns:
        Resolution carrying ``tmax_c`` (``None`` if all tiers failed),
        the matching ``provenance`` code from ``PROVENANCE_TIERS``, and
        the ``source_id`` (station ID or grid identifier) that resolved
        the value.
    """
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
                tmax_c=tmax,
                provenance="tier1_ghcn",
                source_id=source_id,
                note=note,
            )

    # ── Tier 2: long-record observatories (stub) ─────────────────
    # ── Tier 3: ERA5 reanalysis (stub) ───────────────────────────
    # ── Tier 4: 20CRv3 reanalysis (stub) ─────────────────────────

    return Resolution(
        tmax_c=None,
        provenance="unverifiable",
        source_id="",
        note="all available tiers returned no value",
    )
