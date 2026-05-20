# ThermoStrife — data

Three layers, conventional:

| Layer | Tracked? | Purpose |
|-------|----------|---------|
| `raw/` | yes | Curated source-of-truth (the 112-event panel + any future hand-curated additions). Never overwrite — write to `interim/` instead. |
| `interim/` | no (gitkeep only) | Backfilled / merged outputs from the pipeline (`thermostrife-backfill`). Reproducible from `raw/`. |
| `processed/` | no (gitkeep only) | Analysis-ready frames consumed by `thermostrife-analyse`. Reproducible from `interim/`. |

## `raw/uprisings_temperature.csv`

112 violent uprisings, revolutions, massacres, and prison revolts 1750–2026.
RFC-4180 / UTF-8 / `NA` for missing.

Column schema (selected, see the file itself for the full set):

| Column | Meaning |
|--------|---------|
| `event_id` | Stable slug, e.g. `1819_peterloo` |
| `start_date` / `end_date` | ISO-8601; single-day events have `start == end` |
| `city` / `country` | Best modern administrative name |
| `est_deaths_low` / `est_deaths_high` | Scholarly casualty range |
| `day_temp_C` | Day-of-event Tmax. `NA` if not yet backfilled. |
| `decade_mean_temp_C` | Currently a mix of period-correct values and modern-climatology proxies — the `thermostrife-backfill` CLI replaces these with ±5-year same-station means. |
| `anomaly_C` | `day_temp_C − decade_mean_temp_C` |
| `qualitative_weather` | Contemporary description ("hot afternoon", "pouring rain", …) |
| `temp_data_source` | Citation / station ID for `day_temp_C` |
| `event_data_source` | Citation(s) for the event itself |
| `era` | One of `era1_1750_1850` … `era5_2000_2026` |
| `notes` | Free-text caveats |

The curated CSV is the authoritative input to the pipeline. Edits to the
event list, casualties, or qualitative weather belong here. Temperatures
backfilled by the pipeline live in `interim/uprisings_backfilled.csv` and
should never be written back to `raw/`.

## Provenance

The dataset was compiled from Wikipedia, Britannica, USHMM, South African
History Online, BlackPast, Encyclopedia of Arkansas, the Detroit Historical
Society, the National Security Archive, and the historiographic monographs
cited in each row's `event_data_source` column.
