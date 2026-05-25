# ThermoStrife — data

Two layers, conventional:

| Layer | Tracked? | Purpose |
|-------|----------|---------|
| `raw/` | yes | Curated source-of-truth event panels + geocoded coordinates. Never overwrite — derived artefacts go elsewhere. |
| `cache/` | no (gitkeep only) | Per-(station, year-month) parquet caches written by the source adapters so re-runs don't re-hit the upstream APIs. Reproducible from `raw/` plus an internet connection. |

## `raw/uprisings_temperature.csv`

112 violent uprisings, revolutions, massacres, and prison revolts
1750–2024. RFC-4180 / UTF-8 / `NA` for missing.

Column schema (selected; see the file itself for the full set):

| Column | Meaning |
|--------|---------|
| `event_id` | Stable slug, e.g. `1819_peterloo` |
| `start_date` / `end_date` | ISO-8601; single-day events have `start == end` |
| `city` / `country` | Best modern administrative name |
| `est_deaths_low` / `est_deaths_high` | Scholarly casualty range |
| `day_temp_C` | Day-of-event Tmax used as a *qualitative sanity check* on the cascade output. The analysis does NOT read this column — it computes anomaly from the same-source `(event, baseline)` pair returned by the cascade. `NA` rows are fine. |
| `decade_mean_temp_C` | Legacy column kept for cross-reference only; superseded by the per-tier same-source baseline built by the cascade. |
| `anomaly_C` | Legacy column kept for cross-reference only. |
| `qualitative_weather` | Contemporary description ("hot afternoon", "pouring rain", …) |
| `temp_data_source` | Citation / station ID for `day_temp_C` |
| `event_data_source` | Citation(s) for the event itself |
| `era` | One of `era1_1750_1850` … `era5_2000_2026` |
| `notes` | Free-text caveats |

## `raw/peaceful_gatherings.csv` + `raw/peaceful_geo.csv`

41 peaceful mass gatherings (carnivals, papal visits, royal weddings,
large religious pilgrimages) used as the Field-1992 outdoor-opportunity
parallel-control panel. Schema mirrors the violent panel.

## `raw/event_geo.csv` + `raw/peaceful_geo.csv`

Resolved (`event_id`, `lat`, `lon`) pairs. Built by
`scripts/build_geo_map.py` (OpenStreetMap Nominatim, rate-limited and
cached) with hand-curated rows preserved verbatim.

## `raw/observatories/hadcet/`

Daily HadCET totals files (max / mean / min) mirrored from the Met
Office. Needed by the Tier-2 HadCET adapter.

## `cache/`

Three sub-directories, one per network-touching tier:

- `cache/meteostat/<station-hash>/<station>_<YYYY-MM>.parquet`
- `cache/era5/<+lat_+lon>/<YYYY-MM>.parquet`
- `cache/twentycr/<+lat_lon>/<YYYY>.parquet`

Empty (zero-row) parquets are written as negative caches so the
cascade does not re-hit the upstream API for known-missing
(station, year, month) combinations. Safe to delete; the cascade will
rebuild on next run.

## Provenance

The violent panel was compiled from Wikipedia, Britannica, USHMM,
South African History Online, BlackPast, Encyclopedia of Arkansas, the
Detroit Historical Society, the National Security Archive, and the
historiographic monographs cited in each row's `event_data_source`
column. The peaceful panel was compiled from event-specific encyclopedia
articles and news archives.
