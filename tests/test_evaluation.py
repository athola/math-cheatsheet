"""Tests for evaluation module."""

from evaluation import EvaluationResult, Evaluator


class TestAccuracyComputation:
    """Verify accuracy excludes skipped problems from the denominator."""

    def _make_evaluator_with_results(self, results):
        evaluator = Evaluator(model="test")
        evaluator.results = results
        return evaluator

    def test_accuracy_excludes_skipped(self):
        """Skipped problems (predicted=None) must not deflate accuracy."""
        evaluator = self._make_evaluator_with_results(
            [
                EvaluationResult(
                    problem_id=1,
                    equation_1_id=1,
                    equation_2_id=2,
                    predicted_answer=True,
                    actual_answer=True,
                    correct=True,
                    response_time_ms=1.0,
                    model="test",
                ),
                EvaluationResult(
                    problem_id=2,
                    equation_1_id=3,
                    equation_2_id=4,
                    predicted_answer=None,
                    actual_answer=True,
                    correct=False,
                    response_time_ms=1.0,
                    model="test",
                ),
            ]
        )
        summary = evaluator._compute_summary("test")
        # 1 correct out of 1 evaluated (skip the None prediction)
        assert summary.accuracy == 1.0

    def test_accuracy_all_skipped(self):
        """If all problems are skipped, accuracy should be 0.0."""
        evaluator = self._make_evaluator_with_results(
            [
                EvaluationResult(
                    problem_id=1,
                    equation_1_id=1,
                    equation_2_id=2,
                    predicted_answer=None,
                    actual_answer=True,
                    correct=False,
                    response_time_ms=1.0,
                    model="test",
                ),
            ]
        )
        summary = evaluator._compute_summary("test")
        assert summary.accuracy == 0.0

    def test_accuracy_no_skips(self):
        """When nothing is skipped, accuracy = correct / total."""
        evaluator = self._make_evaluator_with_results(
            [
                EvaluationResult(
                    problem_id=1,
                    equation_1_id=1,
                    equation_2_id=2,
                    predicted_answer=True,
                    actual_answer=True,
                    correct=True,
                    response_time_ms=1.0,
                    model="test",
                ),
                EvaluationResult(
                    problem_id=2,
                    equation_1_id=3,
                    equation_2_id=4,
                    predicted_answer=False,
                    actual_answer=True,
                    correct=False,
                    response_time_ms=1.0,
                    model="test",
                ),
            ]
        )
        summary = evaluator._compute_summary("test")
        assert summary.accuracy == 0.5

    def test_accuracy_mixed(self):
        """2 correct, 1 incorrect, 1 skipped => accuracy = 2/3."""
        evaluator = self._make_evaluator_with_results(
            [
                EvaluationResult(
                    problem_id=1,
                    equation_1_id=1,
                    equation_2_id=2,
                    predicted_answer=True,
                    actual_answer=True,
                    correct=True,
                    response_time_ms=1.0,
                    model="test",
                ),
                EvaluationResult(
                    problem_id=2,
                    equation_1_id=3,
                    equation_2_id=4,
                    predicted_answer=True,
                    actual_answer=True,
                    correct=True,
                    response_time_ms=1.0,
                    model="test",
                ),
                EvaluationResult(
                    problem_id=3,
                    equation_1_id=5,
                    equation_2_id=6,
                    predicted_answer=False,
                    actual_answer=True,
                    correct=False,
                    response_time_ms=1.0,
                    model="test",
                ),
                EvaluationResult(
                    problem_id=4,
                    equation_1_id=7,
                    equation_2_id=8,
                    predicted_answer=None,
                    actual_answer=None,
                    correct=False,
                    response_time_ms=1.0,
                    model="test",
                ),
            ]
        )
        summary = evaluator._compute_summary("test")
        assert abs(summary.accuracy - 2.0 / 3.0) < 1e-9

    def test_empty_results(self):
        """No results => accuracy 0.0, no division by zero."""
        evaluator = self._make_evaluator_with_results([])
        summary = evaluator._compute_summary("test")
        assert summary.accuracy == 0.0
        assert summary.total_problems == 0


class TestEvaluationSummaryFields:
    """Verify summary fields are computed correctly."""

    def test_summary_counts(self):
        evaluator = Evaluator(model="test")
        evaluator.results = [
            EvaluationResult(
                problem_id=i,
                equation_1_id=1,
                equation_2_id=2,
                predicted_answer=True,
                actual_answer=True,
                correct=True,
                response_time_ms=1.0,
                model="test",
            )
            for i in range(5)
        ]
        summary = evaluator._compute_summary("v1")
        assert summary.total_problems == 5
        assert summary.correct == 5
        assert summary.incorrect == 0
        assert summary.skipped == 0
        assert summary.accuracy == 1.0
