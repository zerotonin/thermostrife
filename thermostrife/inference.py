# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — inference                                        ║
# ║  « case-crossover null + conditional logit + permutation »       ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Primary: time-stratified case-crossover (Lee et al. 2023).      ║
# ║  Each event's control set = all days at the same station,        ║
# ║  same calendar month, in years event_year ± 5, excluding         ║
# ║  the event window ± 7 days.                                      ║
# ║                                                                  ║
# ║  Reports OR per °C above local-month baseline (conditional       ║
# ║  logit) and a stratified permutation p-value as backup, plus a   ║
# ║  Burke-2015-style 1σ rescaling for cross-study comparison.       ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Case-crossover null model + H1 descriptive tests + 1σ rescaling.

The H1 tests (Wilcoxon signed-rank, sign, bootstrap CI) are ports of
the original ``analysis.py`` scaffold kept under ``_legacy/``; the H2
case-crossover engine is the headline contribution of this module.
All tests run unconditionally on every event regardless of
significance, following the project rule that decision logic belongs
in interpretation, not in the pipeline.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats

from .constants import N_BOOTSTRAP, N_PERMUTATION, RNG_SEED

# ─────────────────────────────────────────────────────────────────
#  H1: one-sample tests on event-day anomalies
# ─────────────────────────────────────────────────────────────────


def wilcoxon_signed_rank(anomaly: np.ndarray) -> dict:
    """One-sided Wilcoxon signed-rank that median(anomaly) > 0."""
    anomaly = np.asarray(anomaly, dtype=float)
    anomaly = anomaly[~np.isnan(anomaly)]
    if len(anomaly) < 5:
        return {"skipped": True, "reason": f"n={len(anomaly)} too small"}
    res = stats.wilcoxon(anomaly, alternative="greater", zero_method="wilcox")
    return {
        "n": int(len(anomaly)),
        "statistic": float(res.statistic),
        "pvalue": float(res.pvalue),
        "median": float(np.median(anomaly)),
    }


def sign_test(anomaly: np.ndarray) -> dict:
    """Binomial sign test on P(anomaly > 0) > 0.5."""
    anomaly = np.asarray(anomaly, dtype=float)
    anomaly = anomaly[~np.isnan(anomaly)]
    positives = int(np.sum(anomaly > 0))
    n_nonzero = int(np.sum(anomaly != 0))
    if n_nonzero < 5:
        return {"skipped": True, "reason": f"only {n_nonzero} non-zero anomalies"}
    res = stats.binomtest(positives, n_nonzero, p=0.5, alternative="greater")
    return {
        "n_nonzero": n_nonzero,
        "n_positive": positives,
        "proportion_positive": positives / n_nonzero,
        "pvalue": float(res.pvalue),
    }


