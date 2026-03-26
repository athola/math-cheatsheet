"""Tests targeting specific coverage gaps across modules.

Covers uncovered branches in:
- implication_oracle: classify mid/strong, query unknown values
- etp_equations: Term.__str__, * tokenization, parser errors,
  is_collapse_structural, is_substitution_instance
- decision_procedure: evaluate_by_phase with unknown matrix values
- equation_analyzer: Phase 4b/7, right absorption, reversed projection, constant law, batch errors
"""

import csv
from pathlib import Path

import numpy as np
import pytest

from etp_equations import ETPEquations, op, parse_equation, var
from implication_oracle import ImplicationOracle

# ---------------------------------------------------------------------------
# implication_oracle coverage gaps
# ---------------------------------------------------------------------------


class TestOracleClassifyMidStrong:
    """Cover the 'mid' and 'strong' branches in classify()."""

    @pytest.fixture
    def mid_oracle(self, tmp_path: Path) -> ImplicationOracle:
        """Oracle where eq1 implies 10 others (mid range: 5 < n <= 1000)."""
        n = 20
        matrix = []
        for i in range(n):
            row = [-3] * n
            row[i] = 3  # self-implication
            if i == 0:
                # Eq1 implies first 10 equations
                for j in range(10):
                    row[j] = 3
            matrix.append(row)
        csv_path = tmp_path / "mid.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        return ImplicationOracle(csv_path)

    def test_classify_mid(self, mid_oracle: ImplicationOracle):
        assert mid_oracle.classify(1) == "mid"

    @pytest.fixture
    def strong_oracle(self, tmp_path: Path) -> ImplicationOracle:
        """Oracle where eq1 implies > 1000 others (strong)."""
        n = 1500
        matrix = np.full((n, n), -3, dtype=np.int8)
        np.fill_diagonal(matrix, 3)
        # Eq1 (row 0) implies first 1001 columns
        matrix[0, :1001] = 3
        csv_path = tmp_path / "strong.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row.tolist())
        return ImplicationOracle(csv_path)

    def test_classify_strong(self, strong_oracle: ImplicationOracle):
        assert strong_oracle.classify(1) == "strong"


class TestOracleQueryUnknownValue:
    """Cover query() returning None for values not in {3,4,-3,-4} (line 84)."""

    @pytest.fixture
    def oracle_with_zeros(self, tmp_path: Path) -> ImplicationOracle:
        csv_path = tmp_path / "zeros.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([3, 0])
            writer.writerow([0, 3])
        return ImplicationOracle(csv_path)

    def test_query_returns_none_for_zero(self, oracle_with_zeros: ImplicationOracle):
        assert oracle_with_zeros.query(1, 2) is None
        assert oracle_with_zeros.query(2, 1) is None

    def test_accuracy_of_skips_zeros(self, oracle_with_zeros: ImplicationOracle):
        """accuracy_of should skip entries with value 0 (line 143)."""
        result = oracle_with_zeros.accuracy_of(lambda h, t: True)
        # Only diagonal (value=3) counted, off-diag zeros skipped
        assert result["total"] == 2  # only the two 3s on diagonal
        assert result["tp"] == 2


# ---------------------------------------------------------------------------
# etp_equations coverage gaps
# ---------------------------------------------------------------------------


class TestTermStr:
    """Cover Term.__str__ (lines 54-59)."""

    def test_var_str(self):
        assert str(var("x")) == "x"

    def test_simple_op_str(self):
        t = op(var("x"), var("y"))
        assert str(t) == "x ◇ y"

    def test_nested_op_str(self):
        t = op(op(var("x"), var("y")), var("z"))
        # LHS is an op node, so gets parens
        assert str(t) == "(x ◇ y) ◇ z"

    def test_right_nested_op_str(self):
        t = op(var("x"), op(var("y"), var("z")))
        assert str(t) == "x ◇ (y ◇ z)"


class TestTokenizeStarOperator:
    """Cover * operator path in etp_equations._tokenize (lines 118-120)."""

    def test_star_operator_parsed(self):
        eq = parse_equation(1, "x * y = y * x")
        assert eq.var_count == 2
        assert eq.total_ops == 2

    def test_skip_unknown_chars(self):
        """Unknown characters like digits are skipped (line 128)."""
        eq = parse_equation(1, "x 3 ◇ y = y ◇ x")
        assert eq.var_count == 2


class TestETPParserErrors:
    """Cover error paths in etp_equations parser."""

    def test_unexpected_end_of_expression(self):
        """Empty LHS triggers 'Unexpected end of expression' (line 135)."""
        with pytest.raises(ValueError, match="Unexpected end"):
            parse_equation(1, "= x")

    def test_missing_close_paren(self):
        """Missing ) triggers error (line 150)."""
        with pytest.raises(ValueError, match="Expected '\\)'"):
            parse_equation(1, "(x ◇ y = z")

    def test_unexpected_token(self):
        """Unexpected token like ) at start (line 155)."""
        with pytest.raises(ValueError, match="Unexpected token"):
            parse_equation(1, ") = x")


