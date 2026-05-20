# Pipeline guide

End-to-end walk-through of the five stages.

## Stage 1 — Curated event panel

`data/raw/uprisings_temperature.csv` holds the 112 events. The file is
hand-curated from Wikipedia, Britannica, USHMM, BlackPast, the Encyclopedia
of Arkansas, the National Security Archive, and the historiographic
monographs cited row-by-row in `event_data_source`.

Editing rule: changes to the event list, casualties, or qualitative weather
description go in `raw/`. Temperatures backfilled by the pipeline live in
`interim/` and are reproducible from `raw/` plus the source adapters.

See `data/README.md` for the column schema.

## Stage 2 — Tiered temperature backfill

```bash
thermostrife-backfill data/raw/uprisings_temperature.csv \
    --output data/interim/uprisings_backfilled.csv
```

For each row with `NA` in `day_temp_C`, the resolver tries:

| Tier | Source | Coverage |
|------|--------|----------|
| 1 | GHCN-Daily / ECA&D / DWD via `meteostat` | ~1880+ |
| 2 | Long-record observatories (HadCET, Paris, Berlin, Brera, Vienna) | 1659+ for a handful of European cities |
| 3 | ERA5 grid cell via `cdsapi` | 1940+ global |
| 4 | 20CRv3 reanalysis grid cell | 1836+ global, ~1 ° |
| — | `temp_provenance = "unverifiable"` | pre-1836 tropics |

Each row gains:

- `temp_provenance` — which tier resolved the value
- `decade_n` — sample size of the ±5-year same-station, same-month window
- `decade_se` — standard error of the decadal mean

## Stage 3 — Period-correct decadal baseline

The same backfill pass replaces `decade_mean_temp_C` (currently a mix of
period-correct values and modern climatology) with a ±5-year same-station,
same-calendar-month mean of daily Tmax. This anchors `anomaly_C` against
the local climate of the event year rather than today's climatology, and
removes the warming-trend bias that currently distorts pre-1900 anomalies.

## Stage 4 — Case-crossover inference

```bash
thermostrife-analyse data/interim/uprisings_backfilled.csv \
    --output reports/
```

The primary test (H2) is a time-stratified case-crossover with conditional
logistic regression. For each event `i`, the control set is every day at
the same station, same calendar month, in years `event_year ± 5`, excluding
the event window ± 7 days.

The stratification absorbs all time-invariant station, regional, and era
confounds by construction. A daylight-hours covariate is included as a
direct rebuttal to the Field (1992) outdoor-opportunity critique.

Robustness:

- **Stratified permutation** within each event's matched set (`B = 10 000`).
- **Hsiang-style 1 σ rescaling** so the effect can be compared directly to
  Burke et al. 2015 (+2.4 % violence per 1 σ).

## Stage 5 — Reporting

Outputs in `reports/`:

- `results.json` — every numerical result, ready for cross-referencing.
- `anomaly_raincloud.{svg,png,csv}` — event vs control anomaly distribution.
- `null_density.{svg,png,csv}` — permutation null with observed marker.
- Per-stratum sub-figures (indoor/outdoor, hemisphere, era, civilian/coup).
