"""Tests for Phase 6 rewrite analysis (issue #28).

Feature: Use H as a rewrite rule on T
    Phase 6 orients H's LHS → RHS as a rewrite rule, applies it to T's
    LHS and RHS up to a bounded depth, and returns TRUE when the rewritten
    target collapses to a tautology. Catches implications that substitution
    (Phase 3) misses because the witness requires unfolding a sub-term,
    not just renaming variables.

Acceptance criteria (from #28):
- Phase 6 implemented in analyze_implication().
- Depth-limited to prevent exponential blowup.
- Tests for rewrite-provable implications.
- No accuracy regression on existing test suite.
"""

from __future__ import annotations

import pytest

from equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)


class TestPhase6ReachesRewriteVerdict:
    """Phase 6 should surface in the `phase` field when rewrite is the witness."""

    @pytest.mark.unit
    def test_idempotence_implies_triple_product(self):
        """H: x = x*x ⇒ T: x = (x*x)*x.

        No earlier phase catches this:
        - Phase 2: T.vars = H.vars = {x}.
        - Phase 3: skipped (H has only 1 variable).
        - Phase 4/4b: every 2-element idempotent magma satisfies T too.
        - Phase 5 / Phase 7: don't apply.

        Phase 6 catches it by rewriting T.RHS ``(x*x)*x`` using H:
        ``x*x → x`` yields ``x*x``; applying H again yields ``x``,
        which equals T.LHS.
        """
        h = parse_equation("x = x * x")
        t = parse_equation("x = (x * x) * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 6", (
            f"expected Phase 6 as the proof witness, got {result.phase}: {result.reason}"
        )

    @pytest.mark.unit
    def test_idempotence_implies_four_product(self):
        """H: x = x*x ⇒ T: x = ((x*x)*x)*x (one more rewrite step)."""
        h = parse_equation("x = x * x")
        t = parse_equation("x = ((x * x) * x) * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE


class TestPhase6DoesNotRegress:
    """Phase 6 must not turn existing FALSE verdicts into TRUE."""

    @pytest.mark.unit
    def test_commutativity_does_not_imply_associativity(self):
        """Commutativity does not imply associativity.

        Phase 4 catches this with a canonical magma (CM). Phase 6 must not
        prematurely rewrite its way to a false TRUE.
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("(x * y) * z = x * (y * z)")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_idempotence_does_not_imply_left_identity(self):
        """x = x*x does not imply x*y = y (left projection)."""
        h = parse_equation("x = x * x")
        t = parse_equation("x * y = y")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE


class TestPhase6Termination:
    """Depth-limit guarantees termination even on rewrite systems that never close."""

    @pytest.mark.unit
    def test_non_terminating_rewrite_exits_gracefully(self):
        """H: x = x*x oriented forward grows unboundedly.

        The canonical orientation (LHS → RHS) here would rewrite x to x*x to
        x*x*x indefinitely. The implementation must bound depth so
        ``analyze_implication`` returns in finite time regardless of verdict.
        """
        h = parse_equation("x = x * x")
        # T that doesn't close but must not hang:
        t = parse_equation("x * x = x")
        result = analyze_implication(h, t)
        assert result.verdict in {
            ImplicationVerdict.TRUE,
            ImplicationVerdict.FALSE,
            ImplicationVerdict.UNKNOWN,
        }
