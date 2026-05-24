# Stratified H2 case-crossover — sensitivity analysis

All rows are independent re-fits of the conditional-logit case-crossover estimator restricted to the named stratum; the daylight covariate is dropped in stratified fits to avoid the collinearity it picks up at small n.

## Headline (all resolved violent uprisings)

- OR per +1 °C: **1.089** (95 % CI 1.030–1.151)
- one-sided p = **0.001236**, two-sided p = 0.002471
- n events = 104, n rows = 30589

## Stratified by Era

| Stratum | n events | OR per +1 °C (95 % CI) | one-sided p |
|---------|---------:|------------------------|------------:|
| era1_1750_1850 | 10 | 1.134 (0.908–1.416) | 0.1337 |
| era2_1850_1920 | 19 | 1.045 (0.898–1.217) | 0.2834 |
| era3_1920_1970 | 22 | 1.099 (0.986–1.225) | 0.04362 |
| era4_1970_2000 | 23 | 1.133 (1.004–1.278) | 0.02166 |
| era5_2000_2026 | 30 | 1.066 (0.972–1.169) | 0.08859 |

## Stratified by Hemisphere

| Stratum | n events | OR per +1 °C (95 % CI) | one-sided p |
|---------|---------:|------------------------|------------:|
| Northern | 98 | 1.090 (1.031–1.153) | 0.001282 |
| Southern | 6 | 1.056 (0.763–1.462) | 0.371 |

## Stratified by Duration

| Stratum | n events | OR per +1 °C (95 % CI) | one-sided p |
|---------|---------:|------------------------|------------:|
| long_multi_day_4_plus | 58 | 1.074 (1.001–1.153) | 0.02278 |
| short_multi_day_2_3 | 27 | 1.164 (1.039–1.304) | 0.004444 |
| single_day | 19 | 1.033 (0.896–1.192) | 0.3263 |

## Stratified by Event type

| Stratum | n events | OR per +1 °C (95 % CI) | one-sided p |
|---------|---------:|------------------------|------------:|
| civilian_uprising_or_riot | 78 | 1.096 (1.031–1.166) | 0.001763 |
| military_coup_or_putsch | 5 | 1.012 (0.809–1.267) | 0.458 |
| prison_riot | 2 | — (only 2 events (< 5)) | — |
| state_massacre_or_genocide | 19 | 1.065 (0.910–1.245) | 0.2164 |

