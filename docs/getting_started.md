# Getting started

## Installation

```bash
git clone https://github.com/zerotonin/thermostrife.git
cd thermostrife
pip install -e ".[climate,dev]"
```

Python ≥ 3.11 is required (meteostat 2.x dropped Python 3.10).

### Conda environment (recommended)

```bash
conda env create -f environment.yml
conda activate thermostrife
pip install -e ".[dev]"
```

### Copernicus CDS API key (needed for the ERA5 fallback tier)

[Register a free CDS account](https://cds.climate.copernicus.eu/api-how-to)
and drop a `.cdsapirc` file in your home directory containing:

```ini
url: https://cds.climate.copernicus.eu/api
key: <YOUR-API-KEY>
```

The Tier 1 / 2 sources (meteostat + HadCET) and the Tier 4 NOAA
20CRv3 OPeNDAP feed work without this key and together cover the
overwhelming majority of the dataset; the CDS key only matters when
the cascade falls through to ERA5 (1981+ events outside Britain and
outside meteostat-station radius).

## Verifying the installation

```bash
python -c "import thermostrife; print(thermostrife.__version__)"
pytest                 # runs the full test suite
```

## Your first run

The pipeline is a sequence of small scripts in `scripts/` that you run
from the repo root.

```bash
# Sanity-check the cascade against the curated CSV
python scripts/validate_cascade.py

# Inference on the headline violent panel
python scripts/run_inference.py --panel violent

# Inference on the peaceful-control panel
python scripts/run_inference.py --panel peaceful

# Side-by-side comparison + two-panel raincloud
python scripts/compare_panels.py

# Sensitivity stratifications (era / hemisphere / duration / event type)
python scripts/run_stratifications.py
```

Each script writes a Markdown report under `reports/` and a figure
triple (SVG + PNG + CSV) under `reports/figs/`. The cascade caches
per-(station, year-month) results under `data/cache/`, so re-runs after
the first network-touching pass are fast.