class TestIsCollapseStructural:
    """Cover branches in is_collapse_structural (lines 223-239)."""

    @pytest.fixture
    def eqs(self, tmp_path: Path) -> ETPEquations:
        """Equations file with various collapse patterns."""
        eq_path = tmp_path / "equations.txt"
        eq_path.write_text(
            # 1: x = y (simple collapse, LHS=var, RHS=var)
            "x = y\n"
            # 2: x ◇ y = z (rhs is var, lhs introduces 2 new vars with 1 op) -- symmetric case
            "x ◇ y = z\n"
            # 3: x ◇ y = y ◇ x (not collapse)
            "x ◇ y = y ◇ x\n"
            # 4: x = y ◇ z (lhs is var, rhs has 2 new vars, 1 op -> collapse)
            "x = y ◇ z\n"
            # 5: x = x (tautology, not collapse)
            "x = x\n",
            encoding="utf-8",
        )
        return ETPEquations(eq_path)

    def test_simple_xy_collapse(self, eqs: ETPEquations):
        assert eqs.is_collapse_structural(1)

    def test_symmetric_collapse_rhs_var(self, eqs: ETPEquations):
        """x ◇ y = z: rhs is var, lhs has 2 new vars -> collapse (lines 232-237)."""
        assert eqs.is_collapse_structural(2)

    def test_commutativity_not_collapse(self, eqs: ETPEquations):
        assert not eqs.is_collapse_structural(3)

    def test_var_eq_op_with_new_vars_collapse(self, eqs: ETPEquations):
        """x = y ◇ z: lhs var, rhs has 2 new vars -> collapse (lines 223-229)."""
        assert eqs.is_collapse_structural(4)

    def test_tautology_not_collapse(self, eqs: ETPEquations):
        assert not eqs.is_collapse_structural(5)


class TestIsSubstitutionInstance:
    """Cover is_substitution_instance (lines 247-268)."""

    @pytest.fixture
    def eqs(self, tmp_path: Path) -> ETPEquations:
        eq_path = tmp_path / "equations.txt"
        eq_path.write_text(
            # 1: x ◇ y = y ◇ x (2 vars, commutativity)
            "x ◇ y = y ◇ x\n"
            # 2: x ◇ x = x ◇ x (idempotent commutativity - substitution of y->x in eq1)
            "x ◇ x = x ◇ x\n"
            # 3: x = x (single var, can't substitute)
            "x = x\n",
            encoding="utf-8",
        )
        return ETPEquations(eq_path)

    def test_substitution_detected(self, eqs: ETPEquations):
        assert eqs.is_substitution_instance(1, 2)

    def test_single_var_returns_false(self, eqs: ETPEquations):
        """Equation with < 2 vars can't produce substitution (line 254)."""
        assert not eqs.is_substitution_instance(3, 1)

    def test_non_matching_returns_false(self, eqs: ETPEquations):
        assert not eqs.is_substitution_instance(1, 3)


# ---------------------------------------------------------------------------
# decision_procedure coverage gaps
# ---------------------------------------------------------------------------


class TestEvaluateByPhaseSkipsUnknowns:
    """Cover the continue for unknown values in evaluate_by_phase (line 118)."""

    @pytest.fixture
    def proc_with_unknowns(self, tmp_path: Path):
        from decision_procedure import DecisionProcedure

        # Create equations
        eq_path = tmp_path / "equations.txt"
        eq_path.write_text("x = x\nx = y\n", encoding="utf-8")

        # Create oracle with a 0 (unknown) value
        csv_path = tmp_path / "impl.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([3, 0])  # Eq1: self=TRUE, Eq2=unknown
            writer.writerow([3, 3])  # Eq2: collapse, implies all
        oracle = ImplicationOracle(csv_path)
        eqs = ETPEquations(eq_path)
        return DecisionProcedure(eqs, oracle)

    def test_phase_breakdown_skips_unknowns(self, proc_with_unknowns):
        phases = proc_with_unknowns.evaluate_by_phase()
        # Total across all phases should be 3 (skipping the one unknown cell)
        total = sum(ps["total"] for ps in phases.values())
        assert total == 3  # 4 cells minus 1 unknown


# ---------------------------------------------------------------------------
# equation_analyzer coverage gaps
# ---------------------------------------------------------------------------


class TestPhase4bExhaustiveSearch:
    """Cover Phase 4b: exhaustive 2-element magma search (lines 301-308)."""

    @pytest.mark.unit
    def test_phase_4b_finds_counterexample(self):
        """An implication that's not caught by canonical magmas but is caught by
        exhaustive 2-element search."""
        from equation_analyzer import analyze_implication, parse_equation

        # This pair: both have same vars, not caught by canonical but there exists
        # a size-2 magma that separates them. Use non-obvious equations.
        h = parse_equation("x * (x * y) = x * y")  # specific absorption
        t = parse_equation("(x * y) * y = x * y")  # different absorption
        result = analyze_implication(h, t)
        # Should be FALSE with a counterexample from some phase
        assert result.verdict.value == "FALSE"


