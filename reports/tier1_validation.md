# Tier-1 (meteostat) validation against hand-verified rows

- Validation set size: **13**
- Resolved at Tier 1: **10 / 13**
- MAE on resolved rows: **2.38 °C**
- Median |Δ| on resolved rows: **1.40 °C**
- Within 0.5 °C: **2** · within 1.5 °C: **5**

## Per-row results

| event_id | date | manual | Tier 1 | Δ | station | note |
|----------|------|-------:|-------:|--:|---------|------|
| `1871_paris_commune` | 1871-05-21 | 22.0 | — | — | `—` | all available tiers returned no value |
| `1916_easter_rising` | 1916-04-24 | 12.5 | 16.7 | +4.20 | `03969` | meteostat: 03969 |
| `1919_chicago_red_summer` | 1919-07-27 | 35.0 | — | — | `—` | all available tiers returned no value |
| `1943_detroit_race_riot` | 1943-06-20 | 32.8 | 31.7 | -1.10 | `71538` | meteostat: 71538 |
| `1965_watts_riots` | 1965-08-11 | 33.3 | — | — | `—` | all available tiers returned no value |
| `1967_detroit_riots` | 1967-07-23 | 32.2 | 30.6 | -1.60 | `71538` | meteostat: 71538 |
| `1968_mlk_dc_riots` | 1968-04-04 | 21.0 | 20.6 | -0.40 | `74594` | meteostat: 74594 |
| `1969_stonewall` | 1969-06-28 | 35.6 | 34.4 | -1.20 | `72503` | meteostat: 72503 |
| `2014_euromaidan` | 2014-02-18 | -1.0 | 8.0 | +9.00 | `33345` | meteostat: 33345 |
| `2020_george_floyd_minneapolis` | 2020-05-26 | 27.0 | 26.1 | -0.90 | `KMIC0` | meteostat: KMIC0 |
| `2021_capitol_storming` | 2021-01-06 | 4.0 | 6.7 | +2.70 | `72405` | meteostat: 72405 |
| `2023_france_nahel_riots` | 2023-06-27 | 25.0 | 25.0 | +0.00 | `07156` | meteostat: 07156 |
| `2024_new_caledonia_riots` | 2024-05-13 | 24.0 | 26.7 | +2.70 | `91592` | meteostat: 91592 |

## Outliers (|Δ| > 2 °C)

- `1916_easter_rising` (1916-04-24): manual 12.5 °C, Tier 1 16.7 °C at `03969` (Δ +4.20 °C).
- `2014_euromaidan` (2014-02-18): manual -1.0 °C, Tier 1 8.0 °C at `33345` (Δ +9.00 °C).
- `2021_capitol_storming` (2021-01-06): manual 4.0 °C, Tier 1 6.7 °C at `72405` (Δ +2.70 °C).
- `2024_new_caledonia_riots` (2024-05-13): manual 24.0 °C, Tier 1 26.7 °C at `91592` (Δ +2.70 °C).

Investigation actions: confirm the manual value's primary source, then either add a `station_hint` to `event_geo.csv` to pin the canonical station, or update the manual value in the curated CSV if the original citation does not survive scrutiny.
