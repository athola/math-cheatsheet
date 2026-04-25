"""Tests for scripts/competition_sim.py (regression #24)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import competition_sim as sim  # noqa: E402


class TestWilsonCI:
    """
    Feature: Report accuracy with a Wilson 95% CI.

    As a competition operator
    I want a CI that behaves at the 0/1 boundaries
    So that small samples with perfect scores don't spuriously report 100%.
    """

    @pytest.mark.unit
    def test_center_matches_proportion(self):
        low, high = sim.wilson_ci(50, 100)
        # For p=0.5, n=100 the Wilson interval is symmetric around ~0.5.
        assert 0.39 < low < 0.41
        assert 0.59 < high < 0.61
        assert low < 0.5 < high

    @pytest.mark.unit
    def test_all_success_not_exactly_one(self):
        """Perfect 100 for 100 must still give a <1.0 upper bound interpretation.

        We accept upper == 1.0 but require low < 1.0 — the hallmark of a
        principled interval for boundary proportions.
        """
        low, high = sim.wilson_ci(100, 100)
        assert low < 1.0
        assert high == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.unit
    def test_zero_total_returns_zero_zero(self):
        assert sim.wilson_ci(0, 0) == (0.0, 0.0)


class _FakeOracle:
    """Minimal oracle stand-in for sample_pairs tests."""

    def __init__(self, truth: dict[tuple[int, int], bool | None]):
        self._truth = truth
        self._eq_ids = sorted({h for h, _ in truth})
        self._col_eq_ids = sorted({t for _, t in truth})

    def query(self, h: int, t: int) -> bool | None:
        return self._truth.get((h, t))


class TestSamplePairs:
    """
    Feature: Draw N oracle-decidable pairs for evaluation.

    As a simulator
    I want deterministic sampling with a seeded RNG
    So that runs are reproducible and None-verdict cells are skipped.
    """

    @pytest.mark.unit
    def test_skips_none_truth(self):
        """Scenario: the only decidable cells are (1,1) and (1,2); sample 2."""
        truth = {(1, 1): True, (1, 2): False, (2, 1): None, (2, 2): None}
        oracle = _FakeOracle(truth)
        pairs = sim.sample_pairs(oracle, 2, random.Random(42))
        assert len(pairs) == 2
        for h, t, actual in pairs:
            assert (h, t) in {(1, 1), (1, 2)}
            assert isinstance(actual, bool)

    @pytest.mark.unit
    def test_raises_when_cannot_find_enough(self):
        """When no cells are decidable, sample_pairs must fail loudly."""
        truth = {(1, 1): None, (1, 2): None, (2, 1): None, (2, 2): None}
        oracle = _FakeOracle(truth)
        with pytest.raises(RuntimeError, match="Could only draw"):
            sim.sample_pairs(oracle, 5, random.Random(0))