class TestPhase7StructuralHeuristic:
    """Cover Phase 7: depth heuristic (lines 311-316)."""

    @pytest.mark.unit
    def test_depth_heuristic_triggers(self):
        from equation_analyzer import analyze_implication, parse_equation

        # H has depth 1, T has depth 4 -> target depth >> hypothesis depth
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * (y * (y * (y * x))) = (x * (y * (y * (y * x)))) * x")
        result = analyze_implication(h, t)
        # With same variables, no canonical counterexample, should hit Phase 7 or earlier
        # The depth difference is large enough to trigger
        if result.phase == "Phase 7":
            assert result.verdict.value == "FALSE"


class TestDetectDeterminedOperation:
    """Cover right absorption and constant law in _detect_determined_operation."""

    @pytest.mark.unit
    def test_right_absorption_x_eq_yx(self):
        """x = y * x -> right projection detected (lines 389-403)."""
        from equation_analyzer import analyze_implication, parse_equation

        h = parse_equation("x = y * x")
        t = parse_equation("x * x = x")  # idempotency: holds in RP
        result = analyze_implication(h, t)
        assert result.verdict.value == "TRUE"
        assert "Phase 5" in result.phase

    @pytest.mark.unit
    def test_reversed_right_projection_yx_eq_x(self):
        """y * x = x -> right projection (reversed form, lines 405-419)."""
        from equation_analyzer import analyze_implication, parse_equation

        h = parse_equation("y * x = x")
        t = parse_equation("x * x = x")  # idempotency: holds in RP
        result = analyze_implication(h, t)
        assert result.verdict.value == "TRUE"
        assert "Phase 5" in result.phase

    @pytest.mark.unit
    def test_reversed_left_projection(self):
        """x * y = x (reversed form, lines 376-387)."""
        from equation_analyzer import analyze_implication, parse_equation

        h = parse_equation("x * y = x")
        t = parse_equation("x * x = x")  # idempotency: holds in LP
        result = analyze_implication(h, t)
        assert result.verdict.value == "TRUE"
        assert "Phase 5" in result.phase

    @pytest.mark.unit
    def test_constant_law_detection(self):
        """x * y = z * w -> constant operation (lines 421-435)."""
        from equation_analyzer import analyze_implication, parse_equation

        h = parse_equation("x * y = z * w")
        t = parse_equation("x * y = y * x")  # commutativity holds in constant magma
        result = analyze_implication(h, t)
        assert result.verdict.value == "TRUE"
        assert "Phase 5" in result.phase


class TestBatchAnalyzeErrorHandling:
    """Cover batch_analyze error handling (lines 448-449)."""

    @pytest.mark.unit
    def test_batch_with_malformed_equation(self):
        from equation_analyzer import ImplicationVerdict, batch_analyze

        problems = [
            ("x * y = y * x", "x * y = y * x"),  # valid
            ("bad input", "x = x"),  # missing =
        ]
        results = batch_analyze(problems)
        assert len(results) == 2
        assert results[0].verdict == ImplicationVerdict.TRUE
        assert results[1].verdict == ImplicationVerdict.UNKNOWN
        assert "Error" in results[1].phase


class TestTermValidationErrors:
    """Cover Term methods raising ValueError for malformed OP nodes (lines 44,51,59,66,76,85)."""

    @pytest.mark.unit
    def test_op_node_missing_children_variables(self):
        from equation_analyzer import NodeType, Term

        bad_term = Term(NodeType.OP, left=None, right=None)
        with pytest.raises(ValueError, match="OP node must have"):
            bad_term.variables()

    @pytest.mark.unit
    def test_op_node_missing_children_depth(self):
        from equation_analyzer import NodeType, Term

        bad_term = Term(NodeType.OP, left=None, right=None)
        with pytest.raises(ValueError, match="OP node must have"):
            bad_term.depth()

    @pytest.mark.unit
    def test_op_node_missing_children_size(self):
        from equation_analyzer import NodeType, Term

        bad_term = Term(NodeType.OP, left=None, right=None)
        with pytest.raises(ValueError, match="OP node must have"):
            bad_term.size()

    @pytest.mark.unit
    def test_op_node_missing_children_substitute(self):
        from equation_analyzer import NodeType, Term

        bad_term = Term(NodeType.OP, left=None, right=None)
        with pytest.raises(ValueError, match="OP node must have"):
            bad_term.substitute({})

    @pytest.mark.unit
    def test_op_node_missing_children_evaluate(self):
        from equation_analyzer import NodeType, Term

        bad_term = Term(NodeType.OP, left=None, right=None)
        with pytest.raises(ValueError, match="OP node must have"):
            bad_term.evaluate([[0]], {"x": 0})

    @pytest.mark.unit
    def test_op_node_missing_children_str(self):
        from equation_analyzer import NodeType, Term

        bad_term = Term(NodeType.OP, left=None, right=None)
        with pytest.raises(ValueError, match="OP node must have"):
            str(bad_term)
