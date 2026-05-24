# Continuous integration

Three GitHub Actions workflows under `.github/workflows/`.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `tests.yml` | push / PR to `main` | pytest on 3 OS × 3 Python versions + `ruff check` |
| `docs.yml` | push / PR to `main` | Build Sphinx docs; deploy to GitHub Pages on push to `main` |
| `release.yml` | push of `v*.*.*` tag | Tests gate, build sdist + wheel, attach to GitHub Release |

## `tests.yml`

- **OS:** `ubuntu-latest`, `macos-latest`, `windows-latest`
- **Python:** `3.11`, `3.12`, `3.13`
- Installs the package with `dev` and `climate` extras (the climate stack
  is needed for any test that touches the source adapters).
- Coverage XML uploaded from Ubuntu / Python 3.12.

The lint job (`ruff check .`) runs as `continue-on-error: true` while the
package is in early scaffold state. Flip the flag once the
implementation modules land.

## `docs.yml`

Builds the Sphinx site on every PR (catches doc regressions) and deploys
to GitHub Pages on every push to `main`.

### One-time repo settings

1. **Settings → Pages → Source:** "GitHub Actions"
2. **Settings → Actions → General → Workflow permissions:** "Read and
   write permissions"

## `release.yml`

Tagging `vX.Y.Z` triggers: tests → `python -m build` → GitHub Release with
sdist + wheel attached. The Zenodo webhook then mints a DOI from
`CITATION.cff`.

## Branch protection

`main` should require:

- `tests` matrix jobs to pass.
- `docs` build job to pass.
- One approving review.
