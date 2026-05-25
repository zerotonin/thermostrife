# ThermoStrife

[![tests](https://github.com/zerotonin/thermostrife/actions/workflows/tests.yml/badge.svg)](https://github.com/zerotonin/thermostrife/actions/workflows/tests.yml)
[![docs](https://github.com/zerotonin/thermostrife/actions/workflows/docs.yml/badge.svg)](https://zerotonin.github.io/thermostrife/)
[![release](https://github.com/zerotonin/thermostrife/actions/workflows/release.yml/badge.svg)](https://github.com/zerotonin/thermostrife/releases)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20371612.svg)](https://doi.org/10.5281/zenodo.20371612)
[![Companion: ThermoKourt](https://img.shields.io/badge/companion-ThermoKourt-009E73.svg)](https://github.com/zerotonin/thermokourt)

**Do violent uprisings cluster on unusually hot days?** Empirical
companion to the [ThermoKourt](https://github.com/zerotonin/thermokourt)
*Drosophila* heat-aggression pipeline.

ThermoStrife curates a 112-event panel of violent uprisings,
revolutions, massacres, and prison revolts from 1750 to 2024, resolves
each event's day-of-event maximum temperature through a four-tier
weather-archive cascade (meteostat → HadCET → ERA5 → 20CRv3), pairs
it with a station-and-month-matched ±5-year decadal baseline drawn
**from the same underlying series**, and tests whether the resulting
anomalies are over-represented above zero against a **case-crossover
null** of matched non-event days at the same station and calendar
month. A 41-event peaceful-crowd parallel-control panel rules out
the Field 1992 outdoor-opportunity confound.

The design extends Lee et al. (2023, *Int. J. Environ. Res. Public
Health*) for the human side, and is the empirical anchor for the
cross-species heat-aggression argument developed in ThermoKourt.

## Headline result (v0.1.0)

| Quantity | Value |
|---|---|
| Resolved violent events | 104 of 112 |
| Resolved peaceful-control events | 37 of 41 |
| **H2 case-crossover OR per +1 °C** | **1.089 (95 % CI 1.029–1.152)** |
| H2 one-sided p (BH-FDR auxiliary) | 0.0016 |
| Stratified permutation backup | observed +0.59 °C, p = 0.0019 |
| σ-rescaled effect (Burke 2015 currency) | +0.20 σ (95 % CI +0.07 to +0.34) |
| Peaceful-control OR (Field-1992 falsifier) | 0.961, p = 0.83 |
| Civilian uprisings stratum (n=78) | OR 1.096, p = 0.0018 |
| Military coups stratum (n=5, indoor-mechanism sanity check) | OR 1.012, p = 0.46 |

All 13 pre-registered stratifications point in the H1 direction; the
military-coups null is the predicted negative control (planned-indoor
events should be weather-insensitive). Full numbers in
`reports/inference_results.md`, `reports/peaceful_vs_violent.md`, and
`reports/stratification.md`.

## Why a separate repo?

ThermoStrife shares the *scientific question* with ThermoKourt (does
heat modulate aggression?) but nothing else: no fly-tracking
dependencies, a different audience (criminology / climate-and-conflict),
and a different publication trajectory. The two repos cross-cite each
other; the historical-uprisings figure cited from the ThermoKourt
manuscript is generated here and imported as a static asset.

## Pipeline overview

```
 ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
 │  1 · CURATE     │    │  2 · CASCADE    │    │  3 · ANOMALY     │
 │  112 violent +  │───▶│  Tier 1 GHCN    │───▶│  event_day −     │
 │  41 peaceful    │    │  Tier 2 HadCET  │    │  same-source     │
 │  events         │    │  Tier 3 ERA5    │    │  ±5 yr same-     │
 │                 │    │  Tier 4 20CRv3  │    │  month baseline  │
 └─────────────────┘    └─────────────────┘    └──────────────────┘
                                                        │
 ┌─────────────────┐    ┌─────────────────┐             ▼
 │  5 · REPORT     │◀───│  4 · INFERENCE  │◀── (case, controls) per
 │  SVG+PNG+CSV    │    │  H1 descriptive │    event stratum
 │  + markdown +   │    │  H2 cond. logit │
 │  forest plots   │    │  H3 temporal    │
 │                 │    │  σ-rescaled     │
 │                 │    │  BH-FDR battery │
 └─────────────────┘    └─────────────────┘
```

| Stage | Module / script | Purpose |
|-------|----------------|---------|
| **1** | `data/raw/uprisings_temperature.csv`, `data/raw/peaceful_gatherings.csv`, `data/raw/event_geo.csv` | Curated 112 violent + 41 peaceful events with geocoded coordinates. |
| **2** | `thermostrife.lookup.resolve_event_anomaly` + `thermostrife.sources.*` | Tiered cascade: meteostat 2.x → HadCET → ERA5 → 20CRv3, returning a single-source (event-day Tmax, baseline window) pair. |
| **3** | (inside the cascade) | The baseline is built from the *same* station / grid cell that resolved the event day; anomaly = `event − mean(baseline)`. |
| **4** | `thermostrife.inference` | H1 Wilcoxon / sign / bootstrap CI; **H2 case-crossover conditional logit (headline)**; stratified permutation backup; H3 within-event temporal contrast (hot day vs hot week); Burke-2015 σ-rescaling; Benjamini–Hochberg FDR across the auxiliary battery. |
| **5** | `thermostrife.viz` + `scripts/*` | Raincloud, null-density, anomaly-by-year, forest plot, superposed-epoch composite, warming-stripes timeline. Every figure ships as SVG + PNG + CSV. |

## Installation

```bash
git clone https://github.com/zerotonin/thermostrife.git
cd thermostrife
pip install -e ".[climate,dev]"
```

For the ERA5 fallback tier you additionally need a
[Copernicus CDS API key](https://cds.climate.copernicus.eu/api-how-to)
in `~/.cdsapirc` (gitignored). The 20CRv3 tier (1806–1980) needs no
key — it streams from NOAA PSL THREDDS.

The CI matrix is `ubuntu-latest × {3.11, 3.12, 3.13}`; the package
itself is Python ≥ 3.11 because meteostat 2.x dropped support for 3.10.

## Quick start

The pipeline runs as a sequence of small scripts that read from
`data/raw/` and write to `reports/`. Run them from the repo root.

```bash
# 1. Sanity-check the cascade against the curated CSV
python scripts/validate_cascade.py

# 2. Headline inference on the violent panel
python scripts/run_inference.py --panel violent

# 3. Parallel-control inference on the peaceful panel
python scripts/run_inference.py --panel peaceful

# 4. Side-by-side comparison + two-panel raincloud
python scripts/compare_panels.py

# 5. Sensitivity stratifications (era / hemisphere / duration / event type)
python scripts/run_stratifications.py
```

Each script writes a Markdown report (under `reports/`) and the figure
triple (SVG + PNG + CSV under `reports/figs/`). The cascade caches per
(station, year-month) under `data/cache/`, so re-runs are fast.

## Pre-registered hypotheses

The full pre-registered protocol is in [`docs/methods.md`]; the short
version:

| ID | Hypothesis | Test (in `thermostrife.inference`) | Role |
|----|------------|------------------------------------|------|
| **H1** | Per-event anomalies have a positive central tendency. | `wilcoxon_signed_rank`, `sign_test`, `bootstrap_mean_ci` (descriptive). | Auxiliary. |
| **H2** | Conditional on station + calendar month, uprising days carry higher Tmax than matched non-event days. | `case_crossover_conditional_logit` (primary) + `stratified_permutation` (non-parametric backup). | **Headline confirmatory.** |
| **H3** | The event day and its immediate neighbour sit above local baseline by more than days a week away (rules out the "hot week happened to contain an event" alternative). | `h3_within_event_contrast`. | Auxiliary. |
| **σ** | Per-event z-score against baseline σ (Burke et al. 2015 currency for cross-study comparison). | `hsiang_sigma_rescaled`. | Effect-size translation. |

H2 is the single confirmatory test (uncorrected α = 0.05); H1 / H3 form
the auxiliary battery with Benjamini–Hochberg FDR (q = 0.05) and a
Bonferroni column alongside as a conservative reference. The
peaceful-control panel is the Field-1992 outdoor-opportunity
falsification — if the H2 signal were a generic crowd-outdoor
artefact, peaceful mass gatherings should show it too. They don't.

## Reports & figures shipped with v0.1.0

- `reports/inference_results.md` / `.json` — violent panel.
- `reports/inference_results_peaceful.md` / `.json` — peaceful control.
- `reports/peaceful_vs_violent.md` — side-by-side comparison.
- `reports/stratification.md` — era / hemisphere / duration / event-type sensitivity.
- `reports/cascade_validation.md` — provenance audit of the tier cascade.
- `reports/figs/` — raincloud, null density, anomaly-by-year,
  warming-stripes timeline, superposed-epoch composite, forest plot;
  each triple SVG + PNG + CSV.

## Project conventions

- Wong (2011) colourblind-safe palette throughout (`thermostrife.constants.WONG`).
- Every figure is SVG-first with `svg.fonttype = "none"` so labels
  stay editable in Inkscape; PNG companion at 200 DPI; CSV companion
  with the underlying numbers.
- All paths are `pathlib.Path`; no `os.path.join`.
- Tests live under `tests/`; ruff + pytest run in CI on every push.

## Authors

Bart R. H. Geurten — Department of Zoology, University of Otago,
Dunedin, New Zealand. ORCID
[0000-0002-1816-3241](https://orcid.org/0000-0002-1816-3241).

## License

MIT — see `LICENSE`.

## Citation

If you use ThermoStrife in published work, please cite the Zenodo
release whose DOI matches the version you used:

> Geurten, B. R. H. (2026). *ThermoStrife: historical-uprisings
> temperature companion to ThermoKourt* (Version 0.1.1) [Software].
> Zenodo. https://doi.org/10.5281/zenodo.20371612

Full citation metadata is in `CITATION.cff` and on the GitHub repo's
"Cite this repository" button.
