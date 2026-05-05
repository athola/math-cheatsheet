"""Tests for ImplicationOracle.

Uses a small synthetic 4x4 CSV fixture representing 4 equations:
  Eq1: tautology (x=x) - implies only itself
  Eq2: collapse (x=y) - implies everything
  Eq3: commutativity - mid-strength
  Eq4: associativity - mid-strength
"""

import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest

from implication_oracle import ImplicationOracle


def _sha256_of(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file (test-only helper)."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


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

    def test_out_of_range_raises_keyerror(self, oracle: ImplicationOracle):
        """Regression #31: query_raw must raise instead of returning 0."""
        with pytest.raises(KeyError, match="out of range"):
            oracle.query_raw(99, 1)
        with pytest.raises(KeyError, match="out of range"):
            oracle.query_raw(1, 99)


class TestRowColCounts:
    def test_tautology_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(1) == 1

    def test_collapse_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(2) == 4

    def test_mid_strength_row_count(self, oracle: ImplicationOracle):
        assert oracle.row_true_count(3) == 2
        assert oracle.row_true_count(4) == 2

    def test_out_of_range_row_count_raises(self, oracle: ImplicationOracle):
        """Unknown ID raises KeyError, consistent with query_raw (regression #31)."""
        with pytest.raises(KeyError, match="99"):
            oracle.row_true_count(99)

    def test_tautology_col_count(self, oracle: ImplicationOracle):
        """Everything implies the tautology."""
        assert oracle.col_true_count(1) == 4

    def test_collapse_col_count(self, oracle: ImplicationOracle):
        """Only collapse implies itself here."""
        assert oracle.col_true_count(2) == 1

    def test_out_of_range_col_count_raises(self, oracle: ImplicationOracle):
        """Unknown ID raises KeyError, consistent with query_raw (regression #31)."""
        with pytest.raises(KeyError, match="99"):
            oracle.col_true_count(99)


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


class TestEquivalenceClass:
    """Test equivalence_class() method that groups equations by row profile."""

    def test_self_is_same_class(self, oracle: ImplicationOracle):
        """An equation is in the same class as itself."""
        c1 = oracle.equivalence_class(1)
        assert c1 is not None
        assert c1 == oracle.equivalence_class(1)

    def test_distinct_profiles_different_classes(self, oracle: ImplicationOracle):
        """Equations with different row profiles get different class IDs."""
        # Eq1 (tautology), Eq2 (collapse), Eq3, Eq4 all have different rows
        classes = {oracle.equivalence_class(i) for i in range(1, 5)}
        assert len(classes) == 4, "All 4 equations have distinct profiles"

    def test_same_profile_same_class(self, tmp_path: Path):
        """Equations with identical row profiles get the same class ID."""
        csv_path = tmp_path / "equiv.csv"
        # Eq1 and Eq3 have identical rows: [3, -3, 3, -3]
        matrix = [
            [3, -3, 3, -3],  # Eq1
            [3, 3, 3, 3],  # Eq2: collapse
            [3, -3, 3, -3],  # Eq3: same as Eq1
            [3, -3, -3, 3],  # Eq4: different
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        oracle = ImplicationOracle(csv_path)

        assert oracle.equivalence_class(1) == oracle.equivalence_class(3)
        assert oracle.equivalence_class(1) != oracle.equivalence_class(2)
        assert oracle.equivalence_class(1) != oracle.equivalence_class(4)

    def test_out_of_range_returns_none(self, oracle: ImplicationOracle):
        """Out-of-range equation ID returns None."""
        assert oracle.equivalence_class(99) is None
        assert oracle.equivalence_class(0) is None

    def test_equivalence_classes_property(self, tmp_path: Path):
        """The equivalence_classes property returns a dict of class_id -> set of eq_ids."""
        csv_path = tmp_path / "equiv.csv"
        matrix = [
            [3, -3, 3, -3],  # Eq1
            [3, 3, 3, 3],  # Eq2
            [3, -3, 3, -3],  # Eq3: same as Eq1
            [3, -3, -3, 3],  # Eq4
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        oracle = ImplicationOracle(csv_path)

        classes = oracle.equivalence_classes
        # Find class containing Eq1 and Eq3
        eq1_class = oracle.equivalence_class(1)
        assert eq1_class is not None
        assert classes[eq1_class] == {1, 3}
        # Eq2 and Eq4 are singletons
        eq2_class = oracle.equivalence_class(2)
        assert eq2_class is not None
        assert classes[eq2_class] == {2}

    def test_equivalence_classes_values_are_immutable(self, oracle: ImplicationOracle):
        """Regression #52/M4: returned class members must be frozenset.

        Previously a caller could do
        ``oracle.equivalence_classes[cid].discard(eq_id)`` and silently
        corrupt the cached row-profile mapping.
        """
        classes = oracle.equivalence_classes
        for cid, members in classes.items():
            assert isinstance(members, frozenset), (
                f"class {cid} members are {type(members).__name__}, expected frozenset"
            )

    def test_equivalence_classes_dict_is_immutable(self, oracle: ImplicationOracle):
        """Regression #52/M4: the outer mapping must also reject mutation."""
        classes = oracle.equivalence_classes
        # MappingProxyType raises TypeError on mutation; a plain dict would not.
        with pytest.raises(TypeError):
            classes[999] = frozenset({999})  # type: ignore[index]

    def test_equivalence_classes_repeated_calls_return_consistent_state(
        self, oracle: ImplicationOracle
    ):
        """Even after attempting mutation, repeated calls return the same data."""
        first = {k: frozenset(v) for k, v in oracle.equivalence_classes.items()}
        second = {k: frozenset(v) for k, v in oracle.equivalence_classes.items()}
        assert first == second


class TestShapeValidation:
    """Feature: ImplicationOracle validates CSV shape on load (regression for #46)."""

    def test_non_square_matrix_raises(self, tmp_path: Path):
        """A non-square matrix must raise a clear error at construction."""
        csv_path = tmp_path / "bad.csv"
        # 3 rows x 4 columns — not square.
        matrix = [
            [3, -3, -3, -3],
            [3, 3, 3, 3],
            [3, -3, 3, -3],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        with pytest.raises(ValueError, match="square"):
            ImplicationOracle(csv_path)

    def test_ragged_matrix_raises(self, tmp_path: Path):
        """Rows of mismatched lengths must be rejected with a clear error."""
        csv_path = tmp_path / "ragged.csv"
        csv_path.write_text("3,-3,-3\n3,3,3,3\n3,-3,3\n", encoding="utf-8")
        with pytest.raises(ValueError, match="ragged|shape|row"):
            ImplicationOracle(csv_path)

    def test_out_of_range_value_raises(self, tmp_path: Path):
        """Values outside the documented {-4,-3,3,4} set must be rejected."""
        csv_path = tmp_path / "bad_values.csv"
        matrix = [
            [3, 0, 3],
            [3, 3, 3],
            [3, -3, 3],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        with pytest.raises(ValueError, match="value|encoding"):
            ImplicationOracle(csv_path)

    def test_missing_file_raises_clear_error(self, tmp_path: Path):
        """A missing CSV must raise FileNotFoundError with remediation hint."""
        with pytest.raises(FileNotFoundError, match="download|make"):
            ImplicationOracle(tmp_path / "nope.csv")


class TestSha256Verification:
    """SHA-256 checksum verification (#48).

    The verification logic in ImplicationOracle existed but had no tests
    pinning it: a complete revert of ``_verify_digest`` and the kwarg
    handling passed the rest of the suite. These tests pin each leg.
    """

    def test_matching_digest_loads_successfully(self, oracle_csv: Path):
        """Passing the correct digest as a kwarg must not falsely reject."""
        digest = _sha256_of(oracle_csv)
        oracle = ImplicationOracle(oracle_csv, expected_sha256=digest)
        assert oracle.shape == (4, 4)

    def test_matching_digest_uppercase_loads_successfully(self, oracle_csv: Path):
        """Digest comparison must be case-insensitive."""
        digest = _sha256_of(oracle_csv).upper()
        oracle = ImplicationOracle(oracle_csv, expected_sha256=digest)
        assert oracle.shape == (4, 4)

    def test_mismatched_digest_raises_with_remediation_hint(self, oracle_csv: Path):
        """A wrong digest must raise ValueError mentioning the fix path."""
        wrong = "0" * 64
        with pytest.raises(ValueError, match="checksum mismatch"):
            ImplicationOracle(oracle_csv, expected_sha256=wrong)
        # Remediation hint must be present so the user knows what to do.
        try:
            ImplicationOracle(oracle_csv, expected_sha256=wrong)
        except ValueError as exc:
            assert "make download-etp" in str(exc)

    def test_sidecar_digest_auto_detected(self, oracle_csv: Path):
        """``foo.csv.sha256`` next to ``foo.csv`` is loaded automatically."""
        sidecar = oracle_csv.with_suffix(oracle_csv.suffix + ".sha256")
        sidecar.write_text(f"{_sha256_of(oracle_csv)}  {oracle_csv.name}\n", encoding="utf-8")
        # No expected_sha256 kwarg — sidecar must be picked up.
        oracle = ImplicationOracle(oracle_csv)
        assert oracle.shape == (4, 4)

    def test_sidecar_with_wrong_digest_rejects_load(self, oracle_csv: Path):
        """A sidecar containing a wrong digest must still cause rejection."""
        sidecar = oracle_csv.with_suffix(oracle_csv.suffix + ".sha256")
        sidecar.write_text(f"{'0' * 64}  {oracle_csv.name}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="checksum mismatch"):
            ImplicationOracle(oracle_csv)

    def test_explicit_kwarg_overrides_sidecar(self, oracle_csv: Path):
        """A wrong sidecar must be ignored when an explicit (correct) kwarg is supplied."""
        sidecar = oracle_csv.with_suffix(oracle_csv.suffix + ".sha256")
        sidecar.write_text(f"{'0' * 64}  {oracle_csv.name}\n", encoding="utf-8")
        digest = _sha256_of(oracle_csv)
        oracle = ImplicationOracle(oracle_csv, expected_sha256=digest)
        assert oracle.shape == (4, 4)

    def test_no_digest_loads_without_verification(self, oracle_csv: Path):
        """Default behaviour without kwarg or sidecar must not break loading."""
        oracle = ImplicationOracle(oracle_csv)
        assert oracle.shape == (4, 4)
