"""Tier-1 validation gate against the hand-verified rows.

Marked ``network`` because it hits the meteostat upstream on the first
run; subsequent runs are served from the parquet cache in
``data/cache/meteostat/``.  Skip in offline CI with
``pytest -m 'not network'``.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from thermostrife.constants import CURATED_CSV, EVENT_GEO_CSV
from thermostrife.lookup import resolve

pytestmark = pytest.mark.network


# Gate thresholds — tightened as Sprint 1.5 (station-hint curation) lands.
MIN_RESOLVED = 8
MAX_MAE_C = 3.0
MAX_MEDIAN_ABS_DELTA_C = 1.5
MIN_WITHIN_1_5C = 4


@pytest.fixture(scope="module")
def validation_frame() -> pd.DataFrame:
    warnings.filterwarnings("ignore")
    curated = pd.read_csv(CURATED_CSV).set_index("event_id")
    geo = pd.read_csv(EVENT_GEO_CSV).set_index("event_id")
    rows = []
    for event_id, grow in geo.iterrows():
        crow = curated.loc[event_id]
        when = pd.to_datetime(crow["start_date"]).date()
        res = resolve(grow["lat"], grow["lon"], when, radius_km=60)
        rows.append(
            {
                "event_id": event_id,
                "manual_C": float(crow["day_temp_C"]),
                "tier1_C": res.tmax_c,
                "delta_C": (res.tmax_c - float(crow["day_temp_C"]))
                if res.tmax_c is not None
                else None,
            }
        )
    return pd.DataFrame(rows)


def test_minimum_rows_resolve(validation_frame):
    n_resolved = validation_frame["tier1_C"].notna().sum()
    assert n_resolved >= MIN_RESOLVED, (
        f"Tier 1 resolved only {n_resolved} / {len(validation_frame)} "
        f"verified rows; expected ≥ {MIN_RESOLVED}.  Check meteostat upstream "
        f"or station-hint coverage in event_geo.csv."
    )


def test_mae_within_threshold(validation_frame):
    deltas = validation_frame["delta_C"].dropna()
    mae = deltas.abs().mean()
    assert mae < MAX_MAE_C, (
        f"Tier 1 MAE = {mae:.2f} °C exceeds threshold {MAX_MAE_C} °C.  "
        f"Review reports/tier1_validation.md for outliers and either pin a "
        f"station_hint or update the manual value."
    )


def test_median_close_to_zero(validation_frame):
    deltas = validation_frame["delta_C"].dropna()
    median = deltas.abs().median()
    assert median < MAX_MEDIAN_ABS_DELTA_C, (
        f"Median |Δ| = {median:.2f} °C exceeds {MAX_MEDIAN_ABS_DELTA_C} °C; "
        f"the typical row is too far off the manual value."
    )


def test_enough_rows_within_tight_band(validation_frame):
    deltas = validation_frame["delta_C"].dropna()
    n_close = (deltas.abs() < 1.5).sum()
    assert n_close >= MIN_WITHIN_1_5C, (
        f"Only {n_close} resolved rows are within 1.5 °C of the manual "
        f"value; expected ≥ {MIN_WITHIN_1_5C}."
    )
