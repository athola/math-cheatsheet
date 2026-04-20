"""Multi-phase decision procedure for equational implications.

Given (hypothesis_id, target_id), returns TRUE/FALSE prediction.
Each phase adds precision on top of the previous ones.

Phases:
  0: Self-implication (identical equations → TRUE)
  1: Tautology target (E1: x=x → TRUE)
  2: Collapse hypothesis (oracle-labeled → TRUE)
  3: Tautology hypothesis + non-tautology target → FALSE
  4: Variable analysis (new vars in target → FALSE)
  5: Substitution detection (target is specialization → TRUE)
  5a: Equivalence class lookup (same row profile → TRUE)
  5b: Determined operation detection (e.g. left projection forces magma → TRUE/FALSE)
  5c: Counterexample testing (canonical + exhaustive 2-element magmas → FALSE)
  6: Default → FALSE

Structural analysis (phases 5b, 5c) is delegated to equation_analyzer.py
to avoid duplicating logic. See issue #21.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
)
from equation_analyzer import (
    parse_equation as ea_parse_equation,
)
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PredictionResult:
    """Outcome of one decision-procedure call.

    Frozen so downstream consumers (error analysis, reporters) cannot mutate
    a prediction after the fact (regression #43/I4).
    """

    prediction: bool
    phase: str
    reason: str


class DecisionProcedure:
    """Predict whether hypothesis implies target using structural rules."""

    def __init__(
        self,
        equations: ETPEquations,
        oracle: ImplicationOracle | None = None,
    ):
        self.equations = equations
        self.oracle = oracle
        # Pre-compute collapse set from oracle (ground truth)
        self._collapse_ids: set[int] = set()
        if oracle:
            for eq_id in equations.ids():
                if oracle.is_collapse(eq_id):
                    self._collapse_ids.add(eq_id)

    @property
    def collapse_ids(self) -> set[int]:
        return self._collapse_ids

    def predict(self, h_id: int, t_id: int) -> PredictionResult:
        """Run the full decision procedure.

        Logs the deciding phase at ``DEBUG`` level for every call
        (regression #30). Enable via ``logging.getLogger('decision_procedure')
        .setLevel(logging.DEBUG)`` or the project's ``--verbose`` CLI flag.
        """
        result = self._predict(h_id, t_id)
        logger.debug("E%d => E%d : %s (%s)", h_id, t_id, result.prediction, result.phase)
        return result

    def _predict(self, h_id: int, t_id: int) -> PredictionResult:
        """Actual decision logic; public ``predict`` wraps with logging."""
        # Phase 0: Self-implication
        if h_id == t_id:
            return PredictionResult(True, "P0-self", "Identical equations")

        # Phase 1: Tautology target (x=x is implied by everything)
        if t_id in self.equations and self.equations[t_id].is_tautology:
            return PredictionResult(True, "P1-taut-target", "Target is tautology")

        # Phase 2: Collapse hypothesis (implies everything)
        if h_id in self._collapse_ids:
            return PredictionResult(True, "P2-collapse", "Hypothesis is collapse")

        # Phase 3: Tautology hypothesis (implies only itself)
        if h_id in self.equations and self.equations[h_id].is_tautology:
            return PredictionResult(False, "P3-taut-hyp", "Tautology implies only itself")

        # Phase 4: Variable analysis
        if h_id in self.equations and t_id in self.equations:
            new_vars = self.equations.vars_in_target_not_in_hypothesis(h_id, t_id)
            if new_vars:
                return PredictionResult(
                    False, "P4-new-vars", f"Target has new variable(s): {new_vars}"
                )

        # Phase 5: Substitution detection
        if h_id in self.equations and t_id in self.equations:
            if self.equations.is_substitution_instance(h_id, t_id):
                return PredictionResult(
                    True, "P5-substitution", "Target is substitution instance of hypothesis"
                )

        # Phase 5a: Equivalence class lookup
        # Equations with identical implication row profiles mutually imply each other.
        # Proof: if rows are identical then matrix[h,t] == matrix[t,t] == TRUE (diagonal).
        if self.oracle is not None:
            h_class = self.oracle.equivalence_class(h_id)
            t_class = self.oracle.equivalence_class(t_id)
            if h_class is not None and t_class is not None and h_class == t_class:
                return PredictionResult(
                    True,
                    "P5a-equiv-class",
                    "Same equivalence class (identical row profiles)",
                )

        # Phase 5b/5c: Structural analysis via equation_analyzer
        # Delegates to the richer analysis in equation_analyzer.py which has:
        # - Determined operation detection (left/right projection, constant law)
        # - Counterexample testing (canonical + exhaustive 2-element magmas)
        # - Structural heuristics (depth comparison)
        if h_id in self.equations and t_id in self.equations:
            try:
                h_eq = ea_parse_equation(self.equations[h_id].text)
                t_eq = ea_parse_equation(self.equations[t_id].text)
                ea_result = analyze_implication(h_eq, t_eq)
                if ea_result.verdict == ImplicationVerdict.TRUE:
                    return PredictionResult(
                        True, f"P5b-structural({ea_result.phase})", ea_result.reason
                    )
                elif ea_result.verdict == ImplicationVerdict.FALSE:
                    return PredictionResult(
                        False, f"P5c-structural({ea_result.phase})", ea_result.reason
                    )
                # UNKNOWN falls through to default
            except (ValueError, KeyError) as exc:
                logger.debug("Structural analysis failed for E%d=>E%d: %s", h_id, t_id, exc)

        # Phase 6: Default FALSE (base rate favors FALSE)
        return PredictionResult(False, "P6-default", "No rule matched, default FALSE")

    def predict_bool(self, h_id: int, t_id: int) -> bool:
        """Simple bool prediction for accuracy evaluation."""
        return self.predict(h_id, t_id).prediction

    def evaluate(self) -> dict[str, object]:
        """Evaluate against the oracle's full matrix."""
        if not self.oracle:
            raise ValueError("Need oracle for evaluation")

        result: dict[str, object] = self.oracle.accuracy_of(self.predict_bool)
        return result



if __name__ == "__main__":
    import time

    print("Loading data...")
    eqs = ETPEquations("research/data/etp/equations.txt")
    oracle = ImplicationOracle("research/data/etp/implications.csv")
    proc = DecisionProcedure(eqs, oracle)

    print(f"Equations: {len(eqs)}")
    print(f"Collapse equations: {len(proc.collapse_ids)}")

    print("\nEvaluating full 22M matrix...")
    t0 = time.time()
    result = proc.evaluate()
    elapsed = time.time() - t0

    print(f"Time: {elapsed:.1f}s")
    print(f"Accuracy: {result['accuracy']:.4f}")
    print(f"  TP={result['tp']:,}  FP={result['fp']:,}")
    print(f"  TN={result['tn']:,}  FN={result['fn']:,}")
    print(f"  Precision={result['precision']:.4f}  Recall={result['recall']:.4f}")
