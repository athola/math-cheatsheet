"""Tests for the ETP equation parser, classifier, and unified query interface."""

import time

import pytest

from etp_equations import Equation, ETPEquations, op, parse_equation, var
from implication_oracle import ImplicationOracle

# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------


class TestTermParsing:
    """
    Feature: Parse ETP equation strings into ASTs.

    As a competition tool
    I want to parse all 4694 ETP equations correctly
    So that structural analysis is accurate.
    """

    @pytest.mark.unit
    def test_parse_tautology(self):
        """Scenario: x = x is a tautology."""
        eq = parse_equation(1, "x = x")
        assert eq.is_tautology
        assert eq.var_count == 1
        assert eq.max_depth == 0

    @pytest.mark.unit
    def test_parse_collapse_xy(self):
        """Scenario: x = y has two variables, depth 0."""
        eq = parse_equation(2, "x = y")
        assert not eq.is_tautology
        assert eq.var_count == 2
        assert eq.variables == frozenset({"x", "y"})

    @pytest.mark.unit
    def test_parse_commutativity(self):
        """Scenario: x ◇ y = y ◇ x has correct structure."""
        eq = parse_equation(43, "x ◇ y = y ◇ x")
        assert eq.var_count == 2
        assert eq.max_depth == 1
        assert eq.total_ops == 2
        assert not eq.is_tautology

    @pytest.mark.unit
    def test_parse_associativity(self):
        """Scenario: Associativity has depth 2."""
        eq = parse_equation(4512, "x ◇ (y ◇ z) = (x ◇ y) ◇ z")
        assert eq.var_count == 3
        assert eq.max_depth == 2
        assert eq.total_ops == 4

    @pytest.mark.unit
    def test_parse_diamond_operator(self):
        """Scenario: diamond operator is parsed correctly."""
        eq = parse_equation(7, "x = y ◇ z")
        assert eq.lhs.is_var
        assert not eq.rhs.is_var
        assert eq.rhs.variables() == frozenset({"y", "z"})

    @pytest.mark.unit
    def test_parse_nested_expression(self):
        """Scenario: Deeply nested expression parses correctly."""
        eq = parse_equation(100, "x = x ◇ (x ◇ (x ◇ y))")
        assert eq.max_depth == 3
        assert eq.var_count == 2

    @pytest.mark.unit
    def test_no_equals_raises(self):
        """Scenario: Missing = sign raises ValueError."""
        with pytest.raises(ValueError, match="No '='"):
            parse_equation(0, "x y")

    @pytest.mark.unit
    def test_term_structural_equality(self):
        """Scenario: Identical terms compare equal (frozen dataclass)."""
        t1 = op(var("x"), var("y"))
        t2 = op(var("x"), var("y"))
        assert t1 == t2

    @pytest.mark.unit
    def test_term_substitution(self):
        """Scenario: Variable substitution works."""
        t = op(var("x"), var("y"))
        result = t.substitute({"y": var("x")})
        expected = op(var("x"), var("x"))
        assert result == expected


class TestETPEquations:
    """
    Feature: Load and query all 4694 ETP equations.
    """

    @pytest.fixture
    def etp(self):
        return ETPEquations("research/data/etp/equations.txt")

    @pytest.mark.unit
    def test_loads_all_4694(self, etp):
        """Scenario: All 4694 equations are loaded."""
        assert len(etp) == 4694

    @pytest.mark.unit
    def test_equation_1_is_tautology(self, etp):
        """Scenario: E1 is x = x (tautology)."""
        assert etp[1].is_tautology
        assert etp[1].text == "x = x"

    @pytest.mark.unit
    def test_equation_2_is_collapse(self, etp):
        """Scenario: E2 (x = y) is structurally collapse."""
        assert etp.is_collapse_structural(2)

    @pytest.mark.unit
    def test_variable_analysis(self, etp):
        """Scenario: Detect new variables in target."""
        # E3 (x = x◇x) has {x}, E43 (x◇y = y◇x) has {x, y}
        new_vars = etp.vars_in_target_not_in_hypothesis(3, 43)
        assert "y" in new_vars

    @pytest.mark.unit
    def test_no_new_vars_same_equation(self, etp):
        """Scenario: Same variable set has no new vars."""
        new_vars = etp.vars_in_target_not_in_hypothesis(43, 43)
        assert len(new_vars) == 0


# ---------------------------------------------------------------------------
# New tests for classification
# ---------------------------------------------------------------------------


