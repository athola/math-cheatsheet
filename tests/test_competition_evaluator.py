"""Tests for CompetitionEvaluator.

Uses small synthetic fixtures (5x5 matrix) for fast tests.
Real 22M evaluation tests are marked @pytest.mark.slow.
"""

import csv
import json
from pathlib import Path

import pytest

import competition_evaluator as ce
from competition_evaluator import (
    ComparisonReport,
    CompetitionEvaluator,
    EvalResult,
    build_parser,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def equations_file(tmp_path: Path) -> Path:
    """Create a small equations file (5 equations).

    Line N = Equation N:
      1: x = x         (tautology)
      2: x = y         (collapse: forces |M|=1)
      3: x ◇ y = y ◇ x (commutativity, 2 vars)
      4: x ◇ y = x     (left projection, 2 vars)
      5: x ◇ y = z     (has new var z, 3 vars)
    """
    eq_path = tmp_path / "equations.txt"
    eq_path.write_text(
        "x = x\nx = y\nx ◇ y = y ◇ x\nx ◇ y = x\nx ◇ y = z\n",
        encoding="utf-8",
    )
    return eq_path


@pytest.fixture
def oracle_csv(tmp_path: Path) -> Path:
    """Create a 5x5 implication matrix.

    Encodes:
      Eq1 (tautology): implies only itself
      Eq2 (collapse): implies everything
      Eq3 (commutative): implies 1, 3
      Eq4 (projection): implies 1, 4
      Eq5 (3-var): implies 1, 2, 5 (collapse-like)
    """
    csv_path = tmp_path / "implications.csv"
    matrix = [
        [3, -3, -3, -3, -3],  # Eq1: tautology
        [3, 3, 3, 3, 3],  # Eq2: collapse
        [3, -3, 3, -3, -3],  # Eq3
        [3, -3, -3, 3, -3],  # Eq4
        [3, 3, -3, -3, 3],  # Eq5
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in matrix:
            writer.writerow(row)
    return csv_path


@pytest.fixture
def evaluator(equations_file: Path, oracle_csv: Path) -> CompetitionEvaluator:
    return CompetitionEvaluator(str(equations_file), str(oracle_csv))


@pytest.fixture
def competition_file(tmp_path: Path) -> Path:
    """Create a small JSONL competition problem file."""
    problems = [
        {"hypothesis_id": 2, "target_id": 3, "answer": True},
        {"hypothesis_id": 3, "target_id": 4, "answer": False},
        {"hypothesis_id": 1, "target_id": 3, "answer": False},
        {"hypothesis_id": 4, "target_id": 1, "answer": True},
        {"hypothesis_id": 3, "target_id": 2, "answer": False},
    ]
    path = tmp_path / "test_problems.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p) + "\n")
    return path


@pytest.fixture
def synthetic_json_file(tmp_path: Path) -> Path:
    """Create a small synthetic_problems.json file (list format)."""
    problems = [
        {
            "id": 1,
            "equation_1_id": 2,
            "equation_2_id": 3,
            "answer": True,
            "difficulty": "normal",
        },
        {
            "id": 2,
            "equation_1_id": 3,
            "equation_2_id": 4,
            "answer": False,
            "difficulty": "normal",
        },
        {
            "id": 3,
            "equation_1_id": 1,
            "equation_2_id": 3,
            "answer": False,
            "difficulty": "hard",
        },
    ]
    path = tmp_path / "synthetic_problems.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(problems, f)
    return path


# ---------------------------------------------------------------------------
# EvalResult
# ---------------------------------------------------------------------------


class TestEvalResult:
    def test_from_counts_basic(self):
        result = EvalResult.from_counts(tp=10, fp=2, tn=80, fn=8, elapsed_seconds=1.5)
        assert result.total == 100
        assert result.accuracy == pytest.approx(0.90)
        assert result.precision == pytest.approx(10 / 12)
        assert result.recall == pytest.approx(10 / 18)
        assert result.elapsed_seconds == 1.5

    def test_from_counts_all_correct(self):
        result = EvalResult.from_counts(tp=50, fp=0, tn=50, fn=0, elapsed_seconds=0.1)
        assert result.accuracy == pytest.approx(1.0)
        assert result.precision == pytest.approx(1.0)
        assert result.recall == pytest.approx(1.0)

    def test_from_counts_zero_positives(self):
        result = EvalResult.from_counts(tp=0, fp=0, tn=100, fn=0, elapsed_seconds=0.1)
        assert result.accuracy == pytest.approx(1.0)
        assert result.precision == 0.0  # no positive predictions
        assert result.recall == 0.0  # no actual positives

    def test_from_counts_zero_total(self):
        result = EvalResult.from_counts(tp=0, fp=0, tn=0, fn=0, elapsed_seconds=0.0)
        assert result.accuracy == 0.0
        assert result.total == 0

    def test_confusion_matrix_structure(self):
        result = EvalResult.from_counts(tp=5, fp=3, tn=7, fn=2, elapsed_seconds=0.5)
        cm = result.confusion_matrix
        assert cm["predicted_true"]["actual_true"] == 5
        assert cm["predicted_true"]["actual_false"] == 3
        assert cm["predicted_false"]["actual_true"] == 2
        assert cm["predicted_false"]["actual_false"] == 7

    def test_f1_score(self):
        result = EvalResult.from_counts(tp=10, fp=2, tn=80, fn=8, elapsed_seconds=1.0)
        expected_f1 = 2 * result.precision * result.recall / (result.precision + result.recall)
        assert result.f1 == pytest.approx(expected_f1)

    def test_f1_zero_when_no_predictions(self):
        result = EvalResult.from_counts(tp=0, fp=0, tn=100, fn=0, elapsed_seconds=0.1)
        assert result.f1 == 0.0


# ---------------------------------------------------------------------------
# evaluate_full_matrix
# ---------------------------------------------------------------------------


class TestEvaluateFullMatrix:
    def test_returns_eval_result(self, evaluator: CompetitionEvaluator):
        result = evaluator.evaluate_full_matrix()
        assert isinstance(result, EvalResult)

    def test_total_matches_matrix_size(self, evaluator: CompetitionEvaluator):
        result = evaluator.evaluate_full_matrix()
        # 5x5 matrix = 25 cells, all should be evaluated (all 3 or -3)
        assert result.total == 25

    def test_accuracy_is_reasonable(self, evaluator: CompetitionEvaluator):
        result = evaluator.evaluate_full_matrix()
        # With a 5x5 test matrix the procedure should do well
        assert result.accuracy > 0.5

    def test_counts_sum_to_total(self, evaluator: CompetitionEvaluator):
        result = evaluator.evaluate_full_matrix()
        assert result.tp + result.fp + result.tn + result.fn == result.total

    def test_elapsed_time_recorded(self, evaluator: CompetitionEvaluator):
        result = evaluator.evaluate_full_matrix()
        assert result.elapsed_seconds >= 0.0

    def test_phase_breakdown_present(self, evaluator: CompetitionEvaluator):
        result = evaluator.evaluate_full_matrix()
        assert result.phase_breakdown is not None
        # At minimum P0-self should be present (diagonal)
        assert "P0-self" in result.phase_breakdown


# ---------------------------------------------------------------------------
# evaluate_competition_problems
# ---------------------------------------------------------------------------


class TestEvaluateCompetitionProblems:
    def test_returns_eval_result(self, evaluator: CompetitionEvaluator, competition_file: Path):
        result = evaluator.evaluate_competition_problems(str(competition_file))
        assert isinstance(result, EvalResult)

    def test_total_matches_problem_count(
        self, evaluator: CompetitionEvaluator, competition_file: Path
    ):
        result = evaluator.evaluate_competition_problems(str(competition_file))
        assert result.total == 5

    def test_counts_sum_to_total(self, evaluator: CompetitionEvaluator, competition_file: Path):
        result = evaluator.evaluate_competition_problems(str(competition_file))
        assert result.tp + result.fp + result.tn + result.fn == result.total

    def test_handles_json_format(self, evaluator: CompetitionEvaluator, synthetic_json_file: Path):
        """Should handle both JSONL and JSON array format."""
        result = evaluator.evaluate_competition_problems(str(synthetic_json_file))
        assert result.total == 3


# ---------------------------------------------------------------------------
# evaluate_by_category
# ---------------------------------------------------------------------------


class TestEvaluateByCategory:
    def test_returns_dict_of_eval_results(self, evaluator: CompetitionEvaluator):
        categories = evaluator.evaluate_by_category()
        assert isinstance(categories, dict)
        for key, val in categories.items():
            assert isinstance(key, str)
            assert isinstance(val, EvalResult)

    def test_categories_cover_all_pairs(self, evaluator: CompetitionEvaluator):
        categories = evaluator.evaluate_by_category()
        total = sum(er.total for er in categories.values())
        # Should cover all 25 pairs in 5x5 matrix
        assert total == 25

    def test_known_categories_present(self, evaluator: CompetitionEvaluator):
        categories = evaluator.evaluate_by_category()
        # Our small test set has collapse (eq2) and tautology (eq1)
        category_names = set(categories.keys())
        # At least "collapse" should be there since eq2 is collapse
        assert "collapse" in category_names

    def test_per_category_timing_is_measured_not_averaged(
        self, evaluator: CompetitionEvaluator, monkeypatch: pytest.MonkeyPatch
    ):
        """elapsed_seconds per category must reflect actual work in that category.

        Regression test for #45: previously elapsed was computed as
        ``total / n_categories`` so every category got the same number regardless
        of size. Using a monotonic counter clock, we verify the recorded times
        track distinct call counts, not an even division.
        """
        tick = {"n": 0}

        def fake_time() -> float:
            tick["n"] += 1
            return float(tick["n"])

        monkeypatch.setattr(ce.time, "time", fake_time)
        categories = evaluator.evaluate_by_category()
        times = sorted(r.elapsed_seconds for r in categories.values())
        # With the fake clock, every elapsed reading is a positive integer count
        # of clock ticks. An averaged implementation would produce identical
        # fractional values across all categories; a measured implementation
        # yields at least one category with a different integer count.
        assert any(t != times[0] for t in times), (
            "All per-category times identical under monotonic fake clock"
            " — implementation is averaging, not measuring."
        )


# ---------------------------------------------------------------------------
# compare_versions
# ---------------------------------------------------------------------------


class TestCompareVersions:
    def test_compare_two_results(self):
        r1 = EvalResult.from_counts(tp=80, fp=5, tn=10, fn=5, elapsed_seconds=1.0)
        r2 = EvalResult.from_counts(tp=85, fp=3, tn=10, fn=2, elapsed_seconds=0.8)
        report = CompetitionEvaluator.compare_versions([("v1", r1), ("v2", r2)])
        assert isinstance(report, ComparisonReport)
        assert len(report.results) == 2
        assert report.best_version == "v2"

    def test_compare_single_result(self):
        r1 = EvalResult.from_counts(tp=50, fp=5, tn=40, fn=5, elapsed_seconds=1.0)
        report = CompetitionEvaluator.compare_versions([("only", r1)])
        assert report.best_version == "only"

    def test_compare_identifies_best_accuracy(self):
        low = EvalResult.from_counts(tp=50, fp=10, tn=30, fn=10, elapsed_seconds=2.0)
        high = EvalResult.from_counts(tp=90, fp=2, tn=5, fn=3, elapsed_seconds=1.0)
        report = CompetitionEvaluator.compare_versions([("low", low), ("high", high)])
        assert report.best_version == "high"


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCLIParsing:
    def test_default_mode_is_full(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.mode == "full"

    def test_competition_mode(self):
        parser = build_parser()
        args = parser.parse_args(["--mode", "competition", "--problems", "test.jsonl"])
        assert args.mode == "competition"
        assert args.problems == "test.jsonl"

    def test_compare_mode(self):
        parser = build_parser()
        args = parser.parse_args(["--mode", "compare"])
        assert args.mode == "compare"

    def test_custom_data_paths(self):
        parser = build_parser()
        args = parser.parse_args(["--equations", "eq.txt", "--oracle", "impl.csv"])
        assert args.equations == "eq.txt"
        assert args.oracle == "impl.csv"


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


class TestReportFormatting:
    def test_eval_result_report_string(self):
        result = EvalResult.from_counts(tp=10, fp=2, tn=80, fn=8, elapsed_seconds=1.5)
        report = result.report()
        assert "Accuracy" in report
        assert "Precision" in report
        assert "Recall" in report
        assert "F1" in report
        assert "TP" in report

    def test_comparison_report_string(self):
        r1 = EvalResult.from_counts(tp=80, fp=5, tn=10, fn=5, elapsed_seconds=1.0)
        r2 = EvalResult.from_counts(tp=85, fp=3, tn=10, fn=2, elapsed_seconds=0.8)
        report = CompetitionEvaluator.compare_versions([("v1", r1), ("v2", r2)])
        text = report.report()
        assert "v1" in text
        assert "v2" in text
        assert "Best" in text
