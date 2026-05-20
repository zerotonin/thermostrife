# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — lookup                                           ║
# ║  « tiered weather-archive resolver »                             ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Resolves a (station, date) request through Tiers 1-4:           ║
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
    """Result of a single (station, date) lookup."""

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
) -> Resolution:
    """Resolve daily Tmax for ``when`` at (``lat``, ``lon``) via tier cascade.

    The cascade tries Tier 1 (meteostat / GHCN) first, then long-record
    observatories, then ERA5 reanalysis (1940+), then 20CRv3 (1836+).

    Args:
        lat:           Latitude in decimal degrees.
        lon:           Longitude in decimal degrees.
        when:          Event date.
        station_hint:  Optional preferred WMO/GHCN station ID.

    Returns:
        Resolution carrying ``tmax_c`` (``None`` if unverifiable),
        ``provenance`` (one of ``PROVENANCE_TIERS``), and ``source_id``
        identifying the station / grid cell that resolved the value.
    """
    raise NotImplementedError(
        "lookup.resolve() is not yet wired up — see thermostrife.sources "
        "for the per-tier adapters that will back it."
    )
