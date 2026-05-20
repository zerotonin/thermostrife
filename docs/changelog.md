# Changelog

All notable changes to ThermoStrife are documented here. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
