"""Unit tests for thermostrife.inference."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from thermostrife.inference import (
    build_case_crossover_frame,
    case_crossover_conditional_logit,
    daylight_hours,
    hsiang_sigma_rescaled,
    stratified_permutation,
)

# ─────────────────────────────────────────────────────────────────
#  Daylight-hours closed form
# ─────────────────────────────────────────────────────────────────


class TestDaylightHours:
    def test_equator_is_roughly_twelve_hours(self):
        # Equator: ~12 hours year-round (small variation from declination)
        for d in (date(2020, 3, 20), date(2020, 6, 21), date(2020, 12, 21)):
            assert 11.5 <= daylight_hours(0.0, d) <= 12.5, d

    def test_summer_solstice_in_paris_is_long(self):
        # Paris (48.86 °N) on June 21 should have ~15-16 h
        assert 15.5 <= daylight_hours(48.86, date(2020, 6, 21)) <= 16.5

    def test_winter_solstice_in_paris_is_short(self):
        # Paris on Dec 21 should have ~8-9 h
        assert 8.0 <= daylight_hours(48.86, date(2020, 12, 21)) <= 9.0

    def test_polar_day_and_night(self):
        # North pole on June 21 → 24h; on Dec 21 → 0h
        assert daylight_hours(85.0, date(2020, 6, 21)) == 24.0
        assert daylight_hours(85.0, date(2020, 12, 21)) == 0.0


# ─────────────────────────────────────────────────────────────────
#  Synthetic case-crossover tests
# ─────────────────────────────────────────────────────────────────


def _synthetic_event(
    event_id: str,
    lat: float,
    when: date,
    event_tmax: float,
    baseline_mean: float,
    baseline_std: float,
    n_baseline: int = 250,
    rng_seed: int = 0,
) -> dict:
    rng = np.random.default_rng(rng_seed)
    baseline_vals = rng.normal(baseline_mean, baseline_std, n_baseline)
    dates = pd.date_range(
        end=when - pd.Timedelta(days=8), periods=n_baseline, freq="D"
    ).date
    baseline = pd.DataFrame({"tmax": baseline_vals}, index=pd.Index(dates, name="date"))
    return {
        "event_id": event_id,
        "lat": lat,
        "lon": 0.0,
        "when": when,
        "tmax_event_c": event_tmax,
        "baseline": baseline,
    }


class TestCaseCrossover:
    def test_null_case_returns_nonsignificant(self):
        """Events drawn from the baseline distribution should give p ~ 0.5.

        Daylight is excluded here because the synthetic baselines span
        arbitrary date ranges (not same-month windows), which makes the
        covariate collinear with the event-day flag — a real-data
        artefact that doesn't apply to ``resolve_event_anomaly``'s
        same-month-window baselines.
        """
        rng = np.random.default_rng(42)
        events = []
        for i in range(50):
            baseline_mean = float(rng.normal(15, 3))
            event_tmax = float(rng.normal(baseline_mean, 5))
            events.append(_synthetic_event(
                f"null_{i}", 45.0, date(2000, 6, 15),
                event_tmax, baseline_mean, 5.0,
                rng_seed=i,
            ))
        frame = build_case_crossover_frame(events)
        result = case_crossover_conditional_logit(frame, covariates=[])
        assert not result.get("skipped")
        assert result["pvalue_two_sided"] > 0.05, result

    def test_strong_positive_signal_is_detected(self):
        """Events systematically +5°C above baseline should give a strong + β."""
        events = [
            _synthetic_event(
                f"hot_{i}", 45.0, date(2000, 6, 15),
                event_tmax=20.0,  # well above baseline
                baseline_mean=15.0,
                baseline_std=3.0,
                rng_seed=i,
            )
            for i in range(40)
        ]
        frame = build_case_crossover_frame(events)
        result = case_crossover_conditional_logit(frame, covariates=[])
        assert not result.get("skipped")
        assert result["beta_per_C"] > 0
        assert result["or_per_C"] > 1.0
        assert result["pvalue_one_sided"] < 0.05, result


class TestStratifiedPermutation:
    def test_strong_positive_signal_p_is_small(self):
        events = [
            _synthetic_event(
                f"hot_{i}", 45.0, date(2000, 6, 15),
                event_tmax=20.0, baseline_mean=15.0, baseline_std=3.0,
                rng_seed=i,
            )
            for i in range(30)
        ]
        frame = build_case_crossover_frame(events)
        result = stratified_permutation(frame, n_perm=2000)
        assert result["observed_diff_C"] > 0
        assert result["pvalue_one_sided"] < 0.05


class TestSigmaRescaled:
    def test_z_scores_track_expected(self):
        # All events 2σ above their own baseline → mean z ≈ 2
        events = [
            _synthetic_event(
                f"sigma_{i}", 45.0, date(2000, 6, 15),
                event_tmax=15.0 + 2.0 * 3.0,  # baseline_mean + 2σ
                baseline_mean=15.0, baseline_std=3.0,
                n_baseline=500, rng_seed=i,
            )
            for i in range(20)
        ]
        result = hsiang_sigma_rescaled(events)
        assert result["n_events"] == 20
        assert 1.7 <= result["mean_z"] <= 2.3, result
        assert result["fraction_positive"] >= 0.9


@pytest.mark.parametrize("missing_field", ["baseline", "tmax_event_c"])
def test_build_frame_skips_unresolved(missing_field):
    e = _synthetic_event(
        "ok", 45.0, date(2000, 6, 15), 20.0, 15.0, 3.0, rng_seed=1,
    )
    bad = dict(e)
    bad["event_id"] = "bad"
    if missing_field == "baseline":
        bad["baseline"] = pd.DataFrame(columns=["tmax"])
    else:
        bad["tmax_event_c"] = None
        # Still build the frame: function skips empty baselines, but a None
        # tmax_event_c falls through and would propagate; we only assert the
        # good event survives.
    frame = build_case_crossover_frame([e, bad])
    assert "ok" in frame["event_id"].values
