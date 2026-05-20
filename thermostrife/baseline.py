# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — baseline                                         ║
# ║  « period-correct decadal baseline »                             ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Computes the ±5-year same-station, same-calendar-month mean     ║
# ║  Tmax to anchor anomaly_C against the local climate at the       ║
# ║  event year, rather than against modern climatology.             ║
# ║  Records decade_n and decade_se for uncertainty propagation.     ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Period-correct decadal-mean baseline for the anomaly column."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Baseline:
    """±5-year same-station, same-month decadal-mean reference."""

    mean_tmax_c: float
    n: int
    se: float
    window_years: tuple[int, int]
    source_id: str
    provenance: str


def compute_baseline(
    lat: float,
    lon: float,
    when: date,
    *,
    half_window_years: int = 5,
    event_buffer_days: int = 7,
    station_hint: str | None = None,
) -> Baseline:
    """Period-correct ±N-year same-station, same-calendar-month baseline.

    All daily Tmax values from the same source / station, restricted to
    the same calendar month as ``when``, in years
    ``[when.year - half_window_years, when.year + half_window_years]``,
    excluding the event window ± ``event_buffer_days``.

    Returns the mean, the sample size ``n``, and the standard error of
    the mean (``sd / sqrt(n)``) so the anomaly's uncertainty can be
    propagated downstream.
    """
    raise NotImplementedError(
        "baseline.compute_baseline() awaits the source adapters in "
        "thermostrife.sources to be implemented."
    )
