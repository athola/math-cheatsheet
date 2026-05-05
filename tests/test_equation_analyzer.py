"""Tests for the equation analyzer module.

Tests the v3 cheatsheet decision procedure implemented as computable functions:
- Equation parsing
- Variable analysis
- Substitution detection
- Counterexample testing
- Structural analysis
"""

import pytest

from src.equation_analyzer import (
    ALL_SIZE_2_MAGMAS,
    CANONICAL_MAGMAS,
    ImplicationVerdict,
    NodeType,
    Term,
    _check_simple_substitutions,
    analyze_implication,
    parse_equation,
    var,
)


class TestTermParsing:
    """
    Feature: Parse equation strings into structured Term/Equation objects.

    As a competition contestant
    I want to parse equation strings from the ETP format
    So that I can analyze their structure programmatically.
    """

    @pytest.mark.unit
    def test_parse_simple_variable(self):
        """
        Scenario: Parse a trivial equation with just variables
        Given the equation string 'x = x'
        When I parse it
        Then both sides should be variable terms named 'x'
        """
        eq = parse_equation("x = x")
        assert eq.lhs.node_type == NodeType.VAR
        assert eq.lhs.name == "x"
        assert eq.rhs.node_type == NodeType.VAR
        assert eq.rhs.name == "x"

    @pytest.mark.unit
    def test_parse_collapse_law(self):
        """
        Scenario: Parse the collapse law x = y
        Given the equation string 'x = y'
        When I parse it
        Then LHS is variable x and RHS is variable y
        """
        eq = parse_equation("x = y")
        assert eq.lhs.name == "x"
        assert eq.rhs.name == "y"

    @pytest.mark.unit
    def test_parse_commutativity(self):
        """
        Scenario: Parse the commutative law x*y = y*x
        Given the equation 'x * y = y * x'
        When I parse it
        Then both sides should be OP nodes with swapped children
        """
        eq = parse_equation("x * y = y * x")
        assert eq.lhs.node_type == NodeType.OP
        assert eq.lhs.left.name == "x"
        assert eq.lhs.right.name == "y"
        assert eq.rhs.left.name == "y"
        assert eq.rhs.right.name == "x"

    @pytest.mark.unit
    def test_parse_associativity(self):
        """
        Scenario: Parse the associative law with nested parentheses
        Given 'x * (y * z) = (x * y) * z'
        When I parse it
        Then the nesting structure should be correct
        """
        eq = parse_equation("x * (y * z) = (x * y) * z")
        # LHS: x * (y * z)
        assert eq.lhs.left.name == "x"
        assert eq.lhs.right.node_type == NodeType.OP
        assert eq.lhs.right.left.name == "y"
        assert eq.lhs.right.right.name == "z"
        # RHS: (x * y) * z
        assert eq.rhs.left.node_type == NodeType.OP
        assert eq.rhs.right.name == "z"

    @pytest.mark.unit
    def test_parse_diamond_symbol(self):
        """
        Scenario: Parse equations using the ◇ symbol from ETP format
        Given an equation with ◇ instead of *
        When I parse it
        Then it should parse identically to the * version
        """
        eq = parse_equation("x ◇ y = y ◇ x")
        assert eq.lhs.node_type == NodeType.OP
        assert eq.variables() == {"x", "y"}


class TestParserErrorPaths:
    """
    Feature: Parser produces clear errors on malformed input.

    As a developer
    I want parse errors to be caught and reported
    So that malformed competition data doesn't cause silent failures.
    """

    @pytest.mark.unit
    def test_no_equals_sign(self):
        """Equation string without '=' should raise ValueError."""
        with pytest.raises(ValueError, match="No '=' found"):
            parse_equation("x * y")

    @pytest.mark.unit
    def test_empty_string(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError):
            parse_equation("")

    @pytest.mark.unit
    def test_unmatched_parenthesis(self):
        """Unmatched parenthesis should raise ValueError."""
        with pytest.raises(ValueError, match="Expected '\\)'"):
            parse_equation("(x * y = z")

    @pytest.mark.unit
    def test_unexpected_token(self):
        """Unexpected token in expression should raise ValueError."""
        with pytest.raises(ValueError, match="Unexpected"):
            parse_equation("* = x")


