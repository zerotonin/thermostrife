"""Smoke tests for thermostrife.viz.

We only assert that each figure function writes the three expected
files (SVG + PNG + CSV) and doesn't raise.  Visual content is not
asserted — the figures are review artefacts, not pass/fail gates.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless backend before pyplot is touched anywhere

import numpy as np
import pandas as pd
import pytest

from thermostrife.viz import (
    plot_anomaly_by_year,
    plot_anomaly_raincloud,
    plot_forest_h2,
    plot_null_density,
    plot_superposed_epoch,
    plot_warming_stripes_timeline,
)


@pytest.fixture
def synthetic_events_df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 60
    return pd.DataFrame({
        "event_id": [f"evt_{i:03d}" for i in range(n)],
        "year": rng.integers(1820, 2024, size=n),
        "anomaly_C": rng.normal(loc=1.0, scale=2.5, size=n),
        "provenance": rng.choice(
            ["tier1_ghcn", "tier2_hadcet_mean", "tier3_era5", "tier4_20crv3"],
            size=n,
        ),
    })


def _triple_exists(out_dir, stem):
    return all((out_dir / f"{stem}.{ext}").exists() for ext in ("svg", "png", "csv"))


def test_raincloud_writes_triple(tmp_path, synthetic_events_df):
    out = plot_anomaly_raincloud(
        synthetic_events_df, tmp_path, annotation="test annotation",
    )
    assert out.suffix == ".png"
    assert _triple_exists(tmp_path, "anomaly_raincloud")


def test_raincloud_empty_raises(tmp_path):
    empty = pd.DataFrame(columns=["event_id", "anomaly_C", "provenance"])
    with pytest.raises(ValueError):
        plot_anomaly_raincloud(empty, tmp_path)


def test_anomaly_by_year_writes_triple(tmp_path, synthetic_events_df):
    plot_anomaly_by_year(synthetic_events_df, tmp_path)
    assert _triple_exists(tmp_path, "anomaly_by_year")


def test_null_density_writes_triple(tmp_path):
    rng = np.random.default_rng(7)
    null_draws = rng.normal(0.0, 0.5, size=2000)
    plot_null_density(
        observed_stat=1.2, null_draws=null_draws, output_dir=tmp_path,
        two_sided_p=0.001,
    )
    assert _triple_exists(tmp_path, "null_density")


def test_null_density_too_few_draws_raises(tmp_path):
    with pytest.raises(ValueError):
        plot_null_density(1.0, np.array([0.1, 0.2, 0.3]), tmp_path)


def test_warming_stripes_writes_triple(tmp_path, synthetic_events_df):
    annual = pd.Series(
        np.linspace(9.0, 11.0, 200) + np.random.default_rng(0).normal(0, 0.4, 200),
        index=np.arange(1820, 2020),
        name="annual",
    )
    plot_warming_stripes_timeline(
        annual_temp=annual,
        panels={"A": synthetic_events_df, "B": synthetic_events_df.iloc[:30]},
        output_dir=tmp_path,
    )
    assert _triple_exists(tmp_path, "warming_stripes_timeline")


def test_warming_stripes_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        plot_warming_stripes_timeline(
            annual_temp=pd.Series(dtype="float64"),
            panels={"A": pd.DataFrame({"year": [], "anomaly_C": []})},
            output_dir=tmp_path,
        )


def test_superposed_epoch_writes_triple(tmp_path):
    rng = np.random.default_rng(2)
    rows = []
    for eid in range(30):
        for off in (-7, -2, -1, 0, 1, 2, 7):
            rows.append({
                "event_id": f"e_{eid}",
                "offset_days": off,
                "anomaly_C": rng.normal(1.0 if off == 0 else 0.0, 1.5),
            })
    df = pd.DataFrame(rows)
    plot_superposed_epoch({"Test panel": df}, tmp_path)
    assert _triple_exists(tmp_path, "superposed_epoch")


def test_forest_writes_triple(tmp_path):
    rows = [
        {"label": "A", "or": 1.10, "ci_low": 1.02, "ci_high": 1.19, "n": 100},
        {"label": "B", "or": 0.95, "ci_low": 0.85, "ci_high": 1.05, "n": 40},
    ]
    plot_forest_h2(rows, tmp_path)
    assert _triple_exists(tmp_path, "forest_h2")


def test_forest_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        plot_forest_h2([], tmp_path)
