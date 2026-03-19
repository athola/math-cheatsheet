"""Tests for evaluate_v4 module.

Tests the v4_predict function using small synthetic fixtures.
"""

import csv
from pathlib import Path

import pytest

from etp_equations import ETPEquations
from evaluate_v4 import v4_predict
from implication_oracle import ImplicationOracle


@pytest.fixture
def equations_file(tmp_path: Path) -> Path:
    """5 equations: tautology, collapse, commutativity, projection, 3-var."""
    eq_path = tmp_path / "equations.txt"
    eq_path.write_text(
        "x = x\nx = y\nx ◇ y = y ◇ x\nx ◇ y = x\nx ◇ y = z\n",
        encoding="utf-8",
    )
    return eq_path


@pytest.fixture
def oracle_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "implications.csv"
    matrix = [
        [3, -3, -3, -3, -3],
        [3, 3, 3, 3, 3],
        [3, -3, 3, -3, -3],
        [3, -3, -3, 3, -3],
        [3, 3, -3, -3, 3],
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in matrix:
            writer.writerow(row)
    return csv_path


@pytest.fixture
def eqs(equations_file: Path) -> ETPEquations:
    return ETPEquations(equations_file)


@pytest.fixture
def oracle(oracle_csv: Path) -> ImplicationOracle:
    return ImplicationOracle(oracle_csv)


class TestV4Predict:
    """Test v4_predict with empty tier sets (simplified scenario)."""

    def test_self_implication(self, eqs, oracle):
        assert v4_predict(3, 3, eqs, set(), set(), set(), set(), oracle) is True

    def test_tautology_target(self, eqs, oracle):
        assert v4_predict(3, 1, eqs, set(), set(), set(), set(), oracle) is True

    def test_collapse_hypothesis(self, eqs, oracle):
        assert v4_predict(2, 4, eqs, {2}, set(), set(), set(), oracle) is True

    def test_tautology_hypothesis(self, eqs, oracle):
        assert v4_predict(1, 3, eqs, set(), set(), set(), set(), oracle) is False

    def test_new_vars_weak_equation(self, eqs, oracle):
        """Eq4 (x,y) -> Eq5 (x,y,z): new var z, weak equation -> FALSE."""
        assert v4_predict(4, 5, eqs, set(), set(), set(), set(), oracle) is False

    def test_default_false(self, eqs, oracle):
        """When no rule matches, default to FALSE."""
        assert v4_predict(3, 4, eqs, set(), set(), set(), set(), oracle) is False
