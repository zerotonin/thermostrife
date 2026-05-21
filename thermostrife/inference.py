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
# ║  logit) and a stratified permutation p-value as backup.          ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Case-crossover null model + descriptive H1 tests.

The H1 tests (Wilcoxon signed-rank, sign test, bootstrap CI) are direct
ports of the original ``analysis.py`` scaffold kept under ``_legacy/``.
They run unconditionally on every event regardless of significance,
following the project rule that decision logic belongs in interpretation,
not in the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

from .constants import N_BOOTSTRAP, RNG_SEED

if TYPE_CHECKING:
    import pandas as pd

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
#  H2: case-crossover  « primary headline test »
# ─────────────────────────────────────────────────────────────────


def case_crossover_conditional_logit(
    event_table: pd.DataFrame,
    control_table: pd.DataFrame,
    *,
    covariates: list[str] | None = None,
) -> dict:
    """Conditional logistic regression on matched case-control sets.

    ``event_table`` has one row per event (the case).  ``control_table``
    has one row per matched control day, with an ``event_id`` column
    keying it back to the case.  The model is

        logit P(case | set) = β · Tmax + γ · X

    fitted with a per-event stratum (conditional likelihood).  Reports
    ``exp(β)`` as the odds ratio per °C above local-month baseline,
    with profile-likelihood 95 % CI.
    """
    raise NotImplementedError(
        "case-crossover engine awaits the matched-control assembly path "
        "in thermostrife.lookup + thermostrife.baseline."
    )


def stratified_permutation(
    event_table: pd.DataFrame,
    control_table: pd.DataFrame,
    n_perm: int = 10_000,
    rng: np.random.Generator | None = None,
) -> dict:
    """Within-event label shuffle, mean-anomaly-difference statistic."""
    raise NotImplementedError(
        "stratified permutation awaits matched-control assembly."
    )
