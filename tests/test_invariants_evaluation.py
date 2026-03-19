"""Property-based invariant tests for the evaluation harness.

Verifies that evaluation metrics maintain mathematical consistency
regardless of input distribution, ensuring the accuracy formula
and counting invariants never break.

BDD Scenarios:
  Feature: Evaluation metric consistency
  Scenario: Given ANY set of evaluation results, THEN metric invariants hold
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from evaluation import EvaluationResult, Evaluator

# ── Strategies ──────────────────────────────────────────────────


@st.composite
def evaluation_results(draw, model: str = "test"):
    """Generate an arbitrary EvaluationResult."""
    problem_id = draw(st.integers(min_value=1, max_value=10000))
    eq1 = draw(st.integers(min_value=1, max_value=100))
    eq2 = draw(st.integers(min_value=1, max_value=100))
    actual = draw(st.one_of(st.none(), st.booleans()))
    predicted = draw(st.one_of(st.none(), st.booleans()))

    if predicted is None:
        correct = False
    else:
        correct = predicted == actual if actual is not None else False

    time_ms = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False))

    return EvaluationResult(
        problem_id=problem_id,
        equation_1_id=eq1,
        equation_2_id=eq2,
        predicted_answer=predicted,
        actual_answer=actual,
        correct=correct,
        response_time_ms=time_ms,
        model=model,
    )


@st.composite
def result_lists(draw, min_size: int = 0, max_size: int = 50):
    """Generate a list of evaluation results."""
    return draw(st.lists(evaluation_results(), min_size=min_size, max_size=max_size))


# ── Feature: Counting invariant ─────────────────────────────────
# Given: ANY list of EvaluationResults
# Then: correct + incorrect + skipped = total


@pytest.mark.property
class TestCountingInvariant:
    """Scenario: Result counts always sum to total."""

    @given(results=result_lists(min_size=1))
    def test_counts_sum_to_total(self, results):
        """correct + incorrect + skipped = total for any result set."""
        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        assert summary.correct + summary.incorrect + summary.skipped == summary.total_problems

    @given(results=result_lists(min_size=1))
    def test_total_equals_result_count(self, results):
        """total_problems equals len(results)."""
        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        assert summary.total_problems == len(results)


# ── Feature: Accuracy bounds ────────────────────────────────────
# Given: ANY list of EvaluationResults
# Then: 0 ≤ accuracy ≤ 1


@pytest.mark.property
class TestAccuracyBounds:
    """Scenario: Accuracy is always in [0, 1]."""

    @given(results=result_lists(min_size=1))
    def test_accuracy_in_unit_interval(self, results):
        """Accuracy ∈ [0, 1] for any result set."""
        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        assert 0.0 <= summary.accuracy <= 1.0

    def test_empty_results_zero_accuracy(self):
        """Empty results → accuracy = 0 (no division by zero)."""
        evaluator = Evaluator(model="test")
        evaluator.results = []
        summary = evaluator._compute_summary("test")

        assert summary.accuracy == 0.0
        assert summary.total_problems == 0


# ── Feature: Accuracy formula correctness ───────────────────────
# Given: ANY list of EvaluationResults with at least one non-skipped
# Then: accuracy = correct / (total - skipped)


@pytest.mark.property
class TestAccuracyFormula:
    """Scenario: Accuracy follows the documented formula."""

    @given(results=result_lists(min_size=1))
    def test_accuracy_formula_matches(self, results):
        """accuracy = correct / evaluated where evaluated = total - skipped."""
        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        evaluated = summary.total_problems - summary.skipped
        if evaluated > 0:
            expected_accuracy = summary.correct / evaluated
            assert abs(summary.accuracy - expected_accuracy) < 1e-10
        else:
            assert summary.accuracy == 0.0

    @given(results=result_lists(min_size=1))
    def test_all_correct_means_full_accuracy(self, results):
        """If every non-skipped result is correct, accuracy = 1.0."""
        # Build modified copies instead of mutating (Hypothesis anti-pattern)
        from dataclasses import replace
        results = [
            replace(r, actual_answer=r.predicted_answer, correct=True)
            if r.predicted_answer is not None
            else r
            for r in results
        ]

        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        if summary.skipped < summary.total_problems:
            assert summary.accuracy == 1.0


# ── Feature: Skipped result handling ────────────────────────────
# Given: Results where predicted_answer is None
# Then: They are counted as skipped, not incorrect


@pytest.mark.property
class TestSkippedHandling:
    """Scenario: None predictions are skipped, not wrong."""

    @given(results=result_lists(min_size=1))
    def test_none_predictions_are_skipped(self, results):
        """predicted_answer=None → skipped, not incorrect."""
        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        manual_skipped = sum(1 for r in results if r.predicted_answer is None)
        assert summary.skipped == manual_skipped

    @given(results=result_lists(min_size=1))
    def test_skipped_excluded_from_accuracy_denominator(self, results):
        """Skipped results don't deflate accuracy."""
        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        # Adding more skipped results shouldn't change accuracy
        # of the non-skipped portion
        non_skipped = [r for r in results if r.predicted_answer is not None]
        if non_skipped:
            correct_non_skipped = sum(1 for r in non_skipped if r.correct)
            expected = correct_non_skipped / len(non_skipped)
            assert abs(summary.accuracy - expected) < 1e-10


# ── Feature: Response time non-negativity ───────────────────────


@pytest.mark.property
class TestResponseTime:
    """Scenario: Average response time is non-negative."""

    @given(results=result_lists(min_size=1))
    def test_avg_response_time_non_negative(self, results):
        """avg_response_time_ms ≥ 0 for any result set."""
        # Ensure all times are non-negative
        from dataclasses import replace
        results = [replace(r, response_time_ms=abs(r.response_time_ms)) for r in results]

        evaluator = Evaluator(model="test")
        evaluator.results = results
        summary = evaluator._compute_summary("test")

        assert summary.avg_response_time_ms >= 0.0


# ── Feature: Serialization roundtrip ────────────────────────────


@pytest.mark.property
class TestEvaluationSerialization:
    """Scenario: EvaluationResult survives to_dict()."""

    @given(result=evaluation_results())
    def test_result_to_dict_contains_all_fields(self, result):
        """to_dict() includes all fields."""
        d = result.to_dict()
        assert "problem_id" in d
        assert "predicted_answer" in d
        assert "actual_answer" in d
        assert "correct" in d
        assert "response_time_ms" in d
        assert "model" in d
        assert d["problem_id"] == result.problem_id
        assert d["correct"] == result.correct
