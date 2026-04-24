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
