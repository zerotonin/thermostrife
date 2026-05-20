# Release process

## 1. Pre-release checks

```bash
pytest
ruff check .
sphinx-build -b html docs/ docs/_build/html
```

All three must pass cleanly before tagging.

## 2. Update version metadata

Three files must move in lockstep:

| File | Field |
|------|-------|
| `pyproject.toml` | `[project] version = "X.Y.Z"` |
| `thermostrife/__init__.py` | `__version__ = "X.Y.Z"` |
| `CITATION.cff` | `version: "X.Y.Z"` (quoted) and `date-released: "YYYY-MM-DD"` |

Validate `CITATION.cff` with [`cffconvert`](https://github.com/citation-file-format/cffconvert):

```bash
cffconvert --validate
```

Watch for the canonical CFF traps that break Zenodo minting:

- Unquoted version (`version: 1.0.0` instead of `version: "1.0.0"`).
- Em-dashes in the abstract — replace with `--`.
- Wrong ORCID format — must be a full URL.

## 3. Update the changelog

Add a section under {doc}`../changelog`.

## 4. Tag and push

```bash
git tag -a vX.Y.Z -m "vX.Y.Z: <one-line summary>"
git push origin vX.Y.Z
```

`release.yml` runs automatically.

## 5. Post-release

- Verify the Zenodo DOI resolves (~10 min after webhook).
- Update the README DOI badge if it's the first time.
- If this release changes the curated CSV, archive a frozen copy under
  `data/raw/uprisings_temperature_vX.Y.Z.csv` for citation by downstream
  re-analyses.

## Rolling back a broken release

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```

Delete the GitHub Release and the draft Zenodo deposit. Fix the issue,
re-tag, re-push.
