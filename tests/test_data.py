"""Schema and integrity tests for the curated uprisings CSV."""

from __future__ import annotations

import pandas as pd
import pytest

from thermostrife.constants import CURATED_CSV


REQUIRED_COLUMNS = {
    "event_id", "event_name", "city", "country",
    "start_date", "end_date",
    "est_deaths_low", "est_deaths_high",
    "day_temp_C", "decade_mean_temp_C", "anomaly_C",
    "qualitative_weather", "temp_data_source", "event_data_source",
    "era", "notes",
}


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(CURATED_CSV)


def test_csv_loads(df):
    assert len(df) > 100  # we know it's 112 today; future-proof the bound


def test_required_columns_present(df):
    missing = REQUIRED_COLUMNS - set(df.columns)
    assert not missing, f"missing columns: {sorted(missing)}"


def test_event_id_is_unique(df):
    assert df["event_id"].is_unique


def test_dates_parseable(df):
    parsed = pd.to_datetime(df["start_date"], errors="coerce")
    assert parsed.isna().sum() == 0


def test_end_date_not_before_start(df):
    start = pd.to_datetime(df["start_date"])
    end = pd.to_datetime(df["end_date"])
    assert (end >= start).all()


def test_era_values_are_known(df):
    known = {"era1_1750_1850", "era2_1850_1920", "era3_1920_1970",
             "era4_1970_2000", "era5_2000_2026"}
    assert set(df["era"].unique()) <= known


def test_anomaly_consistent_where_both_present(df):
    sub = df.dropna(subset=["day_temp_C", "decade_mean_temp_C", "anomaly_C"])
    diff = (sub["day_temp_C"] - sub["decade_mean_temp_C"]) - sub["anomaly_C"]
    assert diff.abs().max() < 0.1
