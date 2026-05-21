# Changelog

All notable changes to ThermoStrife are documented here. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **Tier 1 weather backfill (meteostat).** New
  `thermostrife/sources/meteostat_src.py` with parquet caching per
  `(station, year-month)`; nearest-station search; baseline-window
  fetcher for the period-correct ±5-year same-month reference. Wired
  into `lookup.resolve` as the first tier of the cascade.
- `data/raw/event_geo.csv` — hand-curated lat/lon (plus station hints
  in the notes column) for the 13 verified rows; expansion to all 112
  is Sprint 1.5.
- `scripts/validate_tier1.py` and `reports/tier1_validation.md` —
  per-row manual-vs-Tier-1 comparison with outlier triage notes.
- `tests/test_validation.py` — pytest gate (marked `network`) that
  asserts ≥8 of 13 verified rows resolve, MAE < 3 °C, median |Δ| <
  1.5 °C, and ≥4 rows within 1.5 °C of the manual value.
- `meteostat`, `geopy`, `pyarrow` added to `[climate]` extras and
  `environment.yml`.

### Known caveats from the first validation pass

- 3 of 13 rows do not resolve at Tier 1 (Paris 1871, Chicago 1919,
  LAX 1965). Meteostat coverage thins out pre-1920; these rows are
  the explicit motivation for Tiers 2–4.
- 4 of 10 resolved rows show |Δ| > 2 °C, notably Dublin 1916
  (+4.2 °C) and Kyiv 2014 (+9.0 °C). These need station-hint
  curation or a manual re-check of the original primary source.

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
