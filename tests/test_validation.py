"""Internal-consistency gate for the Tier-1 cascade.

We deliberately do *not* compare against the hand-curated ``day_temp_C``
values — those were qualitative sanity checks from secondary sources,
and the analysis doesn't depend on them.  The anomaly is computed as
``day_temp_C - decade_mean_temp_C`` using the *same* source on both
sides, so station-selection offsets cancel by construction.

What does matter, and what these tests assert:

- **Coverage** — enough verified rows resolve at Tier 1 to support
  downstream analysis.
- **Single-station guarantee** — ``resolve_for_anomaly`` returns a
  ``station_id`` that produced both the event-day value and the
  baseline window, so anomaly = event - baseline is apples-to-apples.
- **Baseline size** — the ±5-year same-month window holds enough
  daily values to compute a meaningful mean ± SE.
- **Baseline plausibility** — the baseline SD is strictly positive
  and finite (i.e., meteostat returned real numbers, not NaN-soup).

Marked ``network`` because it hits meteostat upstream on first run;
re-runs are served from the parquet cache in ``data/cache/meteostat/``.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from thermostrife.constants import CURATED_CSV, EVENT_GEO_CSV
from thermostrife.sources.meteostat_src import resolve_for_anomaly

pytestmark = pytest.mark.network


# Gate thresholds — tighten as Tier 2/3 land and more rows resolve.
MIN_RESOLVED = 8
MIN_BASELINE_DAYS = 20


@pytest.fixture(scope="module")
def event_table() -> pd.DataFrame:
    """Resolve the verified-row subset of event_geo via the unified resolver.

    Scoped to rows where the curated CSV carries a non-NA ``day_temp_C``
    so the gate stays focused on the originally hand-verified 13 events.
    The full 112-event resolution lives in `scripts/validate_tier1.py`.
    """
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(CURATED_CSV).set_index("event_id")
    geo = pd.read_csv(EVENT_GEO_CSV).set_index("event_id")
    # Restrict to the originally hand-verified rows.
    verified = curated.dropna(subset=["day_temp_C"]).index
    geo = geo.loc[geo.index.intersection(verified)]
    rows = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        when = pd.to_datetime(crow["start_date"]).date()
        r = resolve_for_anomaly(grow["lat"], grow["lon"], when, radius_km=60)
        rows.append(
            {
                "event_id": event_id,
                "when": when,
                "tmax_event": r.tmax_event_c,
                "station": r.station_id or None,
                "baseline_n": len(r.baseline),
                "baseline_mean": (
                    float(r.baseline["tmax"].mean()) if len(r.baseline) else None
                ),
                "baseline_std": (
                    float(r.baseline["tmax"].std(ddof=1))
                    if len(r.baseline) > 1
                    else None
                ),
            }
        )
    return pd.DataFrame(rows)


def test_minimum_rows_resolve(event_table):
    """Tier 1 should resolve at least MIN_RESOLVED of the verified rows."""
    n_resolved = event_table["tmax_event"].notna().sum()
    assert n_resolved >= MIN_RESOLVED, (
        f"Tier 1 resolved only {n_resolved} of {len(event_table)} verified "
        f"rows; expected >= {MIN_RESOLVED}. Misses are expected for pre-1920 "
        f"events (Paris 1871, Chicago 1919, LAX 1965); regression beyond that "
        f"set indicates meteostat coverage or station-search drift."
    )


def test_resolved_rows_have_station(event_table):
    """Every resolved row must report the station that produced both readings."""
    resolved = event_table.dropna(subset=["tmax_event"])
    missing_station = resolved[resolved["station"].isna() | (resolved["station"] == "")]
    assert missing_station.empty, (
        "Rows with a non-null tmax_event but no station_id: "
        f"{list(missing_station['event_id'])}. This means the resolver returned "
        "a value without recording its source — fix in meteostat_src."
    )


def test_baseline_window_has_enough_data(event_table):
    """Baseline window must hold >= MIN_BASELINE_DAYS daily Tmax values."""
    resolved = event_table.dropna(subset=["tmax_event"])
    short = resolved[resolved["baseline_n"] < MIN_BASELINE_DAYS]
    if not short.empty:
        rows = "\n".join(
            f"  {r.event_id}: only {r.baseline_n} baseline days at {r.station}"
            for r in short.itertuples()
        )
        pytest.fail(
            f"{len(short)} resolved events have baseline windows with "
            f"< {MIN_BASELINE_DAYS} days:\n{rows}"
        )


def test_baseline_std_is_plausible(event_table):
    """Baseline SD must be strictly positive and finite."""
    resolved = event_table.dropna(subset=["tmax_event"])
    bad = resolved[
        resolved["baseline_std"].isna()
        | (resolved["baseline_std"] <= 0)
        | (resolved["baseline_std"] > 30)  # absurdly high for a single month
    ]
    assert bad.empty, (
        "Baseline SD implausible for: "
        f"{list(zip(bad['event_id'], bad['baseline_std'], strict=False))}. "
        "Either the station is reporting garbage or the window is too short."
    )
