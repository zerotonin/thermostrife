# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — cli                                              ║
# ║  « thermostrife-analyse entry point »                            ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  End-to-end orchestrator: load backfilled CSV, run all           ║
# ║  pre-registered tests, write reports/results.json plus           ║
# ║  figures and per-stratum tables.                                 ║
# ╚══════════════════════════════════════════════════════════════════╝
"""End-to-end analysis CLI."""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run the full pre-registered analysis pipeline."""
    parser = argparse.ArgumentParser(
        prog="thermostrife-analyse",
        description="Run the case-crossover analysis on a backfilled CSV.",
    )
    parser.add_argument("input_csv", type=Path, help="Backfilled uprisings CSV.")
    parser.add_argument(
        "--output", "-o", type=Path, default=Path("reports"),
        help="Output directory for figures and results.json.",
    )
    args = parser.parse_args(argv)

    raise NotImplementedError(
        "cli.main() awaits the inference engine in thermostrife.inference."
    )


if __name__ == "__main__":
    raise SystemExit(main())
