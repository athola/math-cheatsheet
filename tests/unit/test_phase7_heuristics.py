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
    _h_vars_unique,
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
    def test_idempotence_normalises_via_phase6_not_phase7c(self):
        """H: x*x=x (var-repeating, total_ops=1). T: x*x*x*x*x = x*x*x (total_ops=6).

        T.ops (6) > 2*H.ops + 2 (4), so the broken Phase 7c bound would have
        marked this FALSE. After the soundness fix (NEW-C1), Phase 7c is gated
        on H having unique variable occurrences and won't fire here. Phase 6
        rewrites both sides via ``x*x → x`` to ``x``, returning TRUE.

        Pins both verdict AND phase so a regression that bypasses Phase 6 or
        re-enables Phase 7c on var-repeating H is caught (NEW-C2 / NEW-N3).
        """
        h = parse_equation("x * x = x")
        t = parse_equation("x * x * x * x * x = x * x * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 6"


class TestPhase7cSoundnessGuard:
    """NEW-C1: Phase 7c's ``T.ops > 2*H.ops + 2`` bound is unsound when H has
    repeated variables. Substituting ``x → s`` with ``x`` appearing ``k`` times
    in H grows ops by ``k * size(s)``, which can exceed the bound for valid
    implications.

    Fix: gate Phase 7c on H having unique variable occurrences globally
    (``_h_vars_unique``). These tests pin the precondition behaviour so future
    edits to the rule cannot reintroduce the unsound branch by accident.
    """

    @pytest.mark.unit
    def test_unique_vars_helper_accepts_distinct_variables(self):
        """``x*y = z*w`` — every variable appears exactly once."""
        assert _h_vars_unique(parse_equation("x * y = z * w")) is True

    @pytest.mark.unit
    def test_unique_vars_helper_accepts_collapse_law(self):
        """``x = y`` — two distinct variables, one occurrence each."""
        assert _h_vars_unique(parse_equation("x = y")) is True

    @pytest.mark.unit
    def test_unique_vars_helper_rejects_idempotence(self):
        """``x*x = x`` — ``x`` appears three times. Phase 7c must not fire."""
        assert _h_vars_unique(parse_equation("x * x = x")) is False

    @pytest.mark.unit
    def test_unique_vars_helper_rejects_commutativity(self):
        """``x*y = y*x`` — ``x`` and ``y`` each appear twice. Repetition across
        sides is enough to invalidate the bound."""
        assert _h_vars_unique(parse_equation("x * y = y * x")) is False

    @pytest.mark.unit
    def test_phase7c_does_not_force_false_on_var_repeating_h(self):
        """Direct integration check: with H = ``x*x = x`` (idempotence), no T
        constructible from H's variables should receive a Phase 7c FALSE
        verdict — the bound is unsound for this H.

        The chosen T is genuinely TRUE under H (substituting nothing, but
        idempotence collapses both sides). Phase 6 catches it at TRUE; the
        critical assertion is the negative one — verdict is not FALSE via
        Phase 7."""
        h = parse_equation("x * x = x")
        t = parse_equation("(x * x) * (x * x) = x * x")
        result = analyze_implication(h, t)
        assert not (result.verdict == ImplicationVerdict.FALSE and result.phase == "Phase 7")


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