class TestTermProperties:
    """
    Feature: Compute structural properties of terms and equations.

    As an implication analyzer
    I want to compute depth, size, and variable sets
    So that I can apply structural heuristics.
    """

    @pytest.mark.unit
    def test_variable_extraction(self):
        """
        Scenario: Extract variables from an equation
        Given the associativity equation with variables x, y, z
        When I extract variables
        Then I get exactly {x, y, z}
        """
        eq = parse_equation("x * (y * z) = (x * y) * z")
        assert eq.variables() == {"x", "y", "z"}

    @pytest.mark.unit
    def test_depth_calculation(self):
        """
        Scenario: Calculate nesting depth
        Given equations of different depths
        When I compute max_depth
        Then deeper nesting gives higher values
        """
        eq1 = parse_equation("x = y")
        assert eq1.max_depth() == 0

        eq2 = parse_equation("x * y = y * x")
        assert eq2.max_depth() == 1

        eq3 = parse_equation("x * (y * z) = (x * y) * z")
        assert eq3.max_depth() == 2

    @pytest.mark.unit
    def test_operation_count(self):
        """
        Scenario: Count * operations
        Given equations with different numbers of operations
        When I compute total_ops
        Then I get the correct count
        """
        eq1 = parse_equation("x = x")
        assert eq1.total_ops() == 0

        eq2 = parse_equation("x * y = y * x")
        assert eq2.total_ops() == 2

        eq3 = parse_equation("x * (y * z) = (x * y) * z")
        assert eq3.total_ops() == 4

    @pytest.mark.unit
    def test_term_substitution(self):
        """
        Scenario: Substitute a variable with a term
        Given a term x * (y * z)
        When I substitute y := x
        Then I get x * (x * z)
        """
        eq = parse_equation("x * (y * z) = (x * y) * z")
        mapping = {"y": Term(NodeType.VAR, name="x")}
        result = eq.substitute(mapping)
        assert str(result) == str(parse_equation("x * (x * z) = (x * x) * z"))


class TestMagmaEvaluation:
    """
    Feature: Evaluate equations in specific finite magmas.

    As a counterexample searcher
    I want to check if equations hold in specific magmas
    So that I can find counterexamples to false implications.
    """

    @pytest.mark.unit
    def test_left_projection_satisfies_associativity(self):
        """
        Scenario: Left projection is associative
        Given the left projection magma x*y = x
        When I check associativity x*(y*z) = (x*y)*z
        Then it should be satisfied (both sides = x)
        """
        lp = [[0, 0], [1, 1]]
        eq = parse_equation("x * (y * z) = (x * y) * z")
        assert eq.holds_in(lp, 2)

    @pytest.mark.unit
    def test_left_projection_violates_commutativity(self):
        """
        Scenario: Left projection is NOT commutative
        Given the left projection magma
        When I check commutativity x*y = y*x
        Then it should fail (0*1=0 but 1*0=1)
        """
        lp = [[0, 0], [1, 1]]
        eq = parse_equation("x * y = y * x")
        assert not eq.holds_in(lp, 2)

    @pytest.mark.unit
    def test_constant_zero_satisfies_commutativity(self):
        """
        Scenario: Constant-zero magma is commutative
        Given the constant-0 magma where x*y = 0
        When I check commutativity
        Then it holds (0 = 0 always)
        """
        c0 = [[0, 0], [0, 0]]
        eq = parse_equation("x * y = y * x")
        assert eq.holds_in(c0, 2)

    @pytest.mark.unit
    def test_constant_zero_violates_idempotency(self):
        """
        Scenario: Constant-zero is NOT idempotent
        Given the constant-0 magma
        When I check x * x = x
        Then it fails (1*1=0 != 1)
        """
        c0 = [[0, 0], [0, 0]]
        eq = parse_equation("x * x = x")
        assert not eq.holds_in(c0, 2)

    @pytest.mark.unit
    def test_cm_magma_is_commutative_not_associative(self):
        """
        Scenario: CM magma validates the independence of commutativity/associativity
        Given the CM magma (0*0=1, 0*1=1, 1*0=1, 1*1=0)
        When I check commutativity and associativity
        Then commutativity holds but associativity fails
        """
        cm = [[1, 1], [1, 0]]
        comm = parse_equation("x * y = y * x")
        assoc = parse_equation("x * (y * z) = (x * y) * z")
        assert comm.holds_in(cm, 2)
        assert not assoc.holds_in(cm, 2)

    @pytest.mark.unit
    def test_z3_addition_properties(self):
        """
        Scenario: Z/3Z addition is commutative+associative but not idempotent
        Given Z/3Z addition on {0,1,2}
        When I check various properties
        Then comm and assoc hold, idempotency fails
        """
        z3 = [[0, 1, 2], [1, 2, 0], [2, 0, 1]]
        comm = parse_equation("x * y = y * x")
        assoc = parse_equation("x * (y * z) = (x * y) * z")
        idem = parse_equation("x * x = x")
        assert comm.holds_in(z3, 3)
        assert assoc.holds_in(z3, 3)
        assert not idem.holds_in(z3, 3)