class TestETPClassifyStructural:
    """
    Feature: Classify equations structurally without the oracle.

    Categories:
    - tautology: LHS == RHS (e.g. x = x)
    - collapse: forces |M|=1 (e.g. x = y)
    - trivial_lhs: LHS is a single variable (e.g. x = x ◇ y)
    - trivial_rhs: RHS is a single variable
    - balanced: both sides have operations
    """

    @pytest.fixture
    def etp(self):
        return ETPEquations("research/data/etp/equations.txt")

    @pytest.mark.unit
    def test_tautology_classified(self, etp):
        """E1 (x = x) is classified as tautology."""
        assert etp.classify_structural(1) == "tautology"

    @pytest.mark.unit
    def test_collapse_classified(self, etp):
        """E2 (x = y) is classified as collapse."""
        assert etp.classify_structural(2) == "collapse"

    @pytest.mark.unit
    def test_equation_7_collapse(self, etp):
        """E7 (x = y ◇ z) is structurally collapse."""
        assert etp.classify_structural(7) == "collapse"

    @pytest.mark.unit
    def test_trivial_lhs(self, etp):
        """E3 (x = x ◇ x) has LHS as single var, not tautology/collapse."""
        cls = etp.classify_structural(3)
        assert cls == "trivial_lhs"

    @pytest.mark.unit
    def test_balanced_equation(self, etp):
        """E43 (x ◇ y = y ◇ x) has operations on both sides."""
        cls = etp.classify_structural(43)
        assert cls == "balanced"

    @pytest.mark.unit
    def test_all_equations_classified(self, etp):
        """Every equation gets a classification."""
        valid_categories = {"tautology", "collapse", "trivial_lhs", "trivial_rhs", "balanced"}
        for eq_id in etp.ids():
            cls = etp.classify_structural(eq_id)
            assert cls in valid_categories, f"E{eq_id} got unexpected class: {cls}"

    @pytest.mark.unit
    def test_classification_distribution_plausible(self, etp):
        """Structural classification distribution is plausible."""
        from collections import Counter

        counts: Counter[str] = Counter()
        for eq_id in etp.ids():
            counts[etp.classify_structural(eq_id)] += 1
        # There should be exactly 1 tautology (E1)
        assert counts["tautology"] == 1
        # There should be at least a few collapse equations
        assert counts["collapse"] >= 2
        # trivial_lhs is common (many equations are x = ...)
        assert counts["trivial_lhs"] > 0
        # balanced should be substantial
        assert counts["balanced"] > 100


# ---------------------------------------------------------------------------
# New tests for query timing
# ---------------------------------------------------------------------------


class TestQueryTiming:
    """
    Feature: Query any (eq_i, eq_j) pair in <1ms.

    The implication matrix is backed by a numpy array, so lookups
    should be essentially O(1).
    """

    @pytest.fixture(scope="class")
    def oracle(self):
        import pathlib

        csv_path = pathlib.Path("research/data/etp/implications.csv")
        if not csv_path.exists():
            pytest.skip("implications.csv not available")
        return ImplicationOracle(str(csv_path))

    @pytest.mark.unit
    def test_single_query_under_1ms(self, oracle):
        """A single oracle.query() call completes in under 1ms."""
        # Warm up
        oracle.query(43, 4512)

        start = time.perf_counter()
        oracle.query(43, 4512)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1.0, f"Single query took {elapsed_ms:.3f}ms (limit: 1ms)"

    @pytest.mark.unit
    def test_batch_queries_fast(self, oracle):
        """1000 queries complete in under 100ms (0.1ms each on average)."""
        pairs = [(i, j) for i in range(1, 32) for j in range(1, 33)]
        # Warm up
        for h, t in pairs[:10]:
            oracle.query(h, t)

        start = time.perf_counter()
        for h, t in pairs:
            oracle.query(h, t)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100.0, f"1000 queries took {elapsed_ms:.1f}ms (limit: 100ms)"


