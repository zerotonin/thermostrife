# Changelog

All notable changes to ThermoStrife are documented here. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added — Sprint 6 (publication figures for Jess's deck)

- **`thermostrife/viz.py`** — three figure functions, each triple-output
  (SVG with editable text + PNG @ 200 dpi + CSV data companion) so
  they can be opened in Inkscape for slide-deck tweaks:

  - `plot_anomaly_raincloud` — half-violin + boxplot + jittered strip
    of per-event anomalies, points coloured by source tier, headline
    H2 result annotated in the lower right.
  - `plot_null_density` — KDE of the permutation null with the
    observed statistic marked; visual proof of H2.
  - `plot_anomaly_by_year` — anomaly vs event year with an 11-event
    rolling mean overlay; era-stratification visualiser.

- **`TIER_COLOURS` / `TIER_LABELS`** in `constants.py` so every figure
  uses the same Wong-palette mapping per cascade tier (green → blue
  → orange → reddish-purple as you go further back in time).

- **`scripts/run_inference.py`** now generates the three figures
  alongside `reports/inference_results.{md,json}` and embeds them in
  the markdown report.

- **`tests/test_viz.py`** — 5 smoke tests: each function writes the
  expected triple, raises on empty input where appropriate, and the
  small-null-draws guard fires.

- **`reports/figs/`** is now tracked in git: the figures are
  publishable artefacts, not ephemeral build output.

### Added — Sprint 5 (case-crossover inference engine)

- **Case-crossover conditional logit**
  (`thermostrife.inference.case_crossover_conditional_logit`)
  implements the pre-registered H2 headline test via
  `statsmodels.discrete.conditional_models.ConditionalLogit`.
  Strata = event_id, case = event day, controls = baseline days.
  Reports OR per +1 °C above local same-month baseline with 95 %
  CI and one- and two-sided p-values.
- **Stratified permutation** (`stratified_permutation`) backs up
  the parametric test by shuffling case labels within each event
  stratum (B = 10 000) on the mean-event-vs-mean-control
  statistic.
- **Daylight-hours covariate** (`daylight_hours`) — closed-form
  solar geometry, no extra dependencies; goes in alongside
  `tmax_c` in the conditional logit so the model controls for
  the Field (1992) outdoor-opportunity confound.
- **Burke-2015 σ-rescaling** (`hsiang_sigma_rescaled`) expresses
  each event as a z-score against its own baseline std and
  averages; CI via bootstrap.
- **`scripts/run_inference.py`** drives the whole pipeline:
  resolve every event → build long case-crossover frame → run
  all four tests → write `reports/inference_results.{md,json}`.
- **First headline result on 104 / 112 events:**
  case-crossover **OR = 1.089 per +1 °C** above local same-month
  baseline (95 % CI 1.029 – 1.152), one-sided **p = 0.0016**,
  two-sided 0.0031. Stratified permutation converges: observed
  +1.053 °C, p = 0.0015. σ-rescaled mean z = +0.258 σ
  (CI +0.059 – +0.453); 57.7 % of events sit above their local
  baseline.
- 10 new `tests/test_inference.py` cases lock in the daylight
  closed-form, the synthetic-null / synthetic-signal behaviour
  of the conditional logit, and the σ-rescaling arithmetic.

### Added — Sprint 2b (data-coverage limitations note)

- New § 7b in `docs/methods.md` enumerates the 8 unresolved
  pre-1806 events and the four candidate historical-climatology
  references (Rousseau 2009, Yiou 2014, Cornes 2013,
  Slonosky 2002), with the argument that the missingness is not
  informative for the H1 / H2 hypotheses.

### Fixed — CI: drop Python 3.10 from the matrix

- `requires-python` bumped to `>=3.11` (meteostat 2.x is 3.11+;
  3.10 jobs were failing in CI). Workflow matrix updated to
  3.11 / 3.12 / 3.13. Ruff `target-version` follows. Documented
  in `docs/development/ci_cd.md`.

### Added — Sprint 3 (Tier-3 ERA5 reanalysis)

- **ERA5 adapter.** New `thermostrife/sources/era5_src.py` fetches
  ECMWF ERA5 single-level 2-m air temperature (0.25° global grid)
  via the Copernicus CDS API. Hourly natively; daily Tmax is
  derived per-day from the 24 hourly values. One CDS request per
  event bundles the full ±5-year same-month baseline window at the
  event's grid cell so the request fits the CDS fast queue
  (~8 000 hourly values, a few MB). Per-(cell, year-month) parquet
  cache.
- **Coverage** deliberately limited to **1981+**, even though ERA5
  itself reaches 1940. The 1940-1980 window is owned by 20CRv3
  (Sprint 4), which has substantial observational ingest in that
  era; ERA5's comparative value-add is its tighter 0.25° grid in
  the satellite-era post-1980. This also keeps CDS API traffic
  minimal (one request per still-unresolved post-1980 event).
- **Cascade Tier 3** wired into `lookup.resolve_event_anomaly`
  between Tier 2 (HadCET) and Tier 4 (20CRv3). Post-1980 events
  that miss Tier 1 / Tier 2 land here; pre-1981 events fall
  through to Tier 4.
- Requires a `~/.cdsapirc` with a Copernicus API key; the file is
  gitignored and the adapter never inlines the key into code,
  cache, or report artefacts. Users also need to accept the
  ERA5 licence once at
  <https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels>.

### Added — Sprint 4 (Tier-4 20CRv3 reanalysis)

- **20CRv3 adapter.** New `thermostrife/sources/twentycr_src.py`
  serves daily Tmax from NOAA's Twentieth Century Reanalysis V3
  (1806-1980, 1° global grid) via the NOAA PSL THREDDS OPeNDAP
  endpoint. Caches one year's daily slice per grid cell as parquet
  (`data/cache/twentycr/<cell>/<year>.parquet`) so repeated baseline
  queries on the same cell hit one network round-trip per year.
- **Cascade Tier 4** wired into `lookup.resolve_event_anomaly`. With
  Tier 3 (ERA5) still stubbed, 20CRv3 is now the fallback for any
  1806-1980 event Tier 1 and Tier 2 miss.
- All 13 hand-verified rows now resolve. The previously-missing
  three — Paris Commune 1871 (+0.09 °C), Chicago Red Summer 1919
  (+4.34 °C), Watts Riots 1965 (+2.01 °C) — go via Tier 4. Their
  smaller magnitudes vs. the manually curated anomalies reflect
  the 1° grid's regional smoothing (a single grid cell averages
  ~110 × 80 km), not disagreement on the direction of the signal.
