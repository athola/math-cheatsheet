"""Tests for the shared Term AST module (issue #27).

Feature: Single canonical Term class + parser usable by both
    equation_analyzer and etp_equations, so bug fixes apply in one place
    and there is no cognitive overhead deciding which `Term` to import.

Acceptance criteria (from #27):
- Single Term class used everywhere.
- Single set of parser functions.
- All existing tests pass.
- No import cycles.
"""

from __future__ import annotations

import pytest

import equation_analyzer
import etp_equations
import term
from term import NodeType, Term, op, parse_equation_terms, var


class TestCanonicalTerm:
    """The shared module exposes one Term class other modules re-export."""

    @pytest.mark.unit
    def test_term_module_importable(self):
        assert Term is not None
        assert hasattr(NodeType, "VAR")
        assert hasattr(NodeType, "OP")

    @pytest.mark.unit
    def test_equation_analyzer_reexports_canonical_term(self):
        assert equation_analyzer.Term is term.Term
        assert equation_analyzer.NodeType is term.NodeType

    @pytest.mark.unit
    def test_etp_equations_reexports_canonical_term(self):
        assert etp_equations.Term is term.Term


class TestTermConstructorHelpers:
    """Convenient var()/op() factory helpers replace the direct Term(...) form."""

    @pytest.mark.unit
    def test_var_helper_builds_variable(self):
        t = var("x")
        assert t.node_type == NodeType.VAR
        assert t.name == "x"
        assert t.left is None
        assert t.right is None

    @pytest.mark.unit
    def test_op_helper_builds_application(self):
        t = op(var("x"), var("y"))
        assert t.node_type == NodeType.OP
        assert t.left is not None and t.left.name == "x"
        assert t.right is not None and t.right.name == "y"

    @pytest.mark.unit
    def test_is_var_property(self):
        assert var("x").is_var is True
        assert op(var("x"), var("y")).is_var is False


class TestSharedParser:
    """One parser function, used by both callers."""

    @pytest.mark.unit
    def test_parse_terms_returns_lhs_and_rhs_terms(self):
        lhs, rhs = parse_equation_terms("x * y = y * x")
        assert lhs.node_type == NodeType.OP
        assert rhs.node_type == NodeType.OP
        assert lhs.left is not None and lhs.left.name == "x"
        assert rhs.left is not None and rhs.left.name == "y"

    @pytest.mark.unit
    def test_parse_accepts_diamond_operator(self):
        lhs1, rhs1 = parse_equation_terms("x ◇ y = y ◇ x")
        lhs2, rhs2 = parse_equation_terms("x * y = y * x")
        assert lhs1 == lhs2
        assert rhs1 == rhs2

    @pytest.mark.unit
    def test_parse_rejects_missing_equals(self):
        with pytest.raises(ValueError, match="'='"):
            parse_equation_terms("x * y")


class TestParserErrorPaths:
    """Cover every parser error branch (NEW-I7 / #59).

    Coverage previously missed each of these branches; one bad refactor
    could silently flip the wrong error class without a regression
    surfacing.
    """

    @pytest.mark.unit
    def test_unbalanced_open_paren_on_lhs(self):
        # _parse_primary recurses into (x*y, runs out of tokens before ')'.
        with pytest.raises(ValueError, match=r"Expected '\)'"):
            parse_equation_terms("(x*y = z")

    @pytest.mark.unit
    def test_unbalanced_open_paren_on_rhs(self):
        with pytest.raises(ValueError, match=r"Expected '\)'"):
            parse_equation_terms("x = (y")

    @pytest.mark.unit
    def test_bare_leading_operator(self):
        # Tokens [*, x] — _parse_primary sees '*' first and falls through to
        # the "Unexpected token" branch.
        with pytest.raises(ValueError, match="Unexpected token"):
            parse_equation_terms("* x = y")

    @pytest.mark.unit
    def test_trailing_operator(self):
        # Tokens [x, *] — _parse_expr enters the "*" branch and calls
        # _parse_primary at pos = len(tokens), hitting "Unexpected end".
        with pytest.raises(ValueError, match="Unexpected end of expression"):
            parse_equation_terms("x * = y")

    @pytest.mark.unit
    def test_op_term_with_missing_left_child_rejected(self):
        # NEW-I4 (#58) — Term construction now validates the OP/VAR
        # invariant; previously this produced a "successful" Term that
        # only failed at access via _lr().
        with pytest.raises(ValueError, match="OP node must have both left and right"):
            Term(NodeType.OP, left=None, right=var("x"))

    @pytest.mark.unit
    def test_op_term_with_missing_right_child_rejected(self):
        with pytest.raises(ValueError, match="OP node must have both left and right"):
            Term(NodeType.OP, left=var("x"), right=None)

    @pytest.mark.unit
    def test_op_term_with_no_children_rejected(self):
        with pytest.raises(ValueError, match="OP node must have both left and right"):
            Term(NodeType.OP)