# ---------------------------------------------------------------------------
# New tests for edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """
    Feature: Edge case handling for boundary equations.
    """

    @pytest.fixture
    def etp(self):
        return ETPEquations("research/data/etp/equations.txt")

    @pytest.mark.unit
    def test_equation_1_tautology_properties(self, etp):
        """E1 (x = x): single variable, depth 0, tautology."""
        eq = etp[1]
        assert eq.is_tautology is True
        assert eq.var_count == 1
        assert eq.max_depth == 0
        assert eq.total_ops == 0
        assert eq.lhs_is_var is True
        assert eq.rhs_is_var is True

    @pytest.mark.unit
    def test_equation_2_collapse_properties(self, etp):
        """E2 (x = y): two variables, both are bare vars, collapse."""
        eq = etp[2]
        assert eq.is_tautology is False
        assert eq.var_count == 2
        assert eq.max_depth == 0
        assert eq.lhs_is_var is True
        assert eq.rhs_is_var is True
        assert etp.is_collapse_structural(2) is True

    @pytest.mark.unit
    def test_first_and_last_equation_exist(self, etp):
        """E1 and E4694 both exist."""
        assert 1 in etp
        assert 4694 in etp

    @pytest.mark.unit
    def test_equation_0_does_not_exist(self, etp):
        """E0 does not exist (equations are 1-indexed)."""
        assert 0 not in etp

    @pytest.mark.unit
    def test_equation_4695_does_not_exist(self, etp):
        """E4695 does not exist (only 4694 equations)."""
        assert 4695 not in etp

    @pytest.mark.unit
    def test_getitem_raises_for_missing(self, etp):
        """Accessing a missing equation raises KeyError."""
        with pytest.raises(KeyError):
            etp[0]


# ---------------------------------------------------------------------------
# New tests for ETPDataset (unified query interface)
# ---------------------------------------------------------------------------


class TestETPDataset:
    """
    Feature: Unified query interface combining equations + oracle.

    ETPDataset provides one-stop access to structural features,
    implication queries, and classifications.
    """

    @pytest.fixture(scope="class")
    def dataset(self):
        import pathlib

        from etp_equations import ETPDataset

        csv_path = pathlib.Path("research/data/etp/implications.csv")
        if not csv_path.exists():
            pytest.skip("implications.csv not available")
        return ETPDataset(
            equations_path="research/data/etp/equations.txt",
            implications_path=str(csv_path),
        )

    @pytest.mark.unit
    def test_has_equations_and_oracle(self, dataset):
        """Dataset exposes both equations and oracle."""
        assert len(dataset.equations) == 4694
        assert dataset.oracle.num_equations == 4694

    @pytest.mark.unit
    def test_implies(self, dataset):
        """Query whether one equation implies another."""
        # E2 (collapse) implies everything
        assert dataset.implies(2, 43) is True
        # E1 (tautology) implies only itself
        assert dataset.implies(1, 43) is False

    @pytest.mark.unit
    def test_classify_oracle(self, dataset):
        """Oracle-based classification works through dataset."""
        assert dataset.classify(1) == "tautology"
        assert dataset.classify(2) == "collapse"

    @pytest.mark.unit
    def test_get_equation(self, dataset):
        """Can retrieve equation objects."""
        eq = dataset.get_equation(43)
        assert isinstance(eq, Equation)
        assert eq.var_count == 2

    @pytest.mark.unit
    def test_summary(self, dataset):
        """Summary returns a dict with expected keys."""
        s = dataset.summary()
        assert "total_equations" in s
        assert s["total_equations"] == 4694
        assert "classification_counts" in s
        assert "collapse" in s["classification_counts"]
        assert "tautology" in s["classification_counts"]

    @pytest.mark.unit
    def test_equation_info(self, dataset):
        """equation_info() returns combined structural + oracle info."""
        info = dataset.equation_info(43)
        assert info["id"] == 43
        assert info["var_count"] == 2
        assert "structural_class" in info
        assert "oracle_class" in info
        assert "implies_count" in info
        assert "implied_by_count" in info


# ---------------------------------------------------------------------------
# Oracle classification completeness test
# ---------------------------------------------------------------------------


class TestOracleClassificationCompleteness:
    """
    Feature: Oracle classification covers all categories.
    """

    @pytest.fixture(scope="class")
    def oracle(self):
        import pathlib

        csv_path = pathlib.Path("research/data/etp/implications.csv")
        if not csv_path.exists():
            pytest.skip("implications.csv not available")
        return ImplicationOracle(str(csv_path))

    @pytest.mark.unit
    def test_all_categories_present(self, oracle):
        """All five classification categories appear in the dataset."""
        categories_seen = set()
        for eq_id in range(1, oracle.num_equations + 1):
            categories_seen.add(oracle.classify(eq_id))
        expected = {"collapse", "tautology", "weak", "mid", "strong"}
        assert categories_seen == expected, f"Missing: {expected - categories_seen}"

    @pytest.mark.unit
    def test_every_equation_classified(self, oracle):
        """Every equation gets a valid classification."""
        valid = {"collapse", "tautology", "weak", "mid", "strong"}
        for eq_id in range(1, oracle.num_equations + 1):
            cls = oracle.classify(eq_id)
            assert cls in valid, f"E{eq_id} got unexpected class: {cls}"