def bootstrap_mean_ci(
    anomaly: np.ndarray,
    n_boot: int = N_BOOTSTRAP,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> dict:
    """Bootstrap percentile CI for the mean anomaly."""
    if rng is None:
        rng = np.random.default_rng(RNG_SEED)
    anomaly = np.asarray(anomaly, dtype=float)
    anomaly = anomaly[~np.isnan(anomaly)]
    if len(anomaly) < 5:
        return {"skipped": True, "reason": f"n={len(anomaly)} too small"}
    n = len(anomaly)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = anomaly[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {
        "n": n,
        "mean": float(anomaly.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_boot": n_boot,
    }


# ─────────────────────────────────────────────────────────────────
#  Daylight-hours covariate  « solar geometry, no extra deps »
# ─────────────────────────────────────────────────────────────────


def daylight_hours(lat_deg: float, when: date) -> float:
    """Closed-form solar daylight hours for ``when`` at latitude ``lat_deg``.

    Uses the standard astronomical-twilight-free approximation
    (sunrise/sunset by solar declination); accurate to ~10 min outside
    the polar circles, which is well inside the noise of our daily-Tmax
    inference and avoids a hard dependency on ``astral``.

    Returns:
        Daylight in hours.  0.0 at polar night, 24.0 at polar day.
    """
    doy = when.timetuple().tm_yday
    decl = 23.44 * math.sin(math.radians(360 / 365 * (doy - 81)))
    lat = math.radians(lat_deg)
    decl_r = math.radians(decl)
    cos_h = -math.tan(lat) * math.tan(decl_r)
    if cos_h <= -1.0:
        return 24.0
    if cos_h >= 1.0:
        return 0.0
    return (math.degrees(math.acos(cos_h)) * 2.0) / 15.0


# ─────────────────────────────────────────────────────────────────
#  Case-crossover frame  « assemble (case + controls) per event »
# ─────────────────────────────────────────────────────────────────


def build_case_crossover_frame(
    events: list[dict],
) -> pd.DataFrame:
    """Stack per-event case + control rows into one long DataFrame.

    Each ``events`` element must contain:

    - ``event_id`` (str): stratum identifier.
    - ``lat`` (float), ``lon`` (float): for the daylight covariate.
    - ``when`` (date): event day.
    - ``tmax_event_c`` (float): event-day Tmax (the case row).
    - ``baseline`` (DataFrame): one row per control day, index = date,
      column ``tmax`` in °C.

    Returns a long DataFrame with columns
    ``[event_id, day, is_case, tmax_c, daylight_h]``, one row per
    (event, day).  Cases get ``is_case = 1``; controls get ``0``.
    """
    frames = []
    for e in events:
        eid = e["event_id"]
        lat = e["lat"]
        when = e["when"]
        baseline = e["baseline"]
        if baseline is None or len(baseline) == 0:
            continue
        # Controls (one row per baseline day)
        ctrl = pd.DataFrame({
            "event_id": eid,
            "day": baseline.index,
            "is_case": 0,
            "tmax_c": baseline["tmax"].values,
        })
        ctrl["daylight_h"] = [daylight_hours(lat, d) for d in ctrl["day"]]
        # Case (event day)
        case = pd.DataFrame({
            "event_id": [eid],
            "day": [when],
            "is_case": [1],
            "tmax_c": [e["tmax_event_c"]],
            "daylight_h": [daylight_hours(lat, when)],
        })
        frames.append(pd.concat([case, ctrl], ignore_index=True))
    if not frames:
        return pd.DataFrame(columns=["event_id", "day", "is_case", "tmax_c", "daylight_h"])
    return pd.concat(frames, ignore_index=True)


# ─────────────────────────────────────────────────────────────────
#  H2: case-crossover  « primary headline test »
# ─────────────────────────────────────────────────────────────────


def case_crossover_conditional_logit(
    frame: pd.DataFrame,
    *,
    covariates: list[str] | None = None,
) -> dict:
    """Conditional logistic regression on matched case-control sets.

    Fits

        logit P(case | event_id) = β · tmax_c + γ · covariates

    using a per-event-id stratum (conditional likelihood); the stratum
    intercepts are integrated out.  ``exp(β)`` is the odds ratio of
    uprising-on-this-day per +1 °C above the local same-month baseline.

    Args:
        frame:      Output of :func:`build_case_crossover_frame`.
        covariates: Extra columns to include alongside ``tmax_c``
                    (default: ``["daylight_h"]``).

    Returns:
        Dict with the headline estimates and metadata.
    """
    from statsmodels.discrete.conditional_models import ConditionalLogit

    if frame.empty:
        return {"skipped": True, "reason": "empty case-crossover frame"}
    if covariates is None:
        covariates = ["daylight_h"]

    cols = ["tmax_c", *covariates]
    work = frame.dropna(subset=[*cols, "is_case", "event_id"]).copy()
    # Drop strata that lost their case row after NA filtering.
    keep = work.groupby("event_id")["is_case"].sum() > 0
    work = work[work["event_id"].isin(keep[keep].index)]
    if work.empty:
        return {"skipped": True, "reason": "no event_id retains a case row"}

    model = ConditionalLogit(
        endog=work["is_case"].astype(int).values,
        exog=work[cols].astype(float).values,
        groups=work["event_id"].astype(str).values,
    )
    result = model.fit(disp=0)
    beta = float(result.params[0])
    se = float(result.bse[0])
    z = beta / se if se > 0 else float("nan")
    # One-sided p (we pre-registered β > 0; report two-sided as well)
    p_one_sided = 1.0 - stats.norm.cdf(z) if not math.isnan(z) else float("nan")
    p_two_sided = 2.0 * (1.0 - stats.norm.cdf(abs(z))) if not math.isnan(z) else float("nan")
    return {
        "n_events": int(work["event_id"].nunique()),
        "n_rows": int(len(work)),
        "covariates": covariates,
        "beta_per_C": beta,
        "se_per_C": se,
        "or_per_C": float(math.exp(beta)),
        "or_ci95_low": float(math.exp(beta - 1.96 * se)),
        "or_ci95_high": float(math.exp(beta + 1.96 * se)),
        "pvalue_one_sided": float(p_one_sided),
        "pvalue_two_sided": float(p_two_sided),
        "covariate_betas": {
            name: float(b) for name, b in zip(cols[1:], result.params[1:], strict=False)
        },
    }


# ─────────────────────────────────────────────────────────────────
#  Stratified permutation  « non-parametric backup »
# ─────────────────────────────────────────────────────────────────


def stratified_permutation(
    frame: pd.DataFrame,
    n_perm: int = N_PERMUTATION,
    rng: np.random.Generator | None = None,
) -> dict:
    """Within-event label-shuffle test on the mean case-vs-control gap.

    Under H0 the case-day Tmax is exchangeable with the baseline-day
    Tmax within the same event stratum.  For each event we shuffle the
    case label across (case + controls), compute the (event-mean of
    case-Tmax) minus (event-mean of control-Tmax), and average over
    events.

    Two-sided p = fraction of permutations whose absolute statistic is
    ≥ the observed statistic.
    """
    if rng is None:
        rng = np.random.default_rng(RNG_SEED + 3)
    work = frame.dropna(subset=["tmax_c", "is_case", "event_id"]).copy()
    if work.empty:
        return {"skipped": True, "reason": "empty frame"}

    # Per-event Tmax arrays
    per_event = []
    for _eid, grp in work.groupby("event_id"):
        if grp["is_case"].sum() != 1:
            continue
        per_event.append((grp["tmax_c"].to_numpy(), grp["is_case"].to_numpy().astype(int)))

    if not per_event:
        return {"skipped": True, "reason": "no event has exactly one case row"}

    def stat(case_labels_per_event):
        # Each event contributes (case_tmax - mean_of_controls_tmax);
        # aggregate by mean across events.
        diffs = []
        for (tmaxs, labels) in case_labels_per_event:
            ev = tmaxs[labels == 1].mean()
            ct = tmaxs[labels == 0].mean()
            diffs.append(ev - ct)
        return float(np.mean(diffs))

    observed = stat(per_event)

    perm_stats = np.empty(n_perm)
    for i in range(n_perm):
        shuffled = []
        for (tmaxs, _orig) in per_event:
            new_labels = np.zeros_like(_orig)
            new_labels[rng.integers(0, len(tmaxs))] = 1
            shuffled.append((tmaxs, new_labels))
        perm_stats[i] = stat(shuffled)
    p_two_sided = float(np.mean(np.abs(perm_stats) >= abs(observed)))
    p_one_sided = float(np.mean(perm_stats >= observed))
    return {
        "n_events": len(per_event),
        "n_perm": n_perm,
        "observed_diff_C": observed,
        "pvalue_one_sided": p_one_sided,
        "pvalue_two_sided": p_two_sided,
    }


# ─────────────────────────────────────────────────────────────────
#  Burke-2015-style 1σ rescaling
# ─────────────────────────────────────────────────────────────────


def hsiang_sigma_rescaled(
    events: list[dict],
) -> dict:
    """Per-event z-score (event - baseline_mean) / baseline_std, averaged.

    Following Burke, Hsiang & Miguel (2015), expressing each event's
    anomaly as a multiple of its own baseline-window standard deviation
    makes effects comparable across stations and climates.  Their
    headline number for interpersonal violence is +2.4 % per 1 σ
    contemporaneous warming.

    Returns the mean z across events, a bootstrap 95 % CI, and the
    fraction of events with z > 0.
    """
    zs = []
    for e in events:
        baseline = e.get("baseline")
        if baseline is None or len(baseline) < 2:
            continue
        bmean = float(baseline["tmax"].mean())
        bstd = float(baseline["tmax"].std(ddof=1))
        if bstd <= 0:
            continue
        ev = e.get("tmax_event_c")
        if ev is None:
            continue
        zs.append((float(ev) - bmean) / bstd)
    if not zs:
        return {"skipped": True, "reason": "no events with usable baseline"}
    z_arr = np.array(zs)
    rng = np.random.default_rng(RNG_SEED + 4)
    n = len(z_arr)
    boot = rng.choice(z_arr, size=(N_BOOTSTRAP, n), replace=True).mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return {
        "n_events": n,
        "mean_z": float(z_arr.mean()),
        "median_z": float(np.median(z_arr)),
        "ci95_low_z": float(lo),
        "ci95_high_z": float(hi),
        "fraction_positive": float((z_arr > 0).mean()),
    }
