"""Tests for evaluation module."""

import json

import pytest

from data_models import Problem
from evaluation import EvaluationResult, EvaluationSummary, Evaluator, compare_evaluations

# ── Helpers ──────────────────────────────────────────────────────


def _result(pid=1, eq1=1, eq2=2, predicted=True, actual=True, correct=True, time_ms=1.0):
    return EvaluationResult(
        problem_id=pid,
        equation_1_id=eq1,
        equation_2_id=eq2,
        predicted_answer=predicted,
        actual_answer=actual,
        correct=correct,
        response_time_ms=time_ms,
        model="test",
    )


def _evaluator_with(results):
    ev = Evaluator(model="test")
    ev.results = list(results)
    return ev


def _make_problems(answers):
    """Create Problem objects with given answers."""
    return [
        Problem(id=i + 1, equation_1_id=1, equation_2_id=2, answer=a, difficulty="regular")
        for i, a in enumerate(answers)
    ]


# ── Dataclass serialization ─────────────────────────────────────


class TestEvaluationResultSerialization:
    def test_to_dict_roundtrip(self):
        r = _result(pid=42, eq1=10, eq2=20, time_ms=3.14)
        d = r.to_dict()
        assert d["problem_id"] == 42
        assert d["equation_1_id"] == 10
        assert d["equation_2_id"] == 20
        assert d["response_time_ms"] == pytest.approx(3.14)
        assert d["model"] == "test"
        assert d["prompt_tokens"] == 0
        assert d["completion_tokens"] == 0

    def test_to_dict_with_none_prediction(self):
        d = _result(predicted=None, correct=False).to_dict()
        assert d["predicted_answer"] is None


class TestEvaluationSummarySerialization:
    def test_to_dict(self):
        s = EvaluationSummary(
            cheatsheet_version="v1",
            model="test",
            total_problems=10,
            correct=8,
            incorrect=1,
            skipped=1,
            accuracy=0.89,
            avg_response_time_ms=2.5,
            timestamp="2024-01-01T00:00:00",
        )
        d = s.to_dict()
        assert d["cheatsheet_version"] == "v1"
        assert d["accuracy"] == pytest.approx(0.89)


# ── Accuracy computation ────────────────────────────────────────


class TestAccuracyComputation:
    """Verify accuracy excludes skipped problems from the denominator."""

    def test_accuracy_excludes_skipped(self):
        """Skipped problems (predicted=None) must not deflate accuracy."""
        ev = _evaluator_with(
            [
                _result(pid=1, correct=True),
                _result(pid=2, predicted=None, correct=False),
            ]
        )
        summary = ev._compute_summary("test")
        assert summary.accuracy == 1.0

    def test_accuracy_all_skipped(self):
        """If all problems are skipped, accuracy should be 0.0."""
        ev = _evaluator_with([_result(pid=1, predicted=None, correct=False)])
        summary = ev._compute_summary("test")
        assert summary.accuracy == 0.0

    def test_accuracy_no_skips(self):
        """When nothing is skipped, accuracy = correct / total."""
        ev = _evaluator_with(
            [
                _result(pid=1, correct=True),
                _result(pid=2, predicted=False, actual=True, correct=False),
            ]
        )
        summary = ev._compute_summary("test")
        assert summary.accuracy == 0.5

    def test_accuracy_mixed(self):
        """2 correct, 1 incorrect, 1 skipped => accuracy = 2/3."""
        ev = _evaluator_with(
            [
                _result(pid=1, correct=True),
                _result(pid=2, correct=True),
                _result(pid=3, predicted=False, actual=True, correct=False),
                _result(pid=4, predicted=None, actual=None, correct=False),
            ]
        )
        summary = ev._compute_summary("test")
        assert abs(summary.accuracy - 2.0 / 3.0) < 1e-9

    def test_empty_results(self):
        """No results => accuracy 0.0, no division by zero."""
        ev = _evaluator_with([])
        summary = ev._compute_summary("test")
        assert summary.accuracy == 0.0
        assert summary.total_problems == 0


class TestEvaluationSummaryFields:
    """Verify summary fields are computed correctly."""

    def test_summary_counts(self):
        ev = _evaluator_with([_result(pid=i) for i in range(5)])
        summary = ev._compute_summary("v1")
        assert summary.total_problems == 5
        assert summary.correct == 5
        assert summary.incorrect == 0
        assert summary.skipped == 0
        assert summary.accuracy == 1.0

    def test_avg_response_time(self):
        ev = _evaluator_with(
            [
                _result(pid=1, time_ms=10.0),
                _result(pid=2, time_ms=20.0),
            ]
        )
        summary = ev._compute_summary("test")
        assert summary.avg_response_time_ms == pytest.approx(15.0)

    def test_summary_has_timestamp(self):
        ev = _evaluator_with([_result()])
        summary = ev._compute_summary("test")
        assert summary.timestamp  # non-empty ISO timestamp


# ── Simulate LLM call ───────────────────────────────────────────


