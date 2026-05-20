# ╔══════════════════════════════════════════════════════════════════╗
# ║  ThermoStrife — viz                                              ║
# ║  « Wong-palette raincloud + null-density figures »               ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  All plots use the Wong (2011) palette from constants.           ║
# ║  Triple output: SVG (svg.fonttype = 'none') + PNG + CSV.         ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Plotting helpers.  Rainclouds, not bar charts."""

from __future__ import annotations

from pathlib import Path


def plot_anomaly_raincloud(
    event_anomaly: "np.ndarray",
    control_anomaly: "np.ndarray | None",
    output_dir: Path,
    stem: str = "anomaly_raincloud",
) -> Path:
    """Half-violin + jittered strip + boxplot for event vs control anomaly."""
    raise NotImplementedError("viz.plot_anomaly_raincloud not yet implemented.")


def plot_null_density(
    observed_stat: float,
    null_draws: "np.ndarray",
    output_dir: Path,
    stem: str = "null_density",
) -> Path:
    """Permutation-null density with the observed statistic marked."""
    raise NotImplementedError("viz.plot_null_density not yet implemented.")
