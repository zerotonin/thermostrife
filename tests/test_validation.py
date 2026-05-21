"""Internal-consistency gate for the full tiered cascade.

We deliberately do *not* compare against the hand-curated ``day_temp_C``
values — those were qualitative sanity checks from secondary sources,
and the analysis doesn't depend on them.  The anomaly is computed as
``event_day - baseline_mean`` using the *same* underlying source on
both sides (single station for Tier 1, same HadCET series for Tier 2,
etc.), so absolute disagreement with the manual value is expected.

What does matter, and what these tests assert:

- **Coverage** — enough verified rows resolve in the cascade.
- **Single-source guarantee** — every resolved row carries a
  ``station_id`` (Tier 1) or a series identifier (Tier 2+).
- **Baseline size** — the ±5-year same-month window holds enough
  daily values to compute a meaningful mean ± SE.
- **Baseline plausibility** — the baseline SD is strictly positive
  and finite.

Marked ``network`` because Tier 1 (meteostat) hits the upstream API
on first run; re-runs are served from the parquet cache in
``data/cache/meteostat/``.  Tier 2 (HadCET) is fully local.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from thermostrife.constants import CURATED_CSV, EVENT_GEO_CSV
from thermostrife.lookup import resolve_event_anomaly

pytestmark = pytest.mark.network


MIN_RESOLVED = 13  # Tier 4 (20CRv3) now picks up Paris 1871, Chicago 1919, Watts 1965
MIN_BASELINE_DAYS = 20


@pytest.fixture(scope="module")
def event_table() -> pd.DataFrame:
    """Resolve the verified-row subset via the cascading resolver."""
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(CURATED_CSV).set_index("event_id")
    geo = pd.read_csv(EVENT_GEO_CSV).set_index("event_id")
    verified = curated.dropna(subset=["day_temp_C"]).index
    geo = geo.loc[geo.index.intersection(verified)]
    rows = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        when = pd.to_datetime(crow["start_date"]).date()
        r = resolve_event_anomaly(grow["lat"], grow["lon"], when, radius_km=60)
        rows.append(
            {
                "event_id": event_id,
                "when": when,
                "tmax_event": r.tmax_event_c,
                "station": r.station_id or None,
                "provenance": r.provenance,
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
    n_resolved = event_table["tmax_event"].notna().sum()
    assert n_resolved >= MIN_RESOLVED, (
        f"Cascade resolved only {n_resolved} of {len(event_table)} verified "
        f"rows; expected >= {MIN_RESOLVED}. Misses are expected only for "
        f"pre-1836 non-British events (Paris 1871 → needs Paris Observatory, "
        f"Chicago 1919 → meteostat coverage thin, LAX 1965 → likewise)."
    )


def test_resolved_rows_have_source(event_table):
    """Every resolved row must report the source that produced both readings."""
    resolved = event_table.dropna(subset=["tmax_event"])
    missing = resolved[resolved["station"].isna() | (resolved["station"] == "")]
    assert missing.empty, (
        "Rows with a non-null tmax_event but no source id: "
        f"{list(missing['event_id'])}."
    )


def test_baseline_window_has_enough_data(event_table):
    resolved = event_table.dropna(subset=["tmax_event"])
    short = resolved[resolved["baseline_n"] < MIN_BASELINE_DAYS]
    if not short.empty:
        rows = "\n".join(
            f"  {r.event_id}: only {r.baseline_n} baseline days "
            f"({r.provenance})"
            for r in short.itertuples()
        )
        pytest.fail(
            f"{len(short)} resolved events have baseline windows with "
            f"< {MIN_BASELINE_DAYS} days:\n{rows}"
        )


def test_baseline_std_is_plausible(event_table):
    resolved = event_table.dropna(subset=["tmax_event"])
    bad = resolved[
        resolved["baseline_std"].isna()
        | (resolved["baseline_std"] <= 0)
        | (resolved["baseline_std"] > 30)
    ]
    assert bad.empty, (
        "Baseline SD implausible for: "
        f"{list(zip(bad['event_id'], bad['baseline_std'], strict=False))}."
    )
