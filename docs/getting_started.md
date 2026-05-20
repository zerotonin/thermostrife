# Getting started

## Installation

```bash
git clone https://github.com/zerotonin/thermostrife.git
cd thermostrife
pip install -e ".[climate,dev]"
```

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
url: https://cds.climate.copernicus.eu/api/v2
key: <UID>:<API-KEY>
```

The Tier 1 / 2 sources (meteostat + observatory archives) work without
this and cover ~80 % of the dataset on their own.

## Verifying the installation

```bash
python -c "import thermostrife; print(thermostrife.__version__)"
thermostrife-backfill --help
thermostrife-analyse --help
```

## Your first run

```bash
thermostrife-backfill data/raw/uprisings_temperature.csv \
    --output data/interim/uprisings_backfilled.csv

thermostrife-analyse data/interim/uprisings_backfilled.csv \
    --output reports/
```

The first call fills `day_temp_C` and the period-correct decadal mean
where they were `NA`. The second runs the pre-registered hypothesis tests
and writes figures + a `results.json` summary to `reports/`.
