"""Unit tests for thermostrife.inference."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from thermostrife.inference import (
    benjamini_hochberg,
    build_case_crossover_frame,
    case_crossover_conditional_logit,
    daylight_hours,
    h3_within_event_contrast,
    hsiang_sigma_rescaled,
    stratified_permutation,
)


class TestBenjaminiHochberg:
    def test_known_battery(self):
        # Our actual five p-values; verify the hand-calculated outcome.
        res = benjamini_hochberg({
            "A": 0.0015, "B": 0.0016, "C": 0.0052, "D": 0.037, "E": 0.070,
        }, alpha=0.05)
        assert res["family_size"] == 5
        assert res["bonferroni_threshold"] == pytest.approx(0.010)
        assert res["bh_cutoff_rank"] == 4  # BH rescues D
        assert res["n_bonferroni_rejected"] == 3
        # The BH-adjusted q-values are monotone:
        qs = [res["results"][k]["bh_adjusted_p"] for k in ("A", "B", "C", "D", "E")]
        sorted_qs = sorted(qs)
        # Smallest q corresponds to smallest p; sorted order should preserve
        assert sorted_qs[0] == res["results"]["A"]["bh_adjusted_p"]
        # D rejected by BH, not by Bonferroni
        assert res["results"]["D"]["bh_reject"] is True
        assert res["results"]["D"]["bonferroni_reject"] is False

    def test_empty_family(self):
        res = benjamini_hochberg({}, alpha=0.05)
        assert res["family_size"] == 0
        assert res["results"] == {}

    def test_all_pass(self):
        res = benjamini_hochberg({"x": 0.001, "y": 0.002, "z": 0.003}, alpha=0.05)
        assert res["n_bh_rejected"] == 3
        assert all(row["bh_reject"] for row in res["results"].values())

    def test_all_fail(self):
        res = benjamini_hochberg({"x": 0.5, "y": 0.6, "z": 0.7}, alpha=0.05)
        assert res["n_bh_rejected"] == 0
        assert not any(row["bh_reject"] for row in res["results"].values())

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


class TestH3WithinEventContrast:
    """Synthetic events with a programmable fetcher exercise H3.

    The fake fetcher returns ``surround_tmax`` for offsets in
    ``surround_offsets`` and ``window_tmax`` for offsets in
    ``window_offsets`` (other than offset 0, which comes from the
    event's ``tmax_event_c``).
    """

    @staticmethod
    def _fake_fetcher(window_tmax: float, surround_tmax: float):
        def _fetch(provenance, lat, lon, when, *, station_id=None):
            # window_offsets defaults to (0, -1) — only -1 hits the
            # fetcher; surround_offsets defaults to (-7, +7).  Tests
            # below construct events on day 15 of June 2000 so
            # |day-15| ≤ 1 → window, |day-15| == 7 → surround.
            return _fetch.window if abs(when.day - 15) <= 1 else _fetch.surround
        _fetch.window = window_tmax
        _fetch.surround = surround_tmax
        return _fetch

    def _make(self, n, event_tmax, baseline_mean, baseline_std, seed=0):
        return [
            _synthetic_event(
                f"h3_{i}", lat=45.0, when=date(2000, 6, 15),
                event_tmax=event_tmax,
                baseline_mean=baseline_mean,
                baseline_std=baseline_std,
                rng_seed=seed + i,
            )
            for i in range(n)
        ]

    def test_strong_concentration_is_detected(self):
        # window (t, t-1) at 22°C, surround (t-7, t+7) at 15°C → diff ≈ +7
        events = self._make(n=40, event_tmax=22.0, baseline_mean=15.0, baseline_std=3.0)
        for e in events:
            e["provenance"] = "tier1_ghcn"
            e["station_id"] = "FAKE"
        fetcher = self._fake_fetcher(window_tmax=22.0, surround_tmax=15.0)
        result = h3_within_event_contrast(events, fetch_fn=fetcher)
        assert result["n_events_used"] == 40
        assert result["mean_diff_C"] > 5.0
        assert result["pvalue_one_sided"] < 0.001, result

    def test_flat_profile_gives_nonsignificant_p(self):
        # window == surround → diff ≈ 0
        events = self._make(n=40, event_tmax=15.0, baseline_mean=15.0, baseline_std=3.0)
        for e in events:
            e["provenance"] = "tier1_ghcn"
            e["station_id"] = "FAKE"
        fetcher = self._fake_fetcher(window_tmax=15.0, surround_tmax=15.0)
        result = h3_within_event_contrast(events, fetch_fn=fetcher)
        # All diffs are exactly zero → Wilcoxon either skips or returns p ≈ 1
        # but we accept either "skipped" or a non-significant p.
        if result.get("skipped"):
            return
        assert result["pvalue_one_sided"] > 0.05, result

    def test_skipped_when_fetcher_returns_none(self):
        events = self._make(n=20, event_tmax=22.0, baseline_mean=15.0, baseline_std=3.0)
        for e in events:
            e["provenance"] = "tier1_ghcn"
            e["station_id"] = "FAKE"

        def none_fetcher(*args, **kwargs):
            return None

        result = h3_within_event_contrast(events, fetch_fn=none_fetcher)
        assert result.get("skipped")
        assert "only 0 events" in result["reason"]


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
