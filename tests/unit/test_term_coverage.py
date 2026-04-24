"""Direct coverage tests for src/term.py that the canonical consolidation
(issue #27) did not exercise directly.

The #27 test file focuses on the *dedup contract* (same class re-exported
from three modules). Those tests pass without actually calling
``depth()``, ``size()``, or the parser error paths — they rely on
transitive coverage via higher-level tests. This module fills in the
direct call coverage so that a regression in ``Term.depth()`` or the
parser error reporting shows up as a localised failure instead of a
mystery analysis-result miscount three abstractions above.
"""

from __future__ import annotations

import pytest

from term import NodeType, Term, op, parse_equation_terms, parse_term, var


class TestTermDepthAndSize:
    """Direct depth/size coverage on OP nodes."""

    @pytest.mark.unit
    def test_depth_of_leaf_is_zero(self):
        assert var("x").depth() == 0

    @pytest.mark.unit
    def test_depth_of_single_op(self):
        """One binary op contributes one level of depth."""
        assert op(var("x"), var("y")).depth() == 1

    @pytest.mark.unit
    def test_depth_takes_max_of_branches(self):
        """An unbalanced tree reports the deeper branch's depth."""
        # Shape: ((x*y)*z) — left branch is 2 deep, right is 0.
        t = op(op(var("x"), var("y")), var("z"))
        assert t.depth() == 2

    @pytest.mark.unit
    def test_size_counts_ops_not_leaves(self):
        """``size()`` counts binary operations, not variables."""
        # Shape: (x*y)*(z*w) — three ops.
        t = op(op(var("x"), var("y")), op(var("z"), var("w")))
        assert t.size() == 3

    @pytest.mark.unit
    def test_size_of_leaf_is_zero(self):
        assert var("x").size() == 0


class TestParserErrorPaths:
    """Parser error messages are a debugging surface; cover them directly."""

    @pytest.mark.unit
    def test_parse_term_rejects_trailing_tokens(self):
        """``parse_term`` consumes the whole string; leftover tokens surface."""
        with pytest.raises(ValueError, match="trailing tokens"):
            parse_term("x * y ) extra")

    @pytest.mark.unit
    def test_parse_equation_terms_rejects_trailing_on_lhs(self):
        """Unbalanced parens on LHS emit a targeted message."""
        with pytest.raises(ValueError, match="trailing tokens on LHS"):
            parse_equation_terms("x * y) = z")

    @pytest.mark.unit
    def test_parse_equation_terms_rejects_trailing_on_rhs(self):
        """Unbalanced parens on RHS emit a targeted message."""
        with pytest.raises(ValueError, match="trailing tokens on RHS"):
            parse_equation_terms("x = y * z)")

    @pytest.mark.unit
    def test_parse_equation_terms_rejects_missing_equals(self):
        """A single ``=`` is required to separate LHS from RHS."""
        with pytest.raises(ValueError, match="'='"):
            parse_equation_terms("x * y")


class TestNodeTypeInvariant:
    """Invariant-encoding test: the is_var property matches NodeType.VAR
    exactly. If a future refactor flips the encoding (e.g. introduces a
    boolean field) without also updating ``is_var``, code across the
    codebase that pattern-matches on ``node_type`` will silently drift.
    This test forces a conscious decision when the representation changes.
    """

    @pytest.mark.unit
    def test_is_var_true_iff_node_type_var(self):
        """Encode the is_var ↔ NodeType.VAR invariant."""
        assert var("x").is_var is True
        assert op(var("x"), var("y")).is_var is False

        # Direct construction via NodeType must respect the same invariant.
        assert Term(NodeType.VAR, name="x").is_var is True
        assert Term(NodeType.OP, left=var("x"), right=var("y")).is_var is False
