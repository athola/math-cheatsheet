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

        Phase 6 catches it via the RHS→LHS orientation of H. H is
        ``x = x*x`` so the RHS→LHS rule rewrites ``x*x → x`` (note: the
        rule's LHS in this orientation is H.RHS, ``x*x``). Applied to
        T.RHS = ``(x*x)*x``: the inner ``x*x`` reduces to ``x``, giving
        ``x*x``; applying again yields ``x``, equal to T.LHS — so
        Phase 6 closes the implication. NEW-I11 / S11 (#62) updated
        this docstring to be unambiguous about which orientation fires.
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


class TestRewriteOnceRightChildPath:
    """Coverage: line 500 of equation_analyzer.py — when the rule does not
    match the whole term or the left subtree but does match the right
    subtree, ``_rewrite_once`` must descend into the right child and
    rebuild the OP node with the rewritten right side.
    """

    @pytest.mark.unit
    def test_right_only_rewrite_descends_correctly(self):
        from equation_analyzer import _rewrite_once, op, parse_equation, var

        # Rule: y * y → y. Term: a * (y * y). Pattern doesn't match the
        # whole term (root is a*..., not y*y). Doesn't match left (a is
        # a leaf). Matches the right subtree (y * y) → y. Result: a * y.
        h = parse_equation("y * y = y")
        target = op(var("a"), op(var("y"), var("y")))
        out = _rewrite_once(target, h.lhs, h.rhs)
        assert out is not None
        assert str(out) == "(a * y)"


class TestRewriteStatusObservability:
    """NEW-I1 (#60): _rewrite_to_normal_form returns a status code so callers
    can distinguish normal-form completion from cycle abort or budget hit.
    """

    @pytest.mark.unit
    def test_returns_normal_form_when_no_match(self):
        from equation_analyzer import _rewrite_to_normal_form, parse_equation

        h = parse_equation("x = x * x")
        # Pattern x*x never matches a bare variable, so we land in normal form
        # immediately on the first iteration.
        target = parse_equation("y = y").lhs
        out, status = _rewrite_to_normal_form(target, h.rhs, h.lhs)
        assert status == "normal_form"
        assert out == target

    @pytest.mark.unit
    def test_returns_cycle_or_budget_on_growing_orientation(self):
        from equation_analyzer import _rewrite_to_normal_form, parse_equation

        # x → x*x grows the term every step. With max_steps=4 the rewriter
        # must terminate via either the budget guard or (less likely here)
        # cycle detection — but never silently return the original term.
        h = parse_equation("x = x * x")
        original = parse_equation("x = x").lhs
        out, status = _rewrite_to_normal_form(original, h.lhs, h.rhs, max_steps=4)
        assert status in {"budget", "cycle"}
        # The rewriter actually applied the rule, so out is not the input.
        assert out != original


class TestMatchPatternRollsBackBindings:
    """NEW-I2 (#60): _match_pattern restores the bindings dict on failure
    so a partially populated dict cannot leak into a sibling sub-match.
    """

    @pytest.mark.unit
    def test_failed_match_does_not_pollute_caller_bindings(self):
        from equation_analyzer import _match_pattern, parse_equation

        # Pattern: x * x ; Target: a * b. The left sub-match binds x→a,
        # the right sub-match (x must equal b) fails because b ≠ a.
        # The caller's bindings dict must be empty after the failure.
        pattern = parse_equation("x * x = x").lhs  # OP node ((x, x))
        target = parse_equation("a * b = a").lhs  # OP node ((a, b))
        bindings: dict = {}
        assert _match_pattern(pattern, target, bindings) is False
        assert bindings == {}, (
            "Failed match leaked partial bindings — would corrupt sibling "
            "sub-matches in any pattern-cache or AC-matching extension"
        )


class TestRuleSoundnessGuard:
    """NEW-I8 (#60): _rule_is_sound's False branch must protect Phase 6.

    Some equations have only one sound orientation. Phase 6 must reject the
    unsound orientation (RHS variables not contained in LHS would invent
    fresh values) and still derive TRUE via the sound orientation when
    available.
    """

    @pytest.mark.unit
    def test_unsound_orientation_is_rejected(self):
        """``x = x*y`` oriented RHS→LHS is sound (drops y); LHS→RHS would
        invent ``y`` from a bare ``x`` and is unsound.

        Phase 6's `continue` on unsoundness is the only thing preventing
        the rewriter from emitting a proof that introduces fresh
        variables — exactly the bug-class issue #60 NEW-I8 calls out.
        """
        from equation_analyzer import _rule_is_sound, parse_equation

        h = parse_equation("x = x * y")
        # LHS→RHS: lhs vars {x}, rhs vars {x, y} — y is fresh, unsound.
        assert _rule_is_sound(h.lhs, h.rhs) is False
        # RHS→LHS: lhs vars {x, y}, rhs vars {x} — drops y, sound.
        assert _rule_is_sound(h.rhs, h.lhs) is True

    @pytest.mark.unit
    def test_phase6_still_derives_when_only_one_orientation_is_sound(self):
        """H: x*x = x has both orientations sound; Phase 6 must still close
        T: (x*x)*x = x. The earlier `idempotence_implies_triple_product`
        test exercises this path — keep an explicit anchor here so a future
        soundness regression that flips _rule_is_sound surfaces as a
        named test failure rather than an opaque accuracy regression.
        """
        h = parse_equation("x * x = x")
        t = parse_equation("(x * x) * x = x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 6"

    @pytest.mark.unit
    def test_phase6_continue_on_unsound_orientation(self):
        """Coverage: line 567 of equation_analyzer.py — _phase6_rewrite's
        `continue` skips an unsound orientation and tries the other.

        H: x*x = x*y. LHS→RHS rule (x*x → x*y) introduces fresh ``y`` and is
        unsound — must be skipped via the continue. RHS→LHS rule
        (x*y → x*x) drops y and is sound; if its rewrite closes T, Phase 6
        returns TRUE, otherwise None. The point is exercising the
        `continue` branch, not the verdict.
        """
        from equation_analyzer import _phase6_rewrite, _rule_is_sound

        h = parse_equation("x * x = x * y")
        # Confirm one orientation is unsound (forces the continue) and
        # the other is sound (so the loop has a second iteration to run).
        assert _rule_is_sound(h.lhs, h.rhs) is False  # x*x → x*y is unsound
        assert _rule_is_sound(h.rhs, h.lhs) is True  # x*y → x*x is sound
        # Pick any T; we don't care about the verdict, just that
        # _phase6_rewrite executes both orientations (one continued, one
        # full-evaluated) without raising.
        t = parse_equation("x = x")
        result = _phase6_rewrite(h, t)
        # T is a tautology so Phase 6 may or may not derive — either is
        # fine; the line-567 continue executed regardless.
        assert result is None or result.verdict == ImplicationVerdict.TRUE
