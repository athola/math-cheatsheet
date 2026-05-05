"""Invariant-encoding tests for the analyze_implication phase pipeline.

These tests are intentionally load-bearing. If one of them breaks, it
means someone reordered or removed a phase in ``analyze_implication``,
and the reviewer must make an explicit decision about whether the
invariant is being preserved, layered on top, or revised.

The design invariants encoded here came out of implementing Phase 6
(issue #28): the original Phase 7 depth heuristic was pre-empting valid
Phase 6 rewrite proofs and returning FALSE for implications that are
actually TRUE. The fix was placing Phase 6 *before* Phase 7. This file
pins that decision so a future refactor cannot silently undo it.
"""

from __future__ import annotations

import pytest

from equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)


class TestPhaseOrderingInvariants:
    """Positive-verdict phases must run before conservative FALSE fallbacks.

    General principle: any phase that returns TRUE as a proof certificate
    must run before any phase that returns FALSE as a refutation-by-guess.
    Otherwise the guess short-circuits the proof.
    """

    @pytest.mark.unit
    def test_phase6_runs_before_phase7_depth_heuristic(self):
        """Phase 6 (TRUE via rewrite) must precede Phase 7 (FALSE via depth).

        Pair: H: x = x*x, T: x = ((x*x)*x)*x. T.depth is 3, H.depth is 1,
        so the Phase 7 depth rule (t.depth > h.depth + 1) would rule
        FALSE. But Phase 6 reduces T's RHS to x via two applications of
        x*x → x, proving TRUE.

        If this test fails with verdict FALSE at phase 7, someone has
        reordered the phases. Options:
        - Preserve: move the Phase 6 call back above the Phase 7 checks.
        - Layer: add a pre-Phase-7 short-circuit that detects rewritable
          cases without fully running Phase 6.
        - Revise: document a new semantics in which rewrite proofs are
          not trusted over depth heuristics (requires a design note).
        """
        h = parse_equation("x = x * x")
        t = parse_equation("x = ((x * x) * x) * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE, (
            f"Phase 7 pre-empted Phase 6: verdict={result.verdict} at "
            f"{result.phase}. See test docstring for remediation options."
        )
        assert result.phase == "Phase 6", (
            f"A phase other than 6 took credit for this proof: {result.phase}. "
            "Verify Phase 6 placement in analyze_implication()."
        )

    @pytest.mark.unit
    def test_phase4_counterexample_runs_before_phase6_rewrite(self):
        """Phase 4 (FALSE via concrete counterexample) must precede Phase 6.

        Pair: commutativity ⇏ associativity. Phase 4's canonical CM
        magma (commutative non-associative) is the correct witness.
        Phase 6 must not try to rewrite its way to a false TRUE here
        because commutativity oriented as a rewrite doesn't close
        associativity.

        If Phase 6 ever returns TRUE on this pair, either the rewrite
        engine is unsound or Phase 4 was removed from the pipeline.
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("(x * y) * z = x * (y * z)")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE, (
            f"Commutativity ⇏ associativity produced {result.verdict} at "
            f"{result.phase} — Phase 4 counterexample must still fire."
        )
        # Phase 4/4b should win; Phase 6 must not.
        assert result.phase != "Phase 6", (
            f"Phase 6 claimed TRUE on a known-FALSE pair: {result.phase}. "
            "Either the rewrite soundness filter is broken or Phase 4 was "
            "reordered below Phase 6."
        )

    @pytest.mark.unit
    def test_phase1b_tautology_beats_everything(self):
        """Phase 1b (tautology target → TRUE) must run before any
        structural heuristic. Otherwise Phase 7's op-count rule would
        wrongly FALSE a target like ``x = x`` when H has many ops."""
        # Large H, trivial T.
        h = parse_equation("((x * y) * z) * (w * v) = x * (y * (z * (w * v)))")
        t = parse_equation("x = x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
        assert result.phase == "Phase 1b", (
            f"Tautology short-circuit missed: {result.phase}. "
            "Check that Phase 1b runs before Phase 7 heuristics."
        )


class TestPhase6BeatsPhase7cInteraction:
    """S8 (#59): Phase 6 and Phase 7c can both fire on the same pair, but
    Phase 6's TRUE proof must beat Phase 7c's op-count FALSE.
    """

    @pytest.mark.unit
    def test_phase6_true_overrides_phase7c_false_op_count(self):
        """H: x = x*x; T: x = ((x*x)*x)*x.

        - Phase 6 reduces T.RHS to x via x*x→x and proves TRUE.
        - Phase 7c (op-count: t.ops > 2*h.ops + 2) would have triggered
          FALSE in isolation: T has 3 ops, H has 1 op, 3 > 2*1+2=4 is False
          (so this specific pair is not actually a 7c trigger). Need a
          larger T to force the 7c branch.

        Use T = x = (((x*x)*x)*x)*x (5 ops). 5 > 2*1+2=4 is True →
        Phase 7c would fire FALSE. But because H has the variable x
        repeating (so _h_vars_unique returns False), Phase 7c is gated
        off and Phase 6 still gets to prove TRUE. The combination
        verifies both the gate AND that Phase 6 fires before Phase 7c.
        """
        h = parse_equation("x = x * x")
        t = parse_equation("x = (((x * x) * x) * x) * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE, (
            f"Phase 6 should derive TRUE despite t.ops > 2*h.ops + 2;"
            f" got {result.verdict} at {result.phase}: {result.reason}"
        )
        assert result.phase == "Phase 6"


class TestPhase4bCacheCallReduction:
    """S9 (#59): pin the cache complexity claim with a holds_in call counter
    so a regression that bypasses the cache (or stops being hashable) shows
    up as a failing assertion rather than a silent perf regression.
    """

    @pytest.mark.unit
    def test_size_2_satisfactions_caches_per_equation(self):
        from unittest import mock

        from equation_analyzer import _size_2_satisfactions

        # Clear any prior cache entries so the call count is deterministic.
        _size_2_satisfactions.cache_clear()
        h = parse_equation("x * y = y * x")
        # Wrap holds_in to count invocations from the cache function.
        original_holds_in = type(h).holds_in
        with mock.patch.object(type(h), "holds_in", autospec=True) as mocked:
            mocked.side_effect = original_holds_in
            _size_2_satisfactions(h)
            first_call_count = mocked.call_count
            assert first_call_count == 16, (
                f"First evaluation must check all 16 size-2 magmas; got {first_call_count} calls."
            )
            _size_2_satisfactions(h)
            assert mocked.call_count == first_call_count, (
                "Cached lookup must not call holds_in again;"
                f" got {mocked.call_count - first_call_count} extra calls."
            )


class TestSoundnessOnRandomEquations:
    """S7 (#59): hypothesis-driven soundness check.

    For every TRUE verdict from analyze_implication on a randomly
    generated (H, T) pair, T must hold in every magma where H holds —
    bounded to size ≤ 3 magmas to keep the test fast. A regression that
    introduces an unsound rewrite or a false-TRUE structural shortcut
    surfaces as a counterexample-via-Hypothesis rather than as an
    unexplained accuracy delta on the full corpus.
    """

    @pytest.mark.slow
    def test_true_verdict_holds_in_every_h_satisfying_magma_size_3(self):
        from itertools import product

        from hypothesis import HealthCheck, given, settings
        from hypothesis import strategies as st

        equation_strs = st.sampled_from(
            [
                "x = x",
                "x * y = y * x",
                "(x * y) * z = x * (y * z)",
                "x * x = x",
                "x = x * x",
                "x * y = x",
                "x * y = y",
                "x * (y * z) = (x * y) * z",
                "(x * y) * z = (x * z) * y",
            ]
        )

        @given(equation_strs, equation_strs)
        @settings(
            max_examples=30,
            deadline=2000,
            suppress_health_check=[HealthCheck.function_scoped_fixture],
        )
        def check(h_str: str, t_str: str) -> None:
            h = parse_equation(h_str)
            t = parse_equation(t_str)
            result = analyze_implication(h, t)
            if result.verdict != ImplicationVerdict.TRUE:
                return  # Only TRUE verdicts carry soundness obligations.
            # If H ⇒ T is claimed, every magma satisfying H must also
            # satisfy T. Check exhaustively for sizes 1..3.
            for size in (1, 2, 3):
                for table_flat in product(range(size), repeat=size * size):
                    table = [list(table_flat[i * size : (i + 1) * size]) for i in range(size)]
                    if h.holds_in(table, size) and not t.holds_in(table, size):
                        raise AssertionError(
                            f"Soundness violation: {h} ⇒ {t} claimed at "
                            f"{result.phase}, but size-{size} magma {table} "
                            f"satisfies H and not T."
                        )

        check()
