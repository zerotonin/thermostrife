# ThermoStrife

[![tests](https://github.com/zerotonin/thermostrife/actions/workflows/tests.yml/badge.svg)](https://github.com/zerotonin/thermostrife/actions/workflows/tests.yml)
[![docs](https://github.com/zerotonin/thermostrife/actions/workflows/docs.yml/badge.svg)](https://zerotonin.github.io/thermostrife/)
[![release](https://github.com/zerotonin/thermostrife/actions/workflows/release.yml/badge.svg)](https://github.com/zerotonin/thermostrife/releases)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.PENDING.svg)](https://zenodo.org/)
[![Companion: ThermoKourt](https://img.shields.io/badge/companion-ThermoKourt-009E73.svg)](https://github.com/zerotonin/thermokourt)

**Do violent uprisings cluster on unusually hot days?** Empirical companion
to the [ThermoKourt](https://github.com/zerotonin/thermokourt) *Drosophila*
heat-aggression pipeline.

ThermoStrife curates a 112-event panel of violent uprisings, revolutions,
massacres, and prison revolts from 1750 to 2026, pairs each with a verified
day-of-event maximum temperature and a station-and-month-matched ±5-year
decadal baseline, and tests whether the resulting temperature anomalies are
over-represented above zero against a **case-crossover null** of matched
non-event days drawn from the same station and calendar month.

The design matches Lee et al. (2023, *Int. J. Environ. Res. Public Health*)
for the human side, and is the empirical anchor for the cross-species heat-
aggression argument developed in ThermoKourt.

---

## Why a separate repo?

ThermoStrife shares the *scientific question* with ThermoKourt (does heat
modulate aggression?) but nothing else: it has no fly-tracking dependencies,
a different audience (criminology / climate-and-conflict), and a different
publication trajectory. The two repos cross-cite each other; the historical-
uprisings figure used in the ThermoKourt manuscript is generated here and
imported as a static asset.

## Pipeline overview

```
 ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
 │  1 · CURATE     │    │  2 · BACKFILL   │    │  3 · BASELINE    │
 │  112 events     │───▶│  Tier 1: GHCN   │───▶│  ±5-year same-   │
 │  CSV table      │    │  Tier 2: HadCET │    │  station / month │
 │                 │    │  Tier 3: ERA5   │    │  decadal mean    │
 │                 │    │  Tier 4: 20CRv3 │    │  + SE            │
 └─────────────────┘    └─────────────────┘    └──────────────────┘
                                                        │
 ┌─────────────────┐    ┌─────────────────┐             ▼
 │  5 · REPORT     │◀───│  4 · INFERENCE  │◀── anomaly_C per event
 │  figs + tables  │    │  case-crossover │    + provenance + SE
 │  + permutation  │    │  conditional    │
 │  null densities │    │  logit + perm   │
 └─────────────────┘    └─────────────────┘
```

| Stage | Module | Purpose | Key dependency |
|-------|--------|---------|----------------|
| **1** | `data/raw/` | Curated 112-event panel | none |
| **2** | `sources/` | Tiered weather-archive resolvers | meteostat, cdsapi, requests |
| **3** | `baseline` | Period-correct ±5-yr decadal mean | numpy, pandas |
| **4** | `inference` | Case-crossover + conditional logit + stratified permutation | statsmodels, scipy |
| **5** | `viz` | Wong-palette figures + CSV companions | matplotlib |

## Installation

```bash
git clone https://github.com/zerotonin/thermostrife.git
cd thermostrife
pip install -e ".[climate,dev]"
```

For the ERA5 / 20CRv3 fallback tiers you will additionally need a
[Copernicus CDS API key](https://cds.climate.copernicus.eu/api-how-to)
in `~/.cdsapirc`.

## Quick start

### 1 — Backfill temperatures

```bash
thermostrife-backfill data/raw/uprisings_temperature.csv \
    --output data/interim/uprisings_backfilled.csv
```

Each row records `temp_provenance` (which tier resolved the value),
`decade_n` (sample size of the baseline window), and `decade_se`.

### 2 — Run the case-crossover analysis

```bash
thermostrife-analyse data/interim/uprisings_backfilled.csv \
    --output reports/
```

Writes `reports/results.json`, raincloud plots of the anomaly distribution,
and per-stratum tables (indoor/outdoor, hemisphere, era, coup vs civilian).

## Hypotheses (pre-registered)

| ID | Hypothesis | Test |
|----|------------|------|
| **H1** | `mean(anomaly \| event) > 0` | Wilcoxon signed-rank + sign test on event anomalies |
| **H2** | `mean(anomaly \| event) > mean(anomaly \| matched control)` | **Case-crossover conditional logit** — primary |
| **H3** | `anomaly_t > anomaly_{t±7}` | Within-event paired test (excludes "hot week" alternative) |

H2 is the headline. H1 alone cannot distinguish heat from outdoor-opportunity;
H3 is the secondary within-event check.

## Authors

Bart R.H. Geurten — Department of Zoology, University of Otago, Dunedin,
New Zealand.

## License

MIT
