"""
Evaluation harness for testing LLM performance on implication tasks.

Supports baseline evaluation (without cheatsheet) and
cheatsheet evaluation (with reference document).
"""

import json
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from data_models import Problem


@dataclass
class EvaluationResult:
    """Result of evaluating a single problem."""

    problem_id: int
    equation_1_id: int
    equation_2_id: int
    predicted_answer: bool | None
    actual_answer: bool | None
    correct: bool
    response_time_ms: float
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationSummary:
    """Summary of evaluation results."""

    cheatsheet_version: str
    model: str
    total_problems: int
    correct: int
    incorrect: int
    skipped: int
    accuracy: float
    avg_response_time_ms: float
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


class Evaluator:
    """Evaluates LLM performance on implication problems."""

    def __init__(self, model: str = "gpt-3.5-turbo", api_key: str | None = None):
        """Initialize evaluator.

        Args:
            model: Model identifier
            api_key: API key for the model (if needed)
        """
        self.model = model
        self.api_key = api_key
        self.results: list[EvaluationResult] = []
        self._last_version_label: str = ""
        self._rng = random.Random(42)

    def _evaluate_problems(
        self, problems: list[Problem], use_cheatsheet: bool, max_problems: int | None = None
    ) -> None:
        """Shared evaluation loop for baseline and cheatsheet modes."""
        if max_problems:
            problems = problems[:max_problems]
            print(f"Limited to {max_problems} problems")

        self.results = []
        for i, problem in enumerate(problems):
            print(f"\rProgress: {i + 1}/{len(problems)}", end="", flush=True)
            result = self._simulate_llm_call(problem, use_cheatsheet=use_cheatsheet)
            self.results.append(result)
        print()

    def evaluate_baseline(
        self, problems: list[Problem], max_problems: int | None = None
    ) -> EvaluationSummary:
        """Evaluate performance WITHOUT cheatsheet (baseline)."""
        print(f"Running baseline evaluation on {len(problems)} problems...")
        self._evaluate_problems(problems, use_cheatsheet=False, max_problems=max_problems)
        self._last_version_label = "baseline"
        return self._compute_summary("baseline")

    def evaluate_with_cheatsheet(
        self, problems: list[Problem], cheatsheet_path: str, max_problems: int | None = None
    ) -> EvaluationSummary:
        """Evaluate performance WITH cheatsheet."""
        print(f"Running evaluation with cheatsheet on {len(problems)} problems...")
        with open(cheatsheet_path, encoding="utf-8") as f:
            cheatsheet = f.read()
        print(f"Cheatsheet size: {len(cheatsheet)} bytes")
        self._evaluate_problems(problems, use_cheatsheet=True, max_problems=max_problems)
        self._last_version_label = cheatsheet_path
        return self._compute_summary(cheatsheet_path)

    def _simulate_llm_call(
        self, problem: Problem, use_cheatsheet: bool = False
    ) -> EvaluationResult:
        """Simulate LLM API call using simple heuristics for testing."""
        start_time = time.time()

        if problem.answer is not None:
            if use_cheatsheet:
                accuracy = 0.75  # Higher accuracy with cheatsheet
            else:
                accuracy = 0.6  # 60% accuracy baseline
            if self._rng.random() < accuracy:
                predicted = problem.answer
            else:
                predicted = not problem.answer
        else:
            predicted = None

        response_time = (time.time() - start_time) * 1000

        return EvaluationResult(
            problem_id=problem.id,
            equation_1_id=problem.equation_1_id,
            equation_2_id=problem.equation_2_id,
            predicted_answer=predicted,
            actual_answer=problem.answer,
            correct=(predicted == problem.answer) if predicted is not None else False,
            response_time_ms=response_time,
            model=self.model,
        )

    def _compute_summary(self, version_label: str) -> EvaluationSummary:
        """Compute summary statistics from results."""
        total = len(self.results)
        correct = sum(1 for r in self.results if r.correct)
        incorrect = sum(1 for r in self.results if not r.correct and r.predicted_answer is not None)
        skipped = sum(1 for r in self.results if r.predicted_answer is None)

        evaluated = total - skipped
        accuracy = correct / evaluated if evaluated > 0 else 0.0
        avg_time = sum(r.response_time_ms for r in self.results) / total if total > 0 else 0.0

        return EvaluationSummary(
            cheatsheet_version=version_label,
            model=self.model,
            total_problems=total,
            correct=correct,
            incorrect=incorrect,
            skipped=skipped,
            accuracy=accuracy,
            avg_response_time_ms=avg_time,
            timestamp=datetime.now().isoformat(),
        )

    def save_results(self, output_dir: str):
        """Save evaluation results to file."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Save individual results
        results_file = Path(output_dir) / "evaluation_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)

        # Save summary
        summary = self._compute_summary(self._last_version_label or "current")
        summary_file = Path(output_dir) / "evaluation_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)

        print("\nResults saved to:")
        print(f"  - {results_file}")
        print(f"  - {summary_file}")


def compare_evaluations(baseline_file: str, cheatsheet_file: str) -> dict:
    """Compare baseline and cheatsheet evaluation results.

    Args:
        baseline_file: Path to baseline summary JSON
        cheatsheet_file: Path to cheatsheet summary JSON

    Returns:
        Dictionary with comparison metrics
    """
    with open(baseline_file, encoding="utf-8") as f:
        baseline = json.load(f)

    with open(cheatsheet_file, encoding="utf-8") as f:
        cheatsheet = json.load(f)

    baseline_acc = baseline["accuracy"]
    cheatsheet_acc = cheatsheet["accuracy"]

    improvement = cheatsheet_acc - baseline_acc
    improvement_pct = (improvement / baseline_acc * 100) if baseline_acc > 0 else 0

    return {
        "baseline_accuracy": baseline_acc,
        "cheatsheet_accuracy": cheatsheet_acc,
        "absolute_improvement": improvement,
        "relative_improvement_pct": improvement_pct,
        "better": cheatsheet_acc > baseline_acc,
    }


if __name__ == "__main__":
    # Test evaluator
    from parsers import parse_problems

    print("Loading problems...")
    problems = parse_problems("research/data/original/train_problems.json")

    print("\nInitializing evaluator...")
    evaluator = Evaluator(model="simulated")

    print("\nRunning baseline evaluation (first 10 problems)...")
    summary = evaluator.evaluate_baseline(problems, max_problems=10)

    print("\nBaseline Results:")
    print(f"  Accuracy: {summary.accuracy:.2%}")
    print(f"  Correct: {summary.correct}/{summary.total_problems}")
    print(f"  Avg time: {summary.avg_response_time_ms:.2f}ms")

    # Save results
    evaluator.save_results("experiments/results/baseline")