class TestImplicationAnalysis:
    """
    Feature: Analyze equational implications using the v3 decision procedure.

    As a competition contestant
    I want to programmatically determine if H implies T
    So that I can validate cheatsheet heuristics and evaluate accuracy.
    """

    @pytest.mark.unit
    def test_identical_equations_true(self):
        """
        Scenario: Same equation implies itself (Phase 1a)
        Given H and T are the same equation
        When I analyze the implication
        Then the verdict is TRUE
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * (y * z) = (x * y) * z")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert "Phase 1" in result.phase

    @pytest.mark.unit
    def test_tautology_target_true(self):
        """
        Scenario: Any equation implies a tautology (Phase 1b)
        Given any H and T is x = x
        When I analyze the implication
        Then the verdict is TRUE
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("x = x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE

    @pytest.mark.unit
    def test_collapse_hypothesis_true(self):
        """
        Scenario: Collapse law implies everything (Phase 1c)
        Given H is x = y (forces |M|=1)
        When I analyze any implication
        Then the verdict is TRUE
        """
        h = parse_equation("x = y")
        t = parse_equation("x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE

    @pytest.mark.unit
    def test_new_variable_false(self):
        """
        Scenario: New variable in target means FALSE (Phase 2)
        Given H has {x} and T has {x, y}
        When I analyze the implication
        Then the verdict is FALSE (new variable y unconstrained)
        """
        h = parse_equation("x * (x * x) = x")
        t = parse_equation("x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE
        assert "Phase 2" in result.phase

    @pytest.mark.unit
    def test_substitution_detection(self):
        """
        Scenario: T obtainable by substitution in H (Phase 3)
        Given H: x*(y*z) = (x*y)*z and T: x*(x*z) = (x*x)*z
        When I analyze (T is H with y:=x)
        Then the verdict is TRUE
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * (x * z) = (x * x) * z")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert "Phase 3" in result.phase

    @pytest.mark.unit
    def test_associativity_does_not_imply_commutativity(self):
        """
        Scenario: Associativity does NOT imply commutativity (Phase 4)
        Given H=associativity, T=commutativity
        When I analyze the implication
        Then the verdict is FALSE with a counterexample
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE
        assert result.counterexample is not None

    @pytest.mark.unit
    def test_commutativity_does_not_imply_associativity(self):
        """
        Scenario: Commutativity does NOT imply associativity (Phase 4)
        Given H=commutativity, T=associativity
        When I analyze the implication
        Then the verdict is FALSE with a counterexample
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * (y * z) = (x * y) * z")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_left_absorption_implies_idempotency(self):
        """
        Scenario: x = x*y implies x*x = x
        Given H: x = x*y (left absorption forces LP)
        When I analyze against T: x*x = x
        Then the verdict should be TRUE (LP is idempotent)
        """
        h = parse_equation("x = x * y")
        t = parse_equation("x * x = x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE, (
            f"Expected TRUE for left-absorption => idempotency, "
            f"got {result.verdict} at {result.phase}: {result.reason}"
        )

    @pytest.mark.unit
    def test_collapse_target_false(self):
        """
        Scenario: Non-collapse H cannot imply collapse T (Phase 1d)
        Given H: x*x = x and T: x = y
        When I analyze the implication
        Then the verdict is FALSE
        """
        h = parse_equation("x * x = x")
        t = parse_equation("x = y")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE


class TestCanonicalMagmas:
    """
    Feature: Canonical counterexample magmas are correctly defined.

    As a counterexample tester
    I want the 7 canonical magmas to have correct properties
    So that counterexample testing produces reliable results.
    """

    @pytest.mark.unit
    def test_canonical_magma_count(self):
        assert len(CANONICAL_MAGMAS) == 7

    @pytest.mark.unit
    def test_all_size_2_magmas_count(self):
        assert len(ALL_SIZE_2_MAGMAS) == 16

    @pytest.mark.unit
    def test_lp_properties(self):
        """LP should be associative and idempotent but not commutative."""
        lp = CANONICAL_MAGMAS[0]
        assert lp.satisfies(parse_equation("x * (y * z) = (x * y) * z"))
        assert lp.satisfies(parse_equation("x * x = x"))
        assert not lp.satisfies(parse_equation("x * y = y * x"))

    @pytest.mark.unit
    def test_rp_properties(self):
        """RP should be associative and idempotent but not commutative."""
        rp = CANONICAL_MAGMAS[1]
        assert rp.satisfies(parse_equation("x * (y * z) = (x * y) * z"))
        assert rp.satisfies(parse_equation("x * x = x"))
        assert not rp.satisfies(parse_equation("x * y = y * x"))

    @pytest.mark.unit
    def test_c0_properties(self):
        """C0 should be associative and commutative but not idempotent."""
        c0 = CANONICAL_MAGMAS[2]
        assert c0.satisfies(parse_equation("x * (y * z) = (x * y) * z"))
        assert c0.satisfies(parse_equation("x * y = y * x"))
        assert not c0.satisfies(parse_equation("x * x = x"))

    @pytest.mark.unit
    def test_xr_properties(self):
        """XOR should be commutative, associative, not idempotent."""
        xr = CANONICAL_MAGMAS[3]
        assert xr.satisfies(parse_equation("x * y = y * x"))
        assert xr.satisfies(parse_equation("x * (y * z) = (x * y) * z"))
        assert not xr.satisfies(parse_equation("x * x = x"))

    @pytest.mark.unit
    def test_cm_properties(self):
        """CM should be commutative but NOT associative."""
        cm = CANONICAL_MAGMAS[4]
        assert cm.satisfies(parse_equation("x * y = y * x"))
        assert not cm.satisfies(parse_equation("x * (y * z) = (x * y) * z"))


class TestPhase5DeterminedOperations:
    """Regression #29: exercise all six determined-operation patterns.

    Phase 5 in ``equation_analyzer`` detects left/right absorption and
    constant law in both forward and reversed forms, then derives a known
    magma table to test implications. The original suite only covered the
    forward-left-absorption path; this block pins all six.
    """

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "hypothesis,label",
        [
            ("x = x * y", "left-abs-forward"),
            ("x * y = x", "left-abs-reversed"),
            ("x = y * x", "right-abs-forward"),
            ("y * x = x", "right-abs-reversed"),
        ],
    )
    def test_absorption_implies_idempotency(self, hypothesis: str, label: str):
        """Left/right absorption forces a projection magma, which is idempotent."""
        h = parse_equation(hypothesis)
        t = parse_equation("x * x = x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE, (
            f"[{label}] expected TRUE for {hypothesis} => x*x=x, got"
            f" {result.verdict} via {result.phase}"
        )
        assert "Phase 5" in result.phase, f"[{label}] expected Phase 5, got {result.phase}"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "hypothesis,label",
        [
            ("x * y = z * w", "constant-forward"),
            ("z * w = x * y", "constant-reversed"),
        ],
    )
    def test_constant_implies_commutativity(self, hypothesis: str, label: str):
        """Constant law ``x*y=c`` forces all products equal, hence commutativity."""
        h = parse_equation(hypothesis)
        t = parse_equation("x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE, (
            f"[{label}] expected TRUE for {hypothesis} => comm, got"
            f" {result.verdict} via {result.phase}"
        )
        assert "Phase 5" in result.phase, f"[{label}] expected Phase 5, got {result.phase}"


class TestPhase4bExhaustiveSearch:
    """Regression for #38 — assert verdict AND phase origin."""

    @pytest.mark.unit
    def test_phase_4b_finds_exhaustive_counterexample(self):
        """An implication caught by exhaustive 2-element search, not canonical magmas.

        The previous test in ``test_coverage_gaps.py`` only asserted the verdict
        was FALSE, which could be satisfied by any earlier phase (#38). This
        version pins the phase to "Phase 4b" so we verify the exhaustive search
        actually fires.
        """
        h = parse_equation("x * (x * y) = x * y")
        t = parse_equation("(x * y) * y = x * y")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE
        assert result.phase == "Phase 4b", (
            f"Expected Phase 4b to discharge this FALSE; got {result.phase}."
            " Either canonical magmas now cover this case (update the test)"
            " or Phase 4b regressed."
        )


class TestPhase7StructuralHeuristic:
    """Regression for #37 — assert phase unconditionally."""

    @pytest.mark.unit
    def test_extended_collapse_var_not_in_other_side(self):
        """H: x*y = z (z fresh) is an extended collapse law — forces |M|=1.

        Proof: for any p,q in M, set x=p, y=p, z=q in H → p*p = q.
        Set z=p → p*p = p. So q = p*p = p for all p,q. Therefore |M|=1,
        and every equation holds in the singleton magma.

        Previously this was incorrectly treated as a Phase 7 case because
        the old _is_collapse only detected "x = y" (two bare variables).
        """
        h = parse_equation("x * y = z")
        t = parse_equation("x * (y * (y * x)) = (x * y) * ((y * x) * x)")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 1c", (
            f"H='x*y=z' is an extended collapse law; expected Phase 1c TRUE, got {result.phase}."
        )

    @pytest.mark.unit
    def test_depth_heuristic_triggers_phase_7(self):
        """A pair where the depth gap fires after exhaustive 2-element search finds nothing.

        H: (x*y)*x = x*y  (depth 2, not collapse, no determined op)
        T: x*(x*(y*(x*y))) = (x*y)*(x*y)  (depth 4)
        Phase 7 condition: depth(T)=4 > depth(H)+1=3 → FALSE.

        No canonical or 2-element counterexample exists for this pair, so
        only the depth heuristic can discharge it.
        """
        h = parse_equation("(x * y) * x = x * y")
        t = parse_equation("x * (x * (y * (x * y))) = (x * y) * (x * y)")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE
        assert result.phase == "Phase 7", (
            f"Expected Phase 7 depth heuristic to fire; got {result.phase}."
            " Check that neither canonical nor exhaustive search decides this"
            " pair before Phase 7."
        )


class TestCoverageGaps:
    """Targeted tests for previously-uncovered lines in equation_analyzer.py.

    Each test is named after the exact line it exercises so regressions are
    immediately traceable.
    """

    @pytest.mark.unit
    def test_op_node_with_missing_children_rejected_at_construction(self):
        """NEW-I4 (#58): construction-time validation in Term.__post_init__
        catches malformed OP nodes at the construction site rather than at
        every traversal that runs _lr().
        """
        with pytest.raises(ValueError, match="OP node must have both left and right"):
            Term(NodeType.OP)
        with pytest.raises(ValueError, match="OP node must have both left and right"):
            Term(NodeType.OP, left=var("x"))
        with pytest.raises(ValueError, match="OP node must have both left and right"):
            Term(NodeType.OP, right=var("x"))

    @pytest.mark.unit
    def test_var_node_invariants_enforced_at_construction(self):
        """NEW-I4 (#58): VAR nodes must be leaves with non-empty names."""
        with pytest.raises(ValueError, match="VAR node must have a non-empty name"):
            Term(NodeType.VAR)
        with pytest.raises(ValueError, match="VAR node must not have children"):
            Term(NodeType.VAR, name="x", left=var("y"))

    @pytest.mark.unit
    def test_parse_expr_raises_on_empty_rhs(self):
        """Line 124: _parse_expr raises 'Unexpected end of expression'.

        Input 'x = ' has an empty RHS token list; _parse_expr is called
        with pos=0 >= len(tokens)=0 and raises immediately.
        """
        with pytest.raises(ValueError, match="Unexpected end of expression"):
            parse_equation("x = ")

    @pytest.mark.unit
    def test_parse_primary_raises_after_trailing_operator(self):
        """Line 135: _parse_primary raises when tokens exhausted after '*'.

        Input 'x = x *' has RHS tokens ['x', '*']; after parsing 'x',
        the loop sees '*' and calls _parse_primary at pos=2 >= len=2.
        """
        with pytest.raises(ValueError, match="Unexpected end of expression"):
            parse_equation("x = x *")

    @pytest.mark.unit
    def test_tautology_hypothesis_implies_nothing(self):
        """Line 266: Phase 1e — tautology H implies only tautology T.

        H: x*y = x*y is universally true and constrains the operation
        not at all.  Any non-tautological T can be falsified, so the
        verdict must be FALSE (Phase 1e).
        """
        h = parse_equation("x * y = x * y")
        t = parse_equation("x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE
        assert result.phase == "Phase 1e", f"Tautology H should fire Phase 1e; got {result.phase}."

    @pytest.mark.unit
    def test_phase8_inconclusive_fallthrough(self):
        """Line 327: Phase 8 UNKNOWN fallthrough for an undecided pair.

        H: x*(y*z) = (x*z)*y  is non-collapse, non-tautology.
        T: x*(y*z) = (x*y)*z  is associativity.
        No 2-element counterexample exists for H (every 2-element table
        satisfies H vacuously for this pairing), and Phase 3–6 find no
        positive derivation, so the decision procedure reaches Phase 8.
        """
        h = parse_equation("x * (y * z) = (x * z) * y")
        t = parse_equation("x * (y * z) = (x * y) * z")
        result = analyze_implication(h, t)
        assert result.phase == "Phase 8", (
            f"Expected Phase 8 inconclusive fallthrough; got {result.phase}."
        )

    @pytest.mark.unit
    def test_substitution_single_var_hypothesis_returns_none(self):
        """Line 358: _check_simple_substitutions returns None for 1-variable H.

        A single-variable hypothesis has no pair of variables to merge,
        so the function exits immediately with None.
        """
        h = parse_equation("x * x = x")
        t = parse_equation("x * x = x")
        result = _check_simple_substitutions(h, t)
        assert result is None, (
            f"Single-var H should return None from substitution check; got {result}."
        )

    @pytest.mark.unit
    def test_two_step_substitution_chain(self):
        """Line 382: Phase 3 two-step chaining derives T from H.

        H: x*(y*z) = (x*y)*z (associativity, 3 vars).
        T: x*(x*x) = (x*x)*x requires y:=x then z:=x — no single-step
        substitution produces T, so the second-step loop at line 382 fires.
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * (x * x) = (x * x) * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 3", (
            f"Two-step y:=x,z:=x chain should fire Phase 3; got {result.phase}."
        )
        assert "then" in result.reason, (
            f"Reason should mention two-step chain; got: {result.reason!r}."
        )


class TestFrozenAnalysisRecords:
    """NEW-I3 (#58): AnalysisResult and CounterexampleMagma are frozen so
    a returned verdict / canonical magma cannot be mutated by downstream
    consumers (error analysers, reporters, caches).
    """

    @pytest.mark.unit
    def test_analysis_result_is_frozen(self):
        from src.equation_analyzer import AnalysisResult

        r = AnalysisResult(ImplicationVerdict.TRUE, "Phase 1a", "x=x")
        with pytest.raises(Exception):  # FrozenInstanceError
            r.phase = "Phase 99"  # type: ignore[misc]

    @pytest.mark.unit
    def test_counterexample_magma_is_frozen(self):
        m = CANONICAL_MAGMAS[0]
        with pytest.raises(Exception):  # FrozenInstanceError
            m.name = "tampered"  # type: ignore[misc]

    @pytest.mark.unit
    def test_canonical_table_and_properties_are_tuples(self):
        m = CANONICAL_MAGMAS[0]
        assert isinstance(m.table, tuple)
        assert all(isinstance(row, tuple) for row in m.table)
        assert isinstance(m.properties, tuple)

    @pytest.mark.unit
    def test_size_2_magma_table_is_tuple_of_tuples(self):
        # ALL_SIZE_2_MAGMAS is the cache-key surface for _size_2_satisfactions;
        # the table must be hashable for the lru_cache to function.
        m = ALL_SIZE_2_MAGMAS[0]
        assert isinstance(m.table, tuple)
        assert all(isinstance(row, tuple) for row in m.table)
        assert hash(m) == hash(ALL_SIZE_2_MAGMAS[0])

    @pytest.mark.unit
    def test_counterexample_magma_accepts_list_input_for_back_compat(self):
        # Existing callers wrote literal list-of-list tables; the
        # __post_init__ normaliser must convert without error.
        from src.equation_analyzer import CounterexampleMagma

        m = CounterexampleMagma("L", 2, [[0, 1], [1, 0]], ["test"])
        assert m.table == ((0, 1), (1, 0))
        assert m.properties == ("test",)
