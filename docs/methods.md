# Statistical methods

Pre-registered analysis plan, written before the dataset is frozen.
Adapted from `analysis_methods.md` in the project notebook.

## 1 — Core question and primary test

Does the mean temperature anomaly on uprising days exceed zero, after
matching each event to its local climate?

Because the table is small (~100 events), heavy-tailed, and likely
non-normal, we do not rely on a one-sample t-test. Instead we run two
complementary tests on `anomaly_C = day_temp_C − decade_mean_temp_C`:

- **Wilcoxon signed-rank** (one-sided, H1: median anomaly > 0). Robust to
  outliers, makes no normality assumption.
- **Binomial sign test** on `P(anomaly_C > 0) > 0.5`. Discards magnitude
  entirely and is therefore the most conservative; immune to era-dependent
  measurement precision.

We report both. Agreement strengthens the claim; disagreement (e.g.
signed-rank significant, sign test not) implies a few large positive
outliers are driving the result and the conclusion should be tempered.

A **bootstrap 95 % CI on the mean anomaly** (10 000 resamples) is the
headline effect-size estimate.

## 2 — Why a naive t-test is insufficient

1. **Selection bias on famous events.** Events ended up in the table
   because historians recorded them; events without a surviving weather
   record (more common in cold/rainy weeks when fewer observers were
   outside writing diaries?) are missing. The sample is not random.
2. **Heteroscedasticity by era.** A 2010 station reading has ~0.1 °C
   uncertainty; an 1830 reconstruction has ~1–2 °C uncertainty.
   Equal-weighting treats these as equally informative; a rank-based test
   is far less distorted.
3. **Reference-period bias.** The naïve "decade-mean" sliding upward over
   time biases the test against H1 for recent events and toward H1 for
   early events. We replace it with a period-correct ±5-year same-station
   baseline (see {doc}`pipeline`).

## 3 — Deconfounding the outdoor-opportunity confound

The main alternative hypothesis is *not* "no effect" — it is "uprisings
happen when people are outside, and people are outside when it's warm,
so a positive anomaly is mechanically expected even with zero
aggression effect."

Six strategies, in order of increasing analytic power:

### (a) Matched control days — H2, the headline

For each event (station L, date D), draw the control set from the same
station, same calendar month, ± 5 years, excluding the event window ± 7
days. Event-day anomalies are compared against the pooled control
distribution via **conditional logistic regression** with an event-stratum
random effect (case-crossover design, Lee et al. 2023).

### (b) Non-violent crowd events as a parallel control

Compile a parallel list of large peaceful outdoor gatherings (World Cup
finals, Olympic opening ceremonies, royal jubilees, May Day rallies,
papal Masses, Woodstock 1969). If these also occur on positive-anomaly
days, the signal is opportunity, not aggression. *Phase 2 work.*

### (c) Indoor violence as a within-domain control

For the post-1970 subset, compare anomaly distributions for outdoor
uprisings vs. prison riots, ER assault admissions, domestic-violence
call volumes. Heilmann, Kahn & Tang 2021 is the precedent.

### (d) Day-of-event vs surrounding days — H3

Compute mean anomaly for t-7, t-2, t-1, t, t+1, t+2, t+7. A flat profile
across the week argues for "hot summer" rather than "hot day triggers
riot."

### (e) Daylight-hours covariate

Solar geometry → hours of daylight at event latitude and date. Included
in the conditional-logit model. If the anomaly effect survives daylight
control, heat is doing work beyond "longer days = more opportunity."

### (f) Era and regional fixed effects

```
anomaly_i = α_era + α_region + β · event_dummy + γ · daylight_hours + ε_i
```

`event_dummy` is 1 for uprising days, 0 for matched control days. β is
the heat-aggression coefficient net of secular warming, regional climate,
and daylight.

## 4 — Pre-registered hypotheses

- **H1.** `mean(anomaly | event) > 0`. Wilcoxon + sign on event rows.
- **H2.** `mean(anomaly | event) > mean(anomaly | matched control)`.
  **Headline.** Conditional logit + stratified permutation.
- **H3.** `anomaly_t > anomaly_{t±7}`. Within-event paired test.

H2 is the headline. H1 alone cannot distinguish heat from opportunity.
H3 is the secondary within-event check.

## 5 — Multiple comparisons

~6–8 tests total. We treat H2 as the single confirmatory test (α = 0.05)
and H1 / H3 as auxiliary. We report **both raw p-values and
Bonferroni-adjusted p-values** for the full battery.

## 6 — Power

With N = 50 events, anomaly SD ~3 °C, α = 0.05, one-sample two-sided t:
detectable effect size d = 0.4 at 80 % power, i.e. a true mean anomaly
of ~1.2 °C. **Effects smaller than ~1 °C on the mean will not be reliably
detected.** N = 100 with verified daily temperatures drops the detectable
effect to about 0.85 °C.

## 7 — Limitations

- **Small N (~100).** CIs will be wide.
- **Selection on famous events** — no statistical fix; only the
  peaceful-crowd parallel control (§3b) addresses it.
- **Pre-1900 daily temperatures are reconstructions** with ~1–2 °C
  uncertainty. We do not propagate measurement error formally; we
  mitigate by using rank-based tests.
- **"Uprising" is heterogeneous** — peasant revolts, urban riots,
  military coups, color revolutions. Sensitivity analyses drop coups
  (which are planned indoors and weather-insensitive by mechanism).
- **One-sided tests are pre-registered.** If the observed mean anomaly
  is negative, we report it descriptively but do not flip the test.

## 8 — References

- Lee, S. *et al.* (2023). Assault deaths and ambient temperature in
  Seoul. *Int. J. Environ. Res. Public Health* **20**: 6256.
- Heilmann, K., Kahn, M. E. & Tang, C. K. (2021). The urban crime and
  heat gradient in high and low poverty areas. *J. Public Econ.*
  **197**: 104408.
- Burke, M., Hsiang, S. M. & Miguel, E. (2015). Climate and conflict.
  *Annu. Rev. Econ.* **7**: 577–617.
- Ranson, M. (2014). Crime, weather, and climate change.
  *J. Environ. Econ. Manag.* **67**: 274–302.
- Field, S. (1992). The effect of temperature on crime. *Br. J. Criminol.*
  **32**: 340–351.
