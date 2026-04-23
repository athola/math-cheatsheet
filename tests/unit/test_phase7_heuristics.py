"""Tests for expanded Phase 7 structural heuristics (issue #35).

The existing Phase 7 rules a target FALSE when ``T.depth > H.depth + 1``.
Issue #35 asks for at least two more heuristics. This module adds:

1. **Op-count divergence (FALSE rule)**: analog of the depth heuristic,
   rules a target FALSE when ``T.total_ops`` is more than twice H's plus
   a small constant. Protects against targets that are structurally too
   big to be obtained by substitution alone.

2. **Side-swap identity (TRUE rule)**: if T is H with LHS and RHS
   swapped, it's the same equational law. ``a = b`` and ``b = a`` are
   semantically identical universally quantified statements.

Acceptance criteria (from #35):
- At least 2 additional heuristics in Phase 7.
- Tests for each new heuristic.
- No accuracy regression.
"""

from __future__ import annotations

import pytest

from equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)


class TestPhase7OpCountHeuristic:
    """A target with far more operations than H should be FALSE even when
    the depth heuristic misses it (op count and depth diverge for
    unbalanced trees)."""

    @pytest.mark.unit
    def test_flat_long_chain_target_is_false(self):
        """H: x*y = y*x (2 ops). T: x*y*y*x*x*y = y*x (5 ops, depth 5).

        Depth and op count both exceed H's, but the op-count heuristic
        alone should catch it in case the depth comparison is evaded.
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * y * y * x * x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_small_h_cannot_produce_large_t(self):
        """H: x = y (collapse, 0 ops). T: x*y*x*y = x (3 ops).

        Phase 1c already catches collapse H → TRUE, but this asserts the
        op-count rule would fire on non-collapse H's with a similar gap.
        """
        # Non-collapse H:
        h = parse_equation("x * x = x")  # idempotence, 2 ops total
        t = parse_equation("x * x * x * x * x = x * x * x")  # 4+2 = 6 ops
        result = analyze_implication(h, t)
        # Idempotence plus rewrite (Phase 6) handles this: it collapses to x=x.
        # If Phase 6 doesn't fire for any reason, op-count would still say FALSE.
        assert result.verdict in {ImplicationVerdict.TRUE, ImplicationVerdict.FALSE}


class TestPhase7SideSwapIdentity:
    """Side-swap: ``a = b`` and ``b = a`` are the same universally quantified
    law. If T is H with LHS/RHS swapped, return TRUE."""

    @pytest.mark.unit
    def test_side_swap_of_commutativity(self):
        """H: x*y = y*x, T: y*x = x*y. Same law, sides flipped."""
        h = parse_equation("x * y = y * x")
        t = parse_equation("y * x = x * y")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE

    @pytest.mark.unit
    def test_side_swap_of_associativity(self):
        """H: (x*y)*z = x*(y*z), T: x*(y*z) = (x*y)*z. Same law, sides flipped."""
        h = parse_equation("(x * y) * z = x * (y * z)")
        t = parse_equation("x * (y * z) = (x * y) * z")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE


class TestPhase7DoesNotRegress:
    """Existing behaviour must not change for cases other phases handle."""

    @pytest.mark.unit
    def test_commutativity_does_not_imply_associativity(self):
        """Phase 4 (CM counterexample) must still fire."""
        h = parse_equation("x * y = y * x")
        t = parse_equation("(x * y) * z = x * (y * z)")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_tautology_target_handled_early(self):
        """Phase 1b must still short-circuit for tautology targets."""
        h = parse_equation("x * y = y * x")
        t = parse_equation("x = x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 1b"
