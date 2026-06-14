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
    """A target structurally too big to be reached from H must be FALSE — but
    via the *sound* counterexample search (Phases 4/4b), not a syntactic
    op-count/depth bound. The bound was removed as unsound (review H2)."""

    @pytest.mark.unit
    def test_flat_long_chain_target_is_false(self):
        """H: x*y = y*x. T: x*y*y*x*x*y = y*x.

        T is not implied by commutativity (commutativity cannot reduce a
        depth-5 product to ``y*x``). The commutative-but-non-associative
        canonical magma CM refutes it, so Phase 4 returns FALSE soundly —
        no reliance on the removed syntactic op-count heuristic.
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * y * y * x * x * y = y * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_idempotence_normalises_via_phase6(self):
        """H: x*x=x. T: x*x*x*x*x = x*x*x.

        The old (unsound) Phase 7c op-count bound would have marked this FALSE.
        With that bound removed, Phase 6 rewrites both sides via ``x*x → x`` to
        ``x`` and returns TRUE. Pins verdict AND phase so a regression that
        re-introduces a syntactic-size FALSE rule is caught.
        """
        h = parse_equation("x * x = x")
        t = parse_equation("x * x * x * x * x = x * x * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 6"


class TestDepthAndOpCountNoLongerRefute:
    """review H2: syntactic depth / op-count divergence is NOT a sound
    refutation under congruence closure. Phases 7b/7c no longer emit FALSE;
    such pairs reach the Phase 8 UNKNOWN verdict (or a sound earlier phase)."""

    @pytest.mark.unit
    def test_var_repeating_h_never_false_via_phase7(self):
        """H = ``x*x = x``. T is genuinely TRUE under H; the critical check is
        that no FALSE verdict is ever attributed to Phase 7."""
        h = parse_equation("x * x = x")
        t = parse_equation("(x * x) * (x * x) = x * x")
        result = analyze_implication(h, t)
        assert not (result.verdict == ImplicationVerdict.FALSE and result.phase == "Phase 7")

    @pytest.mark.unit
    def test_deep_congruence_consequence_is_not_false(self):
        """H = commutativity. T has depth 3 (> H.depth + 1) yet holds in every
        commutative magma by congruence, so it must not be refuted."""
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * (y * (x * y)) = x * (y * (y * x))")
        result = analyze_implication(h, t)
        assert result.verdict != ImplicationVerdict.FALSE


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
