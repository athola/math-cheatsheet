#!/usr/bin/env python3
"""Accuracy error analyzer for the decision procedure.

Analyzes WHERE the decision procedure fails across the implication matrix.
Groups misclassifications by structural features to identify patterns
and suggest which phases to improve.

Usage:
    python scripts/analyze_errors.py [--output PATH] [--sample N]
    python scripts/analyze_errors.py --sample 10000 --output reports/errors.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from decision_procedure import DecisionProcedure, PredictionResult
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle


@dataclass(frozen=True)
class ErrorRecord:
    """A single misclassification.

    Frozen so an error list is structurally immutable once collected.
    ``error_type`` is Literal["FP", "FN"] to make the invariant explicit.
    """

    h_id: int
    t_id: int
    predicted: bool
    actual: bool
    phase: str
    error_type: Literal["FP", "FN"]
    h_depth: int
    t_depth: int
    h_vars: int
    t_vars: int
    new_vars_in_target: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ErrorReport:
    """Full error analysis report.

    Frozen so downstream consumers can't accidentally mutate the aggregated
    buckets. Internal dict/list fields remain mutable by Python semantics.
    """

    total_pairs: int
    total_errors: int
    fp_count: int
    fn_count: int
    by_phase: dict[str, int]
    by_error_type: dict[str, int]
    top_patterns: list[dict]
    phase_suggestions: list[str]
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_pairs": self.total_pairs,
                "total_errors": self.total_errors,
                "fp_count": self.fp_count,
                "fn_count": self.fn_count,
                "error_rate": self.total_errors / self.total_pairs if self.total_pairs > 0 else 0.0,
                "elapsed_seconds": self.elapsed_seconds,
            },
            "by_phase": self.by_phase,
            "by_error_type": self.by_error_type,
            "top_patterns": self.top_patterns,
            "phase_suggestions": self.phase_suggestions,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# Phase improvement suggestions keyed by phase name
_PHASE_SUGGESTIONS: dict[str, str] = {
    "P0-self": ("Phase 0 errors indicate a bug in self-implication detection."),
    "P1-taut-target": (
        "Phase 1 errors: review tautology target detection."
        " Some non-tautologies may be structurally equivalent to x=x."
    ),
    "P2-collapse": (
        "Phase 2 errors: collapse set from oracle may be incomplete"
        " or the hypothesis is only collapse-like (strong but not universal)."
    ),
    "P3-taut-hyp": (
        "Phase 3 errors: tautology hypothesis returning FALSE is too aggressive."
        " Some tautology-like equations may imply non-trivial targets."
    ),
    "P4-new-vars": (
        "Phase 4 errors: new-vars-in-target heuristic is too strict."
        " Some implications hold despite extra variables via variable merging."
    ),
    "P5-substitution": (
        "Phase 5 errors: substitution detection may miss multi-step"
        " or non-trivial specializations. Consider deeper unification."
    ),
    "P5a-equiv-class": (
        "Phase 5a errors: equivalence class lookup disagreed with ground truth."
        " The row-profile hash may be merging equations that actually differ"
        " on conjectured cells; re-check oracle value range."
    ),
    "P5b-structural": (
        "Phase 5b errors: structural TRUE via equation_analyzer overshot."
        " The delegated phase (shown in parens) flagged an implication that"
        " ground truth rejects; tighten that analyzer phase."
    ),
    "P5c-structural": (
        "Phase 5c errors: structural FALSE via equation_analyzer missed a TRUE."
        " The delegated counterexample/heuristic phase rejected an implication"
        " the matrix confirms; widen the analyzer's acceptance criteria."
    ),
    "P6-default": (
        "Phase 6 errors: the default FALSE catchall misses true implications."
        " This is the main area for new rules."
    ),
}


def _suggestion_for_phase(phase: str) -> str | None:
    """Look up a phase suggestion, tolerating dynamic parenthesised suffixes.

    Phases like ``P5b-structural(Phase 4b)`` embed the delegated analyzer phase
    in parentheses. The suggestion table is keyed on the bare prefix so those
    phases still resolve to a hint.
    """
    if phase in _PHASE_SUGGESTIONS:
        return _PHASE_SUGGESTIONS[phase]
    bare = phase.split("(", 1)[0]
    return _PHASE_SUGGESTIONS.get(bare)


class ErrorAnalyzer:
    """Analyze decision procedure errors across the implication matrix."""

    def __init__(
        self,
        proc: DecisionProcedure,
        oracle: ImplicationOracle,
        equations: ETPEquations,
    ):
        self.proc = proc
        self.oracle = oracle
        self.equations = equations

    def collect_errors(self, sample: int | None = None) -> list[ErrorRecord]:
        """Iterate all pairs (or a random sample) and collect misclassifications."""
        errors: list[ErrorRecord] = []
        collapse_ids = self.proc.collapse_ids

        pairs = self._random_pairs(sample) if sample is not None else self._all_pairs()

        for h_idx, t_idx, h_id, t_id in pairs:
            actual = self.oracle.decode_truth(int(self.oracle._matrix[h_idx, t_idx]))
            if actual is None:
                continue

            result: PredictionResult = self.proc.predict(h_id, t_id)

            if result.prediction == actual:
                continue

            error_type: Literal["FP", "FN"] = "FP" if result.prediction and not actual else "FN"

            h_depth, t_depth, h_vars, t_vars, new_vars = 0, 0, 1, 1, False

            if h_id in self.equations:
                h_eq = self.equations[h_id]
                h_depth = h_eq.max_depth
                h_vars = h_eq.var_count
            if t_id in self.equations:
                t_eq = self.equations[t_id]
                t_depth = t_eq.max_depth
                t_vars = t_eq.var_count
            if h_id in self.equations and t_id in self.equations:
                new_vars = len(self.equations.vars_in_target_not_in_hypothesis(h_id, t_id)) > 0

            errors.append(
                ErrorRecord(
                    h_id=h_id,
                    t_id=t_id,
                    predicted=result.prediction,
                    actual=actual,
                    phase=result.phase,
                    error_type=error_type,
                    h_depth=h_depth,
                    t_depth=t_depth,
                    h_vars=h_vars,
                    t_vars=t_vars,
                    new_vars_in_target=new_vars,
                )
            )

        return errors

    def _all_pairs(self):
        """Yield (h_idx, t_idx, h_id, t_id) for all pairs."""
        for i, h_id in enumerate(self.oracle._eq_ids):
            for j, t_id in enumerate(self.oracle._col_eq_ids):
                yield i, j, h_id, t_id

    def _random_pairs(self, n: int):
        """Yield n random (h_idx, t_idx, h_id, t_id) pairs."""
        n_rows = len(self.oracle._eq_ids)
        n_cols = len(self.oracle._col_eq_ids)
        seen: set[tuple[int, int]] = set()
        n = min(n, n_rows * n_cols)

        while len(seen) < n:
            i = random.randint(0, n_rows - 1)
            j = random.randint(0, n_cols - 1)
            if (i, j) not in seen:
                seen.add((i, j))
                yield i, j, self.oracle._eq_ids[i], self.oracle._col_eq_ids[j]

    def group_errors(self, errors: list[ErrorRecord], key: str) -> dict[str, list[ErrorRecord]]:
        """Group errors by an attribute, sorted by count descending."""
        groups: dict[str, list[ErrorRecord]] = defaultdict(list)
        for err in errors:
            groups[str(getattr(err, key))].append(err)
        return dict(sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True))

    def top_patterns(self, errors: list[ErrorRecord], n: int = 10) -> list[dict]:
        """Identify top-n feature combinations with highest error count.

        Buckets by: (error_type, phase, h_depth, t_depth, new_vars_in_target).
        """
        buckets: dict[tuple, list[ErrorRecord]] = defaultdict(list)
        for err in errors:
            buckets[(err.error_type, err.phase, err.h_depth, err.t_depth, err.new_vars_in_target)].append(err)

        total = len(errors) if errors else 1
        patterns = []
        for key, errs in sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True)[:n]:
            error_type, phase, h_depth, t_depth, new_vars = key
            example = errs[0]
            patterns.append(
                {
                    "bucket": {
                        "error_type": error_type,
                        "phase": phase,
                        "h_depth": h_depth,
                        "t_depth": t_depth,
                        "new_vars_in_target": new_vars,
                    },
                    "count": len(errs),
                    "pct_of_total": round(len(errs) / total * 100, 2),
                    "example": {"h_id": example.h_id, "t_id": example.t_id},
                    "suggestion": (
                        _suggestion_for_phase(phase)
                        or f"Investigate phase {phase} for improvement opportunities."
                    ),
                }
            )

        return patterns

    def generate_report(self, sample: int | None = None) -> ErrorReport:
        """Run full analysis and produce a structured report."""
        t0 = time.time()
        errors = self.collect_errors(sample=sample)
        elapsed = time.time() - t0

        fp_count = sum(1 for e in errors if e.error_type == "FP")
        fn_count = sum(1 for e in errors if e.error_type == "FN")

        total_pairs = (
            sample
            if sample is not None
            else len(self.oracle._eq_ids) * len(self.oracle._col_eq_ids)
        )

        by_phase_grouped = self.group_errors(errors, "phase")
        by_phase = {k: len(v) for k, v in by_phase_grouped.items()}

        patterns = self.top_patterns(errors, n=10)

        suggestions = [
            f"[{phase}] ({by_phase[phase]} errors): {msg}"
            for phase in by_phase
            if (msg := _suggestion_for_phase(phase)) is not None
        ]

        return ErrorReport(
            total_pairs=total_pairs,
            total_errors=len(errors),
            fp_count=fp_count,
            fn_count=fn_count,
            by_phase=by_phase,
            by_error_type={"FP": fp_count, "FN": fn_count},
            top_patterns=patterns,
            phase_suggestions=suggestions,
            elapsed_seconds=round(elapsed, 2),
        )

    def print_report(self, report: ErrorReport) -> None:
        """Print structured report to stdout."""
        print("=" * 70)
        print("  DECISION PROCEDURE ERROR ANALYSIS")
        print("=" * 70)

        s = report.to_dict()["summary"]
        print(f"\nTotal pairs evaluated: {s['total_pairs']:,}")
        print(f"Total errors:          {s['total_errors']:,}")
        print(f"Error rate:            {s['error_rate']:.4%}")
        print(f"  False positives:     {s['fp_count']:,}")
        print(f"  False negatives:     {s['fn_count']:,}")
        print(f"Time:                  {s['elapsed_seconds']:.1f}s")

        print(f"\n{'─' * 70}")
        print("ERRORS BY DECISION PHASE")
        print(f"{'─' * 70}")
        for phase, count in report.by_phase.items():
            pct = count / report.total_errors * 100 if report.total_errors > 0 else 0
            print(f"  {phase:<20s} {count:>8,} ({pct:5.1f}%)")

        print(f"\n{'─' * 70}")
        print("TOP ERROR PATTERNS")
        print(f"{'─' * 70}")
        for i, p in enumerate(report.top_patterns, 1):
            b = p["bucket"]
            print(f"\n  #{i}: {p['count']:,} errors ({p['pct_of_total']:.1f}% of total)")
            print(f"      Type: {b['error_type']}, Phase: {b['phase']}")
            print(f"      h_depth={b['h_depth']}, t_depth={b['t_depth']}, new_vars={b['new_vars_in_target']}")
            print(f"      Example: E{p['example']['h_id']} -> E{p['example']['t_id']}")

        print(f"\n{'─' * 70}")
        print("IMPROVEMENT SUGGESTIONS")
        print(f"{'─' * 70}")
        for suggestion in report.phase_suggestions:
            print(f"  {suggestion}")

        print(f"\n{'=' * 70}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze decision procedure errors across the implication matrix",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to save JSON report (default: stdout only)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Evaluate on N random pairs instead of full 22M",
    )
    parser.add_argument(
        "--equations",
        type=Path,
        default=PROJECT_ROOT / "research" / "data" / "etp" / "equations.txt",
        help="Path to equations.txt",
    )
    parser.add_argument(
        "--oracle",
        type=Path,
        default=PROJECT_ROOT / "research" / "data" / "etp" / "implications.csv",
        help="Path to implications.csv",
    )
    args = parser.parse_args()

    print("Loading data...")
    eqs = ETPEquations(args.equations)
    oracle = ImplicationOracle(args.oracle)
    proc = DecisionProcedure(eqs, oracle)

    print(f"Equations: {len(eqs)}")
    print(f"Matrix: {oracle.shape}")
    print(f"Collapse equations: {len(proc.collapse_ids)}")

    analyzer = ErrorAnalyzer(proc, oracle, eqs)

    if args.sample:
        print(f"\nAnalyzing {args.sample:,} random pairs...")
    else:
        total = oracle.shape[0] * oracle.shape[1]
        print(f"\nAnalyzing all {total:,} pairs...")

    report = analyzer.generate_report(sample=args.sample)
    analyzer.print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.to_json(), encoding="utf-8")
        print(f"\nJSON report saved to: {args.output}")


if __name__ == "__main__":
    main()
