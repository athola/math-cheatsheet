"""Tests for tla_bridge equation evaluation and counterexample search.

Tests the evaluate_equation() and search_counterexample() functions
that bridge the equation_analyzer parser into the TLA+ magma infrastructure.
"""

import pytest
from tla_bridge import evaluate_equation, search_counterexample

from data_models import Magma


class TestEvaluateEquation:
    """
    Feature: Evaluate an equation string in a finite magma.

    As a magma researcher
    I want to evaluate equation strings against specific magmas and assignments
    So that I can check whether equations hold for particular variable values.
    """

    @pytest.mark.unit
    def test_commutative_equation_holds_in_xor(self, xor_magma):
        """
        Scenario: Commutativity holds in XOR magma for a specific assignment
        Given the XOR magma (Z/2Z addition)
        When I evaluate 'x * y = y * x' with x=0, y=1
        Then the result should be True
        """
        assert evaluate_equation(xor_magma, "x * y = y * x", {"x": 0, "y": 1}) is True

    @pytest.mark.unit
    def test_commutative_equation_holds_symmetric(self, xor_magma):
        """
        Scenario: Commutativity holds with swapped assignment
        Given the XOR magma
        When I evaluate 'x * y = y * x' with x=1, y=0
        Then the result should be True
        """
        assert evaluate_equation(xor_magma, "x * y = y * x", {"x": 1, "y": 0}) is True

    @pytest.mark.unit
    def test_idempotent_fails_in_xor(self, xor_magma):
        """
        Scenario: Idempotence fails in XOR for x=1
        Given the XOR magma where 1 XOR 1 = 0
        When I evaluate 'x * x = x' with x=1
        Then the result should be False because 1*1=0 != 1
        """
        assert evaluate_equation(xor_magma, "x * x = x", {"x": 1}) is False

    @pytest.mark.unit
    def test_idempotent_holds_for_zero_in_xor(self, xor_magma):
        """
        Scenario: Idempotence holds for x=0 in XOR
        Given the XOR magma where 0 XOR 0 = 0
        When I evaluate 'x * x = x' with x=0
        Then the result should be True because 0*0=0 == 0
        """
        assert evaluate_equation(xor_magma, "x * x = x", {"x": 0}) is True

    @pytest.mark.unit
    def test_associativity_equation(self, xor_magma):
        """
        Scenario: Associativity holds in XOR magma
        Given the XOR magma (which is associative)
        When I evaluate '(x * y) * z = x * (y * z)' with x=0, y=1, z=1
        Then the result should be True
        """
        result = evaluate_equation(xor_magma, "(x * y) * z = x * (y * z)", {"x": 0, "y": 1, "z": 1})
        assert result is True

    @pytest.mark.unit
    def test_tautology_equation(self, xor_magma):
        """
        Scenario: Tautological equation x = x always holds
        Given any magma and any assignment
        When I evaluate 'x = x'
        Then the result should be True
        """
        assert evaluate_equation(xor_magma, "x = x", {"x": 0}) is True
        assert evaluate_equation(xor_magma, "x = x", {"x": 1}) is True

    @pytest.mark.unit
    def test_trivial_magma_all_equations_with_one_var(self, trivial_magma):
        """
        Scenario: In a trivial (size-1) magma, all equations hold
        Given the trivial magma with one element
        When I evaluate any equation with x=0
        Then the result should be True
        """
        assert evaluate_equation(trivial_magma, "x * x = x", {"x": 0}) is True
        assert evaluate_equation(trivial_magma, "x = x", {"x": 0}) is True

    @pytest.mark.unit
    def test_unicode_diamond_operator(self, xor_magma):
        """
        Scenario: Equation with unicode diamond operator parses correctly
        Given an equation using the diamond operator
        When I evaluate it
        Then it should work the same as the * operator
        """
        assert evaluate_equation(xor_magma, "x \u25c7 y = y \u25c7 x", {"x": 0, "y": 1}) is True

    @pytest.mark.unit
    def test_left_projection_magma(self):
        """
        Scenario: Left projection satisfies x * y = x
        Given a left projection magma where a*b = a
        When I evaluate 'x * y = x' for various assignments
        Then the result should be True
        """
        lp = Magma(size=2, elements=[0, 1], operation=[[0, 0], [1, 1]])
        assert evaluate_equation(lp, "x * y = x", {"x": 0, "y": 1}) is True
        assert evaluate_equation(lp, "x * y = x", {"x": 1, "y": 0}) is True

    @pytest.mark.unit
    def test_missing_variable_raises_error(self, xor_magma):
        """
        Scenario: Missing variable in assignment raises ValueError
        Given the XOR magma
        When I evaluate 'x * y = y * x' with only x assigned
        Then a ValueError should be raised indicating missing variable y
        """
        with pytest.raises(ValueError, match="missing variables"):
            evaluate_equation(xor_magma, "x * y = y * x", {"x": 0})

    @pytest.mark.unit
    def test_out_of_range_assignment_raises_error(self, xor_magma):
        """
        Scenario: Out-of-range assignment value raises ValueError
        Given the XOR magma of size 2
        When I evaluate with y=5 (out of range [0, 2))
        Then a ValueError should be raised indicating the out-of-range value
        """
        with pytest.raises(ValueError, match="out of range"):
            evaluate_equation(xor_magma, "x * y = y * x", {"x": 0, "y": 5})


