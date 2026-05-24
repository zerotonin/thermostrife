# ThermoStrife — inference results

Pre-registered hypothesis tests on the cascade-resolved events (**N = 104** of 112). See `docs/methods.md` for the pre-registered protocol and the data-coverage limitations behind the missing rows.

## Source-tier breakdown

- `tier1_ghcn`: **58**
- `tier4_20crv3`: **37**
- `tier3_era5`: **7**
- `tier2_hadcet_mean`: **2**

## H2 — case-crossover conditional logit (headline)

- **OR per +1 °C** above local same-month baseline: **1.089** (95 % CI 1.029 – 1.152)
- β (log-OR) per °C: +0.0851 (SE 0.0288)
- p-value: one-sided **0.001553**, two-sided 0.003105
- n strata = 104, n rows = 30589
- Covariate β values:
  - `daylight_h`: +0.0018

## H2 — stratified permutation (non-parametric backup)

- Observed (mean of event-day Tmax minus mean of control Tmax, averaged across events): **+1.053 °C**
- p-value: one-sided **0.0015**, two-sided 0.003
- n events = 104, n permutations = 10000

## σ-rescaled effect (Burke et al. 2015 currency)

- Mean z-score across events: **+0.258 σ** (95 % CI +0.059 – +0.453)
- Median z: +0.186 σ
- Fraction of events with z > 0: **57.7%**
- Burke, Hsiang & Miguel (2015) report +2.4 % interpersonal violence per 1 σ contemporaneous warming as the pooled cross-study estimate.

## H1 — descriptive (per-event anomalies)

- **Wilcoxon signed-rank** (one-sided, H1: median > 0): p = **0.005206**, median = +0.570 °C, n = 104
- **Sign test** (one-sided, H1: P(anomaly > 0) > 0.5): 60/104 positive = 57.7%; p = **0.07048**
- **Bootstrap mean anomaly**: **+1.053 °C** (95 % CI +0.375 – +1.726), n = 104, B = 10000
