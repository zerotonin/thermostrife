# Contributing

## Development setup

```bash
git clone https://github.com/zerotonin/thermostrife.git
cd thermostrife
pip install -e ".[climate,dev]"
```

For the ERA5 / 20CRv3 fallback tiers you will also need a Copernicus
CDS API key — see {doc}`../getting_started`.

## Running the test suite

```bash
pytest
```

CI-matched run with coverage:

```bash
pytest --cov=thermostrife --cov-report=term
```

## Linting

```bash
ruff check .
ruff check . --fix    # apply safe fixes
```

## Building the docs locally

```bash
pip install -r docs/requirements.txt
sphinx-build -b html docs/ docs/_build/html
xdg-open docs/_build/html/index.html
```

## Commit conventions

Atomic commits, one logical change per commit.

| Prefix | Use for |
|--------|---------|
| `feat(<module>):` | New feature in `<module>` |
| `fix(<module>):` | Bug fix in `<module>` |
| `refactor(<module>):` | Restructure without behaviour change |
| `docs(<topic>):` | Documentation only |
| `test(<module>):` | Test additions or fixes |
| `data(<event_id>):` | Curated CSV updates (event additions, casualty revisions, weather citations) |
| `ci:` | Continuous integration changes |
| `chore:` | Tooling, dependencies, housekeeping |

`data(...)` is ThermoStrife-specific — the curated CSV is part of the
scientific contribution, and edits deserve clear commit provenance.

## Pull request workflow

1. Fork and create a feature branch from `main`.
2. Run `pytest` and `ruff check .` locally.
3. Open a PR against `main`. Both `tests` and `docs` workflows must pass.
4. CSV edits get the same review weight as code edits — please include a
   citation in the row's `event_data_source` or `temp_data_source`.
