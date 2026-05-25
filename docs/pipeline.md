# Pipeline guide

End-to-end walk-through of the five stages. All scripts run from the
repo root.

## Stage 1 — Curated event panels

Two parallel panels live under `data/raw/`:

- **`uprisings_temperature.csv`** — 112 violent uprisings,
  revolutions, massacres, and prison revolts (1750–2024).
  Hand-curated from Wikipedia, Britannica, USHMM, BlackPast, the
  Encyclopedia of Arkansas, the National Security Archive, and the
  historiographic monographs cited row-by-row in `event_data_source`.
- **`peaceful_gatherings.csv`** — 41 peaceful mass gatherings
  (carnivals, papal visits, royal weddings, large religious
  pilgrimages) used as the Field-1992 outdoor-opportunity
  falsification panel.

Coordinates live in `event_geo.csv` and `peaceful_geo.csv`. Editing
rule: changes to the event lists go in `raw/`; resolved temperatures
and analysis frames are derived artefacts and live elsewhere.

See `data/README.md` for the column schema.

## Stage 2 — Tiered weather-archive cascade

The cascade is implemented in `thermostrife.lookup.resolve_event_anomaly`
and dispatched through `thermostrife.sources.*`:

| Tier | Source | Coverage | Adapter |
|------|--------|----------|---------|
| 1 | GHCN-Daily / ECA&D / DWD via `meteostat` 2.x | ~1880+ where stations exist | `sources.meteostat_src` |
| 2 | HadCET (Hadley Centre Central England Temperature) | 1772+ (mean), 1878+ (max), British Isles only | `sources.hadcet_src` |
| 3 | ECMWF ERA5 reanalysis (0.25° grid) via `cdsapi` | 1981+ global | `sources.era5_src` |
| 4 | NOAA 20CRv3 reanalysis (1° grid, ensemble mean) via PSL THREDDS | 1806–1980 global | `sources.twentycr_src` |

The resolver tries each tier in order and accepts the **first** tier
that returns *both* an event-day Tmax and a same-source baseline
window with ≥ 20 days of data. The baseline is built from the *same*
station / grid cell that resolved the event day, so the anomaly
`event − mean(baseline)` is internally consistent. Each resolved row
carries a `temp_provenance` flag (`tier1_ghcn`, `tier2_hadcet_max`,
`tier2_hadcet_mean`, `tier3_era5`, `tier4_20crv3`) so the analysis can
audit which events came from which tier.

## Stage 3 — Anomaly construction

Built inside the cascade rather than as a separate stage. For each
resolved event:

```
anomaly_C = event_day_Tmax − mean(baseline_window_Tmax)
```

where `baseline_window` is the ±5-year same-station, same-calendar-month
daily Tmax record from the resolving tier, excluding the event window
± 7 days. This anchors `anomaly_C` against the local climate of the
event year rather than today's climatology and removes the warming-trend
bias that would otherwise distort pre-1900 anomalies.

## Stage 4 — Case-crossover inference

```bash
python scripts/run_inference.py --panel violent
python scripts/run_inference.py --panel peaceful
```

The primary test (H2) is a **time-stratified case-crossover** fitted
with `statsmodels.discrete.conditional_models.ConditionalLogit`. For
each event `i`, the control set is every day at the same station,
same calendar month, in years `event_year ± 5`, excluding the event
window ± 7 days. The stratification absorbs all time-invariant
station, regional, and era confounds by construction. A
daylight-hours covariate is included as a direct rebuttal to the
Field (1992) outdoor-opportunity critique.

Robustness battery (same script):

- **H1 descriptive** — Wilcoxon signed-rank, sign test, bootstrap
  mean CI on the per-event anomalies.
- **Stratified permutation** within each event's matched set
  (`B = 10 000`) as a non-parametric backup for H2.
- **H3 within-event temporal contrast** — paired test against the
  "hot week happened to contain an event" alternative.
- **Burke-2015 σ rescaling** — per-event z-score so the effect
  translates into the +2.4 % per 1 σ Burke meta-analytic currency.
- **Benjamini–Hochberg FDR** across the auxiliary battery (q = 0.05),
  with Bonferroni columns alongside.

## Stage 5 — Reporting

```bash
python scripts/compare_panels.py
python scripts/run_stratifications.py
```

Outputs in `reports/`:

- `inference_results.{md,json}` — violent panel.
- `inference_results_peaceful.{md,json}` — peaceful control.
- `peaceful_vs_violent.md` — side-by-side comparison.
- `stratification.md` — era / hemisphere / duration / event-type
  sensitivity analysis with per-stratum forest plot.
- `cascade_validation.md` — diagnostic audit of the tier cascade.
- `figs/` — raincloud, null density, anomaly-by-year, warming-stripes
  timeline, superposed-epoch composite, forest plot. Every figure is
  a triple SVG + PNG + CSV.