class TestSimulateLlmCall:
    def test_known_answer_returns_prediction(self):
        ev = Evaluator(model="test")
        problem = Problem(id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty="regular")
        result = ev._simulate_llm_call(problem, use_cheatsheet=False)
        assert result.predicted_answer in (True, False)
        assert result.model == "test"
        assert result.response_time_ms >= 0

    def test_none_answer_returns_none_prediction(self):
        ev = Evaluator(model="test")
        problem = Problem(id=1, equation_1_id=1, equation_2_id=2, answer=None, difficulty="regular")
        result = ev._simulate_llm_call(problem)
        assert result.predicted_answer is None
        assert result.correct is False

    def test_cheatsheet_mode_flag(self):
        """Cheatsheet and baseline modes both produce results."""
        ev = Evaluator(model="test")
        p = Problem(id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty="regular")
        r1 = ev._simulate_llm_call(p, use_cheatsheet=False)
        r2 = ev._simulate_llm_call(p, use_cheatsheet=True)
        assert isinstance(r1.predicted_answer, bool)
        assert isinstance(r2.predicted_answer, bool)


# ── Evaluate problems pipeline ──────────────────────────────────


class TestEvaluateProblems:
    def test_evaluate_problems_stores_results(self):
        ev = Evaluator(model="test")
        problems = _make_problems([True, False, True])
        ev._evaluate_problems(problems, use_cheatsheet=False)
        assert len(ev.results) == 3

    def test_max_problems_limits_evaluation(self):
        ev = Evaluator(model="test")
        problems = _make_problems([True] * 10)
        ev._evaluate_problems(problems, use_cheatsheet=False, max_problems=3)
        assert len(ev.results) == 3


# ── Baseline & cheatsheet evaluation ────────────────────────────


class TestEvaluateBaseline:
    def test_returns_summary(self):
        ev = Evaluator(model="test")
        problems = _make_problems([True, False])
        summary = ev.evaluate_baseline(problems, max_problems=2)
        assert summary.total_problems == 2
        assert summary.cheatsheet_version == "baseline"
        assert summary.model == "test"


class TestEvaluateWithCheatsheet:
    def test_reads_cheatsheet_and_evaluates(self, tmp_path):
        cs = tmp_path / "cs.txt"
        cs.write_text("test cheatsheet content")
        ev = Evaluator(model="test")
        problems = _make_problems([True, False])
        summary = ev.evaluate_with_cheatsheet(problems, str(cs), max_problems=2)
        assert summary.total_problems == 2
        assert summary.cheatsheet_version == str(cs)


# ── Save results ────────────────────────────────────────────────


class TestSaveResults:
    def test_saves_json_files(self, tmp_path):
        ev = Evaluator(model="test")
        ev.results = [_result(pid=1), _result(pid=2)]
        ev._last_version_label = "v1"
        ev.save_results(str(tmp_path / "output"))

        results_file = tmp_path / "output" / "evaluation_results.json"
        summary_file = tmp_path / "output" / "evaluation_summary.json"
        assert results_file.exists()
        assert summary_file.exists()

        results_data = json.loads(results_file.read_text())
        assert len(results_data) == 2

        summary_data = json.loads(summary_file.read_text())
        assert summary_data["total_problems"] == 2
        assert summary_data["cheatsheet_version"] == "v1"

    def test_creates_output_directory(self, tmp_path):
        ev = Evaluator(model="test")
        ev.results = [_result()]
        nested = tmp_path / "deep" / "nested" / "dir"
        ev.save_results(str(nested))
        assert (nested / "evaluation_results.json").exists()


# ── Compare evaluations ─────────────────────────────────────────


class TestCompareEvaluations:
    def test_comparison_metrics(self, tmp_path):
        baseline = {"accuracy": 0.6, "model": "test"}
        cheatsheet = {"accuracy": 0.8, "model": "test"}

        bf = tmp_path / "baseline.json"
        cf = tmp_path / "cheatsheet.json"
        bf.write_text(json.dumps(baseline))
        cf.write_text(json.dumps(cheatsheet))

        result = compare_evaluations(str(bf), str(cf))
        assert result["baseline_accuracy"] == 0.6
        assert result["cheatsheet_accuracy"] == 0.8
        assert result["absolute_improvement"] == pytest.approx(0.2)
        assert result["relative_improvement_pct"] == pytest.approx(100 * 0.2 / 0.6)
        assert result["better"] is True

    def test_no_improvement(self, tmp_path):
        data = {"accuracy": 0.5}
        bf = tmp_path / "b.json"
        cf = tmp_path / "c.json"
        bf.write_text(json.dumps(data))
        cf.write_text(json.dumps(data))

        result = compare_evaluations(str(bf), str(cf))
        assert result["absolute_improvement"] == 0.0
        assert result["better"] is False

    def test_zero_baseline_accuracy(self, tmp_path):
        bf = tmp_path / "b.json"
        cf = tmp_path / "c.json"
        bf.write_text(json.dumps({"accuracy": 0.0}))
        cf.write_text(json.dumps({"accuracy": 0.5}))

        result = compare_evaluations(str(bf), str(cf))
        assert result["relative_improvement_pct"] == 0  # guarded against div-by-zero