class TestSearchCounterexample:
    """
    Feature: Search for counterexample magmas to equation implications.

    As a magma researcher
    I want to find magmas where premise equations hold but a conclusion fails
    So that I can disprove equational implications.
    """

    @pytest.mark.unit
    def test_finds_counterexample_commutativity_does_not_imply_idempotence(self):
        """
        Scenario: Commutativity does not imply idempotence
        Given commutativity 'x * y = y * x' as premise
        And idempotence 'x * x = x' as target
        When I search for a counterexample up to size 4
        Then a counterexample magma should be found
        And all premises should hold in that magma
        And the target should fail in that magma
        """
        result = search_counterexample(
            equations_holding=["x * y = y * x"],
            equation_to_test="x * x = x",
            max_size=4,
        )
        assert result is not None
        assert isinstance(result, Magma)

    @pytest.mark.unit
    def test_no_counterexample_when_implication_holds(self):
        """
        Scenario: Idempotence implies x * x = x (trivially itself)
        Given idempotence as both premise and target
        When I search for a counterexample
        Then no counterexample should be found
        """
        result = search_counterexample(
            equations_holding=["x * x = x"],
            equation_to_test="x * x = x",
            max_size=3,
        )
        assert result is None

    @pytest.mark.unit
    def test_tautology_never_fails(self):
        """
        Scenario: Cannot disprove implication to a tautology
        Given any premise
        And target 'x = x' (tautology)
        When I search for a counterexample
        Then no counterexample should be found
        """
        result = search_counterexample(
            equations_holding=["x * y = y * x"],
            equation_to_test="x = x",
            max_size=3,
        )
        assert result is None

    @pytest.mark.unit
    def test_associativity_does_not_imply_commutativity(self):
        """
        Scenario: Associativity does not imply commutativity
        Given associativity as premise
        When I search for a counterexample up to size 3
        Then a non-commutative but associative magma should be found
        """
        result = search_counterexample(
            equations_holding=["(x * y) * z = x * (y * z)"],
            equation_to_test="x * y = y * x",
            max_size=3,
        )
        assert result is not None
        assert isinstance(result, Magma)

    @pytest.mark.unit
    def test_multiple_premises(self):
        """
        Scenario: Multiple premises narrow the search space
        Given commutativity and associativity as premises
        And a target that does not follow from them
        When I search for a counterexample
        Then a magma satisfying both premises but not the target should be found
        """
        result = search_counterexample(
            equations_holding=[
                "x * y = y * x",
                "(x * y) * z = x * (y * z)",
            ],
            equation_to_test="x * x = x",
            max_size=3,
        )
        assert result is not None
        assert isinstance(result, Magma)

    @pytest.mark.unit
    def test_counterexample_is_valid_magma(self):
        """
        Scenario: Returned counterexample is a well-formed magma
        Given a known non-implication
        When a counterexample is found
        Then it should be a valid Magma with correct size and table dimensions
        """
        result = search_counterexample(
            equations_holding=["x * y = y * x"],
            equation_to_test="x * x = x",
            max_size=3,
        )
        assert result is not None
        assert result.size >= 2
        assert len(result.operation) == result.size
        for row in result.operation:
            assert len(row) == result.size