- `test_validation.MIN_RESOLVED` raised from 10 to 13.

### Added — Sprint 2 (Tier-2 HadCET observatory)

- **HadCET adapter.** New `thermostrife/sources/hadcet_src.py`.
  Mirrors the Met Office daily totals files (Tmax 1878+, mean 1772+,
  Tmin 1878+) into `data/raw/observatories/hadcet/`; resolves
  British-Isles events (lat-lon bounding box) and falls back to the
  mean series with a `tier2_hadcet_mean` provenance flag when the
  Tmax record doesn't go far enough back.
- **Cascading resolver** `thermostrife.lookup.resolve_event_anomaly`
  with a shared `AnomalyFetch` dataclass. Walks Tier 1 → Tier 2 →
  ... until one tier returns a single-source `(event, baseline)`
  pair; the analysis only sees the consistent pair, never a mixed
  one.
- `scripts/validate_cascade.py` replaces the per-tier validate
  script and writes `reports/cascade_validation.md`.
- `tests/test_validation.py` now exercises the full cascade and
  raises `MIN_RESOLVED` from 8 to 10 (Tier 2 picks up Peterloo and
  Irish 1798).

First Sprint-2 coverage numbers: **60 / 112 resolved** (Tier 1: 58,
Tier 2 HadCET: 2). Mean anomaly +1.46 °C, median +1.41 °C; 38
positive, 22 negative.

### Added — Sprint 1 (Tier-1 weather backfill)

- **meteostat adapter.** New `thermostrife/sources/meteostat_src.py`
  with parquet caching per `(station, year-month)`, nearest-station
  search, baseline-window fetcher, and a **unified
  `resolve_for_anomaly`** that commits to one station serving both
  the event-day fetch and the ±5-year same-month baseline window so
  the anomaly is computed apples-to-apples.
- `lookup.resolve` cascades through Tier 1 (Tiers 2–4 still stubbed).
- `meteostat`, `geopy`, `pyarrow` added to `[climate]` extras and
  `environment.yml`.

### Added — Sprint 1.5 (geo-map + internal-consistency gate)

- `scripts/build_geo_map.py` — geopy Nominatim geocoder with JSON
  cache; expanded `data/raw/event_geo.csv` from 13 to **all 112**
  events. Hand-curated rows are preserved; the only manual override
  after the auto-run was Kent State (Nominatim resolved to *Kent
  County, Texas* instead of Kent, Ohio).
- `scripts/validate_tier1.py` reframed as a **diagnostic** report,
  not a gate. The `manual_C` column from the source CSV is kept for
  cross-reference but explicitly not a validation target — the
  anomaly is computed from a single meteostat station's record, so
  absolute disagreement with the hand-curated value is expected and
  unimportant.
- `tests/test_validation.py` rewritten as **internal-consistency
  tests**: ≥ 8 of the verified rows resolve, every resolved row
  carries a `station_id`, baseline windows hold ≥ 20 days, and the
  baseline SD is finite and plausible (`0 < SD < 30 °C`).

### Known caveats

- 3 of the 13 verified rows do not resolve at Tier 1 (Paris 1871,
  Chicago 1919, LAX 1965). Meteostat coverage thins out pre-1920;
  these rows are the explicit motivation for Tiers 2–4.
- Several Nominatim hits land on a metro-area centroid (e.g.
  Brixton, Broadwater Farm → "Greater London"). For weather-baseline
  purposes this is acceptable — meteostat will pick the same nearby
  station regardless of which sub-borough the event happened in —
  but worth tightening if the analysis ever uses geocoded coordinates
  for anything more granular than weather lookup.

## v0.1.0 — 2026-05-21

Initial scaffold split out of the ThermoKourt project notebook.

### Added

- Curated 112-event panel of violent uprisings 1750–2026
  (`data/raw/uprisings_temperature.csv`), copied from the Obsidian project
  folder.
- Package skeleton: `constants`, `sources/`, `lookup`, `baseline`,
  `inference`, `backfill`, `viz`, `cli`. Most module bodies are stubs
  with type hints and docstrings; the H1 tests (Wilcoxon, sign,
  bootstrap CI) are ported from `_legacy/analysis.py`.
- GitHub Actions workflows: `tests.yml`, `docs.yml`, `release.yml`.
- Sphinx + Furo documentation with grouped sidebar (User guide,
  Development, API reference, Project).
- Pre-registered methods note (`docs/methods.md`).
- Wong (2011) palette and `save_figure` triple-output helper in
  `constants.py`.

### Known limitations

- 99 of 112 rows still have `day_temp_C = NA`. The `thermostrife-backfill`
  CLI is stubbed pending the source adapters in `thermostrife/sources/`.
- `decade_mean_temp_C` is partly modern climatology — the period-correct
  baseline awaits Stage 3 implementation.
- The case-crossover engine and stratified permutation in
  `thermostrife.inference` are stubbed.
