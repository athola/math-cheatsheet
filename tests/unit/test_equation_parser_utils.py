"""Tests for src/equation_parser_utils.py — shared equation tokenizer.

Feature: Shared equation tokenization
    As equation parsers in equation_analyzer and etp_equations
    I want a single tokenize_equation function
    So that operator normalization bugs are fixed once, not twice
"""

from __future__ import annotations

import pytest

from equation_parser_utils import tokenize_equation


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
        assert tokenize_equation("x * y = y * x") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_diamond_operator_normalized(self):
        """
        Scenario: ◇ is normalized to *
        Given 'x ◇ y = y ◇ x'
        When tokenize_equation is called
        Then ◇ becomes * in the token list
        """
        assert tokenize_equation("x ◇ y = y ◇ x") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_small_diamond_normalized(self):
        """
        Scenario: ⋄ (small diamond) is normalized to *
        Given 'x ⋄ y = y ⋄ x'
        When tokenize_equation is called
        Then ⋄ becomes *
        """
        assert tokenize_equation("x ⋄ y = y ⋄ x") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_parentheses_preserved(self):
        """
        Scenario: Parentheses become tokens
        Given 'x * (y * z) = (x * y) * z'
        When tokenize_equation is called
        Then parens appear in the token list
        """
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
        assert tokenize_equation("  x  *  y  =  y  *  x  ") == ["x", "*", "y", "=", "y", "*", "x"]

    @pytest.mark.unit
    def test_multi_letter_variable(self):
        """
        Scenario: Multi-letter variable names are captured whole
        Given 'xy * z = z * xy'
        When tokenize_equation is called
        Then 'xy' appears as a single token
        """
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
        assert tokenize_equation("x = x") == ["x", "=", "x"]


class TestUnknownCharsSurfacing:
    """Feature: tokenize_equation surfaces unrecognised characters (S6 / #54).

    Previous behaviour silently dropped digits, punctuation, and stray
    unicode operators, so ``x1 * y`` and ``x * y`` produced the same tokens.
    Now the dropped characters trigger a warning by default and raise under
    ``strict=True``.
    """

    @pytest.mark.unit
    def test_digit_in_variable_warns(self):
        with pytest.warns(UserWarning, match="dropped 1 unrecognised char"):
            tokens = tokenize_equation("x1 * y")
        # Existing behaviour preserved for non-strict callers: stray chars
        # are dropped but the rest tokenises.
        assert tokens == ["x", "*", "y"]

    @pytest.mark.unit
    def test_unknown_unicode_operator_warns(self):
        with pytest.warns(UserWarning, match="dropped"):
            tokens = tokenize_equation("x ⊕ y")
        assert tokens == ["x", "y"]

    @pytest.mark.unit
    def test_strict_mode_raises(self):
        with pytest.raises(ValueError, match="dropped"):
            tokenize_equation("x1 * y", strict=True)

    @pytest.mark.unit
    def test_strict_mode_passes_clean_input(self):
        # A clean input must not raise even with strict=True.
        assert tokenize_equation("x * y = y * x", strict=True) == [
            "x",
            "*",
            "y",
            "=",
            "y",
            "*",
            "x",
        ]

    @pytest.mark.unit
    def test_message_truncates_offender_list(self):
        # Six unknown characters should produce a "+1 more" suffix so the
        # message stays bounded for pathological inputs.
        with pytest.warns(UserWarning, match=r"\+1 more"):
            tokenize_equation("123456")
