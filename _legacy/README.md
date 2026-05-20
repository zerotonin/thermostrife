# Legacy code

Material preserved per the style guide (1.3): kept around until all useful
logic has been extracted into the new package.

## `analysis.py`

The original single-file scaffold from the Obsidian project folder.
Implements:

- H1 Wilcoxon signed-rank and binomial sign test (extracted into
  `thermostrife.inference`).
- Bootstrap CI on the mean anomaly (extracted into
  `thermostrife.inference`).
- A **placeholder** synthetic-control "matched-control test" that draws
  `N(0, σ_event)` controls — superseded by the case-crossover engine in
  `thermostrife.inference.case_crossover_conditional_logit`.
- Per-era descriptives and basic histogram / box-by-era / scatter plots,
  to be replaced with Wong-palette raincloud variants in
  `thermostrife.viz`.

Delete this directory once the new package matches its functionality on
the same dataset.
