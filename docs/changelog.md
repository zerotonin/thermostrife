# Changelog

All notable changes to ThermoStrife are documented here. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
