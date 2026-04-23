"""Competition evaluator for the decision procedure.

Evaluates the DecisionProcedure against:
- The full 22M implication matrix (batch mode)
- Competition problem sets (JSONL / JSON files)
- Breakdown by equation category

Reports accuracy, precision, recall, F1, and confusion matrix.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from decision_procedure import DecisionProcedure
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle
from metrics_utils import update_confusion


@dataclass(frozen=True)
class EvalResult:
    """Evaluation result with standard classification metrics.

    Frozen (#43/I4) so consumer code cannot mutate metrics after a report is
    produced. Prefer :meth:`from_counts` — the bare constructor requires every
    derived metric (accuracy, precision, recall, f1, confusion_matrix) to be
    supplied consistently, which is easy to get wrong (#43/S3).
    """

    accuracy: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int
    total: int
    confusion_matrix: dict
    elapsed_seconds: float
    phase_breakdown: dict[str, dict] | None = None

    @classmethod
    def from_counts(
        cls,
        tp: int,
        fp: int,
        tn: int,
        fn: int,
        elapsed_seconds: float,
        phase_breakdown: dict[str, dict] | None = None,
    ) -> EvalResult:
        """Build an EvalResult from raw confusion matrix counts."""
        total = tp + fp + tn + fn
        accuracy = (tp + tn) / total if total > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        confusion_matrix = {
            "predicted_true": {"actual_true": tp, "actual_false": fp},
            "predicted_false": {"actual_true": fn, "actual_false": tn},
        }
        return cls(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            total=total,
            confusion_matrix=confusion_matrix,
            elapsed_seconds=elapsed_seconds,
            phase_breakdown=phase_breakdown,
        )

    def report(self) -> str:
        """Format a human-readable report."""
        lines = [
            "Evaluation Results",
            "=" * 50,
            f"  Total pairs:  {self.total:,}",
            f"  Accuracy:     {self.accuracy:.4f}  ({self.accuracy:.2%})",
            f"  Precision:    {self.precision:.4f}",
            f"  Recall:       {self.recall:.4f}",
            f"  F1:           {self.f1:.4f}",
            "",
            "Confusion Matrix:",
            f"  TP={self.tp:,}  FP={self.fp:,}",
            f"  FN={self.fn:,}  TN={self.tn:,}",
            f"  Time: {self.elapsed_seconds:.2f}s",
        ]
        if self.phase_breakdown:
            lines.append("")
            lines.append("Phase Breakdown:")
            for phase, stats in sorted(self.phase_breakdown.items()):
                total_p = stats.get("total", 0)
                acc = stats.get("accuracy", 0.0)
                lines.append(f"  {phase:30s}  n={total_p:>8,}  acc={acc:.4f}")
        return "\n".join(lines)


@dataclass
class ComparisonReport:
    """Comparison of multiple evaluation runs."""

    results: list[tuple[str, EvalResult]]
    best_version: str

    def report(self) -> str:
        """Format a human-readable comparison report."""
        lines = [
            "Version Comparison",
            "=" * 60,
        ]
        for name, r in self.results:
            lines.append(
                f"  {name:20s}  acc={r.accuracy:.4f}  prec={r.precision:.4f}"
                f"  rec={r.recall:.4f}  f1={r.f1:.4f}  ({r.elapsed_seconds:.1f}s)"
            )
        lines.append("")
        lines.append(f"Best: {self.best_version}")
        return "\n".join(lines)


class CompetitionEvaluator:
    """Evaluate the decision procedure against oracle and competition data."""

    def __init__(self, equations_path: str, oracle_path: str):
        self.equations = ETPEquations(equations_path)
        self.oracle = ImplicationOracle(oracle_path)
        self.procedure = DecisionProcedure(self.equations, self.oracle)

    def evaluate_full_matrix(self) -> EvalResult:
        """Evaluate against the full implication matrix with phase breakdown."""
        t0 = time.time()

        global_counts: dict[str, int] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        phase_stats: dict[str, dict] = {}

        for i, h_id in enumerate(self.oracle._eq_ids):
            for j, t_id in enumerate(self.oracle._col_eq_ids):
                actual = self.oracle.decode_truth(int(self.oracle._matrix[i, j]))
                if actual is None:
                    continue

                result = self.procedure.predict(h_id, t_id)
                predicted = result.prediction
                phase = result.phase

                update_confusion(global_counts, predicted, actual)

                if phase not in phase_stats:
                    phase_stats[phase] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0}
                ps = phase_stats[phase]
                ps["total"] += 1
                update_confusion(ps, predicted, actual)

        # Compute per-phase accuracy
        for ps in phase_stats.values():
            correct = ps["tp"] + ps["tn"]
            ps["accuracy"] = correct / ps["total"] if ps["total"] > 0 else 0.0

        elapsed = time.time() - t0
        return EvalResult.from_counts(
            tp=global_counts["tp"],
            fp=global_counts["fp"],
            tn=global_counts["tn"],
            fn=global_counts["fn"],
            elapsed_seconds=elapsed,
            phase_breakdown=phase_stats,
        )

    def evaluate_competition_problems(self, problems_path: str) -> EvalResult:
        """Evaluate against a JSONL or JSON competition problem file.

        Supports two formats:
        - JSONL: one JSON object per line with hypothesis_id, target_id, answer
        - JSON array: list of objects with equation_1_id, equation_2_id, answer
        """
        path = Path(problems_path)
        problems = _load_problems(path)

        t0 = time.time()
        counts: dict[str, int] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}

        for prob in problems:
            h_id = prob["hypothesis_id"]
            t_id = prob["target_id"]
            actual = prob["answer"]
            predicted = self.procedure.predict_bool(h_id, t_id)
            update_confusion(counts, predicted, actual)

        elapsed = time.time() - t0
        return EvalResult.from_counts(
            tp=counts["tp"],
            fp=counts["fp"],
            tn=counts["tn"],
            fn=counts["fn"],
            elapsed_seconds=elapsed,
        )

    def evaluate_by_category(self) -> dict[str, EvalResult]:
        """Evaluate full matrix, broken down by hypothesis equation category.

        Categories come from oracle.classify(): collapse, tautology, weak, mid, strong.

        Per-category ``elapsed_seconds`` is measured directly by summing the
        wall-clock span each hypothesis row takes, so categories of different
        sizes surface their real cost rather than an average.
        """
        category_counts: dict[str, dict[str, int]] = {}
        category_elapsed: dict[str, float] = {}

        for i, h_id in enumerate(self.oracle._eq_ids):
            cat = self.oracle.classify(h_id)

            if cat not in category_counts:
                category_counts[cat] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
                category_elapsed[cat] = 0.0

            row_start = time.time()
            for j, t_id in enumerate(self.oracle._col_eq_ids):
                actual = self.oracle.decode_truth(int(self.oracle._matrix[i, j]))
                if actual is None:
                    continue

                predicted = self.procedure.predict_bool(h_id, t_id)
                update_confusion(category_counts[cat], predicted, actual)
            category_elapsed[cat] += time.time() - row_start

        results: dict[str, EvalResult] = {}
        for cat, counts in category_counts.items():
            results[cat] = EvalResult.from_counts(
                tp=counts["tp"],
                fp=counts["fp"],
                tn=counts["tn"],
                fn=counts["fn"],
                elapsed_seconds=category_elapsed[cat],
            )
        return results

    @staticmethod
    def compare_versions(
        labeled_results: list[tuple[str, EvalResult]],
    ) -> ComparisonReport:
        """Compare multiple evaluation results and identify the best."""
        if not labeled_results:
            raise ValueError("Need at least one result to compare")

        best_name = max(labeled_results, key=lambda x: x[1].accuracy)[0]
        return ComparisonReport(results=labeled_results, best_version=best_name)


def _load_problems(path: Path) -> list[dict]:
    """Load problems from JSONL or JSON format, normalizing field names."""
    content = path.read_text(encoding="utf-8").strip()

    # Try JSON array first
    if content.startswith("["):
        raw = json.loads(content)
    else:
        # JSONL: one JSON object per line
        raw = []
        for line in content.splitlines():
            line = line.strip()
            if line:
                raw.append(json.loads(line))

    # Normalize field names
    problems = []
    for obj in raw:
        prob: dict = {}
        h = obj.get("hypothesis_id")
        prob["hypothesis_id"] = h if h is not None else obj.get("equation_1_id")
        t = obj.get("target_id")
        prob["target_id"] = t if t is not None else obj.get("equation_2_id")
        prob["answer"] = obj["answer"]
        problems.append(prob)
    return problems


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Evaluate the decision procedure against oracle and competition data"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "competition", "compare"],
        default="full",
        help="Evaluation mode (default: full)",
    )
    parser.add_argument(
        "--equations",
        default="research/data/etp/equations.txt",
        help="Path to equations file",
    )
    parser.add_argument(
        "--oracle",
        default="research/data/etp/implications.csv",
        help="Path to implication matrix CSV",
    )
    parser.add_argument(
        "--problems",
        default=None,
        help="Path to competition problems file (JSONL or JSON)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    print("Loading data...")
    evaluator = CompetitionEvaluator(args.equations, args.oracle)
    print(f"  Equations: {len(evaluator.equations)}")
    print(f"  Collapse:  {len(evaluator.procedure.collapse_ids)}")

    if args.mode == "full":
        print("\nEvaluating full matrix...")
        result = evaluator.evaluate_full_matrix()
        print(result.report())

        print("\n\nCategory breakdown:")
        print("=" * 60)
        categories = evaluator.evaluate_by_category()
        for cat, cat_result in sorted(categories.items()):
            print(
                f"  {cat:12s}  n={cat_result.total:>8,}  "
                f"acc={cat_result.accuracy:.4f}  "
                f"prec={cat_result.precision:.4f}  "
                f"rec={cat_result.recall:.4f}"
            )

    elif args.mode == "competition":
        if not args.problems:
            # Try default paths
            default_paths = [
                "research/data/etp/competition/normal.jsonl",
                "research/data/etp/competition/hard.jsonl",
                "research/data/etp/competition/synthetic_problems.json",
            ]
            for p in default_paths:
                if Path(p).exists():
                    print(f"\nEvaluating: {p}")
                    result = evaluator.evaluate_competition_problems(p)
                    print(result.report())
                    print()
        else:
            result = evaluator.evaluate_competition_problems(args.problems)
            print(result.report())

    elif args.mode == "compare":
        print("\nRunning full matrix evaluation for comparison...")
        result = evaluator.evaluate_full_matrix()
        report = CompetitionEvaluator.compare_versions([("current", result)])
        print(report.report())


if __name__ == "__main__":
    main()
