# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — backfill                                         ║
# ║  « fill day_temp_C and decadal baseline for every row »          ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  CLI entry point.  Reads the curated uprisings CSV, calls        ║
# ║  lookup + baseline for each NA row, and writes a versioned       ║
# ║  interim CSV with provenance columns appended.                   ║
# ╚══════════════════════════════════════════════════════════════════╝
"""CLI: fill day_temp_C and period-correct decade_mean_temp_C."""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Backfill day_temp_C and decade_mean_temp_C with provenance tracking."""
    parser = argparse.ArgumentParser(
        prog="thermostrife-backfill",
        description="Fill day_temp_C and period-correct decadal baselines.",
    )
    parser.add_argument("input_csv", type=Path, help="Curated uprisings CSV.")
    parser.add_argument(
        "--output", "-o", type=Path, required=True,
        help="Path to the backfilled interim CSV to write.",
    )
    parser.add_argument(
        "--tier-floor", type=int, default=4,
        help="Skip rows whose only available tier is worse than this (1-4).",
    )
    args = parser.parse_args(argv)

    raise NotImplementedError(
        f"backfill.main() awaits thermostrife.lookup.resolve() and "
        f"thermostrife.baseline.compute_baseline() "
        f"(would have processed {args.input_csv} -> {args.output})."
    )


if __name__ == "__main__":
    raise SystemExit(main())
