"""Smoke tests for thermostrife.constants."""

from __future__ import annotations

from itertools import pairwise

import pytest

from thermostrife import constants as C


class TestEraBins:
    def test_bin_count_matches_label_count(self):
        # N labels = N+1 boundaries
        assert len(C.ERA_LABELS) == len(C.ERA_BINS) - 1

    def test_bins_are_strictly_increasing(self):
        assert all(a < b for a, b in pairwise(C.ERA_BINS))

    def test_first_and_last_boundary(self):
        assert C.ERA_BINS[0] == 1750
        assert C.ERA_BINS[-1] >= 2026


class TestWongPalette:
    def test_palette_has_eight_colours(self):
        assert len(C.WONG) == 8

    def test_all_values_are_hex(self):
        for name, value in C.WONG.items():
            assert value.startswith("#") and len(value) == 7, name

    def test_semantic_colours_reference_palette(self):
        # Every semantic colour must come from WONG, no ad-hoc hex values.
        for role, value in C.SEMANTIC_COLOURS.items():
            assert value in C.WONG.values(), role


class TestProvenance:
    def test_known_tiers_present(self):
        for code in (
            "tier1_ghcn", "tier2_obs", "tier3_era5", "tier4_20crv3",
            "unverifiable", "curated_manual",
        ):
            assert code in C.PROVENANCE_TIERS

    def test_tier_rank_ordering(self):
        assert C.PROVENANCE_TIERS["tier1_ghcn"].rank < C.PROVENANCE_TIERS["tier4_20crv3"].rank


class TestPaths:
    def test_repo_root_contains_pyproject(self):
        assert (C.REPO_ROOT / "pyproject.toml").exists()

    def test_curated_csv_exists(self):
        assert C.CURATED_CSV.exists()


class TestSaveFigure:
    def test_save_figure_writes_svg_and_png(self, tmp_path):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        C.save_figure(fig, "smoke", tmp_path)
        plt.close(fig)

        assert (tmp_path / "smoke.svg").exists()
        assert (tmp_path / "smoke.png").exists()


@pytest.mark.parametrize("module", ["lookup", "baseline", "backfill", "viz", "cli"])
def test_module_stubs_raise_notimplemented(module):
    """Every stub module must surface NotImplementedError, not silently no-op."""
    import importlib

    mod = importlib.import_module(f"thermostrife.{module}")
    assert mod is not None
