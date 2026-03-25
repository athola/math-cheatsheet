"""Tests for the ETP equation parser and structural analyzer."""

import pytest

from etp_equations import ETPEquations, op, parse_equation, var


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
        """Scenario: ◇ operator is parsed correctly."""
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
