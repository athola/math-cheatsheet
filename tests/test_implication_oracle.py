"""Tests for ImplicationOracle.

Uses a small synthetic 4x4 CSV fixture representing 4 equations:
  Eq1: tautology (x=x) - implies only itself
  Eq2: collapse (x=y) - implies everything
  Eq3: commutativity - mid-strength
  Eq4: associativity - mid-strength
"""

import csv
from pathlib import Path

import numpy as np
import pytest

from implication_oracle import ImplicationOracle


@pytest.fixture
def oracle_csv(tmp_path: Path) -> Path:
    """Create a small 4x4 implication matrix CSV.

    Matrix encodes:
      Row/Col  Eq1   Eq2   Eq3   Eq4
      Eq1       3    -3    -3    -3     tautology: implies only itself
      Eq2       3     3     3     3     collapse: implies everything
      Eq3       3    -3     3    -3     commutativity: implies 1,3
      Eq4       3    -3    -3     3     associativity: implies 1,4
    """
    csv_path = tmp_path / "implications.csv"
    matrix = [
        [3, -3, -3, -3],
        [3, 3, 3, 3],
        [3, -3, 3, -3],
        [3, -3, -3, 3],
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in matrix:
            writer.writerow(row)
    return csv_path


@pytest.fixture
def oracle(oracle_csv: Path) -> ImplicationOracle:
    return ImplicationOracle(oracle_csv)


class TestLoading:
    def test_shape(self, oracle: ImplicationOracle):
        assert oracle.shape == (4, 4)

    def test_num_equations(self, oracle: ImplicationOracle):
        assert oracle.num_equations == 4

    def test_matrix_dtype(self, oracle: ImplicationOracle):
        assert oracle._matrix.dtype == np.int8


class TestQuery:
    def test_self_implication(self, oracle: ImplicationOracle):
        """Diagonal entries are all TRUE (self-implication)."""
        for eq_id in range(1, 5):
            assert oracle.query(eq_id, eq_id) is True

    def test_tautology_implies_only_itself(self, oracle: ImplicationOracle):
        assert oracle.query(1, 1) is True
        assert oracle.query(1, 2) is False
        assert oracle.query(1, 3) is False
        assert oracle.query(1, 4) is False

    def test_collapse_implies_everything(self, oracle: ImplicationOracle):
        for t_id in range(1, 5):
            assert oracle.query(2, t_id) is True

    def test_commutativity_implications(self, oracle: ImplicationOracle):
        assert oracle.query(3, 1) is True
        assert oracle.query(3, 2) is False
        assert oracle.query(3, 3) is True
        assert oracle.query(3, 4) is False

    def test_out_of_range_returns_none(self, oracle: ImplicationOracle):
        assert oracle.query(0, 1) is None
        assert oracle.query(1, 5) is None
        assert oracle.query(99, 99) is None


class TestQueryRaw:
    def test_returns_raw_value(self, oracle: ImplicationOracle):
        assert oracle.query_raw(1, 1) == 3
        assert oracle.query_raw(1, 2) == -3

    def test_out_of_range_returns_zero(self, oracle: ImplicationOracle):
        assert oracle.query_raw(99, 1) == 0
        assert oracle.query_raw(1, 99) == 0


class TestRowColCounts:
    def test_tautology_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(1) == 1

    def test_collapse_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(2) == 4

    def test_mid_strength_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(3) == 2
        assert oracle.row_true_count(4) == 2

    def test_out_of_range_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(99) == 0

    def test_tautology_col_count(self, oracle: ImplicationOracle):
        """Everything implies the tautology."""
        assert oracle.col_true_count(1) == 4

    def test_collapse_col_count(self, oracle: ImplicationOracle):
        """Only collapse implies itself here."""
        assert oracle.col_true_count(2) == 1

    def test_out_of_range_col_count(self, oracle: ImplicationOracle):
        assert oracle.col_true_count(99) == 0


class TestClassification:
    def test_tautology(self, oracle: ImplicationOracle):
        assert oracle.classify(1) == "tautology"

    def test_collapse(self, oracle: ImplicationOracle):
        assert oracle.classify(2) == "collapse"

    def test_weak(self, oracle: ImplicationOracle):
        assert oracle.classify(3) == "weak"
        assert oracle.classify(4) == "weak"

    def test_is_collapse(self, oracle: ImplicationOracle):
        assert oracle.is_collapse(2) is True
        assert oracle.is_collapse(1) is False
        assert oracle.is_collapse(3) is False


class TestStats:
    def test_stats_keys(self, oracle: ImplicationOracle):
        stats = oracle.stats()
        assert "shape" in stats
        assert "proven_true" in stats
        assert "proven_false" in stats
        assert stats["equation_ids"] == (1, 4)

    def test_stats_counts(self, oracle: ImplicationOracle):
        stats = oracle.stats()
        assert stats["proven_true"] == 9  # count of 3s: 1+4+2+2
        assert stats["proven_false"] == 7  # count of -3s: 3+0+2+2
        assert stats["conj_true"] == 0
        assert stats["conj_false"] == 0


class TestAccuracyOf:
    def test_perfect_predictor(self, oracle: ImplicationOracle):
        """A predictor that always matches the oracle gets 100% accuracy."""
        result = oracle.accuracy_of(lambda h, t: oracle.query(h, t))
        assert result["accuracy"] == 1.0
        assert result["fp"] == 0
        assert result["fn"] == 0

    def test_always_true_predictor(self, oracle: ImplicationOracle):
        """Always-true predictor gets all TPs right but many FPs."""
        result = oracle.accuracy_of(lambda _h, _t: True)
        assert result["tp"] == 9
        assert result["fp"] == 7
        assert result["tn"] == 0
        assert result["fn"] == 0
        assert result["recall"] == 1.0

    def test_always_false_predictor(self, oracle: ImplicationOracle):
        """Always-false predictor gets all TNs right but many FNs."""
        result = oracle.accuracy_of(lambda _h, _t: False)
        assert result["tp"] == 0
        assert result["fp"] == 0
        assert result["tn"] == 7
        assert result["fn"] == 9
        assert result["precision"] == 0.0


class TestConjValueHandling:
    """Test that conjectured values (4, -4) are treated like proven."""

    def test_conjectured_true(self, tmp_path: Path):
        csv_path = tmp_path / "conj.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([4, -4])
            writer.writerow([-4, 4])
        oracle = ImplicationOracle(csv_path)
        assert oracle.query(1, 1) is True
        assert oracle.query(1, 2) is False
        assert oracle.query(2, 1) is False
        assert oracle.query(2, 2) is True
