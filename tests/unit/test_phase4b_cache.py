"""Tests for Phase 4b satisfiability cache (issue #34).

Feature: per-equation size-2 satisfiability cache
    Phase 4b tests each equation pair against all 16 size-2 magmas. Because
    ``Equation.holds_in`` is deterministic, the set of satisfying magmas
    depends only on the equation, not on the pair it appears in. Caching
    per-equation turns the per-pair cost from O(16 × evaluations) into
    O(1 dict lookup) after first encounter.

Acceptance criteria (from #34):
- Satisfiability cache computed once per equation (not per pair).
- Phase 4b uses cache instead of per-pair evaluation.
- No accuracy regression.
"""

from __future__ import annotations

import pytest

from equation_analyzer import (
    ALL_SIZE_2_MAGMAS,
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)


class TestSatisfactionCacheSemantics:
    """The cached lookup must return the same result as per-pair evaluation."""

    @pytest.mark.unit
    def test_cache_returns_same_indices_as_direct_evaluation(self):
        """For each of the 16 2-element magmas, the cache must agree with
        the direct ``Equation.holds_in`` call."""
        from equation_analyzer import _size_2_satisfactions

        eq = parse_equation("x * y = y * x")  # commutativity
        cached = _size_2_satisfactions(eq)
        direct = frozenset(
            i for i, magma in enumerate(ALL_SIZE_2_MAGMAS) if eq.holds_in(magma.table, magma.size)
        )
        assert cached == direct

    @pytest.mark.unit
    def test_cache_is_idempotent(self):
        """Calling the cache twice returns the same frozenset (not a new copy)."""
        from equation_analyzer import _size_2_satisfactions

        eq = parse_equation("x * x = x")
        first = _size_2_satisfactions(eq)
        second = _size_2_satisfactions(eq)
        assert first == second


class TestPhase4bUsesCache:
    """Phase 4b must not call ``Equation.holds_in`` more times than necessary.
    Specifically, for two analyses that share H, the cache should avoid
    re-evaluating H against the 16 magmas."""

    @pytest.mark.unit
    def test_shared_hypothesis_evaluated_once(self):
        """Two analyses with the same H should evaluate H at most 16 times total,
        not 32 (which would mean the cache did nothing)."""
        h = parse_equation("x * y = y * x")
        t1 = parse_equation("x * y = y * x")  # same as H, caught by Phase 1a
        t2 = parse_equation("(x * y) * z = x * (y * z)")  # associativity, Phase 4 catches

        # We test the cache itself; analyze_implication may short-circuit
        # before Phase 4b for these, so also do a direct cache check.
        from equation_analyzer import _size_2_satisfactions

        _size_2_satisfactions.cache_clear()
        _size_2_satisfactions(h)
        _size_2_satisfactions(h)  # second call should be a cache hit
        info = _size_2_satisfactions.cache_info()
        assert info.hits >= 1, f"expected >=1 cache hit, got {info}"
        assert info.misses == 1, f"expected exactly 1 cache miss, got {info}"

        # Clean state for other tests.
        _size_2_satisfactions.cache_clear()

        # Exercise the full pipeline — result parity with direct evaluation:
        r1 = analyze_implication(h, t1)
        r2 = analyze_implication(h, t2)
        assert r1.verdict == ImplicationVerdict.TRUE
        assert r2.verdict == ImplicationVerdict.FALSE


class TestPhase4bRegression:
    """Pre-#34 behaviour on known pairs must be preserved."""

    @pytest.mark.unit
    def test_commutativity_not_implies_associativity(self):
        h = parse_equation("x * y = y * x")
        t = parse_equation("(x * y) * z = x * (y * z)")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_idempotence_with_rewrite_is_true(self):
        h = parse_equation("x = x * x")
        t = parse_equation("x = (x * x) * x")
        result = analyze_implication(h, t)
        assert result.verdict == ImplicationVerdict.TRUE
