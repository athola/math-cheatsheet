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


class TestMainIntegration:
    """End-to-end smoke test for competition_sim.main (#51).

    Pre-existing tests covered ``wilson_ci`` and ``sample_pairs`` in
    isolation; ``main`` itself was never invoked, so a regression in the
    JSON output schema or the argparse wiring would slip through.
    """

    @pytest.fixture
    def synthetic_oracle_csv(self, tmp_path):
        """A 5x5 ETP-encoded matrix with a tautology, collapse, and three weak rows."""
        import csv as _csv

        csv_path = tmp_path / "implications.csv"
        matrix = [
            [3, -3, -3, -3, -3],
            [3, 3, 3, 3, 3],
            [3, -3, 3, -3, -3],
            [3, -3, -3, 3, -3],
            [3, -3, -3, -3, 3],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = _csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        return csv_path

    @pytest.fixture
    def synthetic_equations_file(self, tmp_path):
        eq_path = tmp_path / "equations.txt"
        eq_path.write_text(
            "x = x\nx = y\nx ◇ y = y ◇ x\nx ◇ y = x\nx ◇ y = z\n",
            encoding="utf-8",
        )
        return eq_path

    @pytest.mark.unit
    def test_main_writes_results_json_with_expected_schema(
        self, tmp_path, synthetic_oracle_csv, synthetic_equations_file
    ):
        out_path = tmp_path / "result.json"
        cheatsheet = tmp_path / "cheatsheet.txt"
        cheatsheet.write_text("dummy cheatsheet", encoding="utf-8")

        rc = sim.main(
            [
                "--n",
                "3",
                "--seed",
                "1",
                "--oracle",
                str(synthetic_oracle_csv),
                "--equations",
                str(synthetic_equations_file),
                "--cheatsheet",
                str(cheatsheet),
                "--out",
                str(out_path),
            ]
        )
        assert rc == 0
        assert out_path.exists()

        import json as _json

        result = _json.loads(out_path.read_text(encoding="utf-8"))
        assert result["n"] == 3
        assert result["seed"] == 1
        assert 0 <= result["accuracy"] <= 1.0
        assert 0 <= result["ci95_low"] <= result["ci95_high"] <= 1.0
        assert len(result["per_problem"]) == 3
        for entry in result["per_problem"]:
            assert set(entry.keys()) == {"h_id", "t_id", "actual", "predicted", "correct"}
            assert isinstance(entry["correct"], bool)

    @pytest.mark.unit
    def test_main_default_seed_is_reproducible(
        self, tmp_path, synthetic_oracle_csv, synthetic_equations_file
    ):
        """Same seed → identical per-problem output (catches RNG drift)."""
        cheatsheet = tmp_path / "cheatsheet.txt"
        cheatsheet.write_text("dummy", encoding="utf-8")

        out_a = tmp_path / "a.json"
        out_b = tmp_path / "b.json"
        common = [
            "--n",
            "5",
            "--seed",
            "42",
            "--oracle",
            str(synthetic_oracle_csv),
            "--equations",
            str(synthetic_equations_file),
            "--cheatsheet",
            str(cheatsheet),
        ]
        sim.main([*common, "--out", str(out_a)])
        sim.main([*common, "--out", str(out_b)])

        import json as _json

        a = _json.loads(out_a.read_text(encoding="utf-8"))
        b = _json.loads(out_b.read_text(encoding="utf-8"))
        assert a["per_problem"] == b["per_problem"]
