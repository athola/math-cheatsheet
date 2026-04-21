"""Tests for src/equation_parser_utils.py — shared equation tokenizer.

Feature: Shared equation tokenization
    As equation parsers in equation_analyzer and etp_equations
    I want a single tokenize_equation function
    So that operator normalization bugs are fixed once, not twice
"""

from __future__ import annotations

import pytest


class TestTokenizeEquation:
    """Feature: tokenize_equation normalizes operators and splits equation strings."""

    @pytest.mark.unit
    def test_simple_commutative(self):
        """
        Scenario: Tokenize 'x * y = y * x'
        Given the string 'x * y = y * x'
        When tokenize_equation is called
        Then tokens are ['x', '*', 'y', '=', 'y', '*', 'x']
        """
        from equation_parser_utils import tokenize_equation

        assert tokenize_equation("x * y = y * x") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_diamond_operator_normalized(self):
        """
        Scenario: ◇ is normalized to *
        Given 'x ◇ y = y ◇ x'
        When tokenize_equation is called
        Then ◇ becomes * in the token list
        """
        from equation_parser_utils import tokenize_equation

        assert tokenize_equation("x ◇ y = y ◇ x") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_small_diamond_normalized(self):
        """
        Scenario: ⋄ (small diamond) is normalized to *
        Given 'x ⋄ y = y ⋄ x'
        When tokenize_equation is called
        Then ⋄ becomes *
        """
        from equation_parser_utils import tokenize_equation

        assert tokenize_equation("x ⋄ y = y ⋄ x") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_parentheses_preserved(self):
        """
        Scenario: Parentheses become tokens
        Given 'x * (y * z) = (x * y) * z'
        When tokenize_equation is called
        Then parens appear in the token list
        """
        from equation_parser_utils import tokenize_equation

        tokens = tokenize_equation("x * (y * z) = (x * y) * z")
        assert "(" in tokens
        assert ")" in tokens

    @pytest.mark.unit
    def test_whitespace_ignored(self):
        """
        Scenario: Extra whitespace is stripped
        Given '  x  *  y  =  y  *  x  '
        When tokenize_equation is called
        Then the same tokens as 'x * y = y * x' are returned
        """
        from equation_parser_utils import tokenize_equation

        assert tokenize_equation("  x  *  y  =  y  *  x  ") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_multi_letter_variable(self):
        """
        Scenario: Multi-letter variable names are captured whole
        Given 'xy * z = z * xy'
        When tokenize_equation is called
        Then 'xy' appears as a single token
        """
        from equation_parser_utils import tokenize_equation

        tokens = tokenize_equation("xy * z = z * xy")
        assert "xy" in tokens

    @pytest.mark.unit
    def test_tautology_x_equals_x(self):
        """
        Scenario: Tautology 'x = x' tokenizes correctly
        Given 'x = x'
        When tokenize_equation is called
        Then tokens are ['x', '=', 'x']
        """
        from equation_parser_utils import tokenize_equation

        assert tokenize_equation("x = x") == ["x", "=", "x"]
