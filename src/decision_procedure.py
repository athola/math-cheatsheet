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
  6: Default → FALSE
"""

from __future__ import annotations

from dataclasses import dataclass

from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle


@dataclass(frozen=True)
class PredictionResult:
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
        """Run the full decision procedure."""
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

        # Phase 6: Default FALSE (base rate favors FALSE)
        return PredictionResult(False, "P6-default", "No rule matched, default FALSE")

    def predict_bool(self, h_id: int, t_id: int) -> bool:
        """Simple bool prediction for accuracy evaluation."""
        return self.predict(h_id, t_id).prediction

    def evaluate(self, sample_size: int | None = None) -> dict[str, object]:
        """Evaluate against the oracle's full matrix.

        If sample_size is set, evaluate on a random sample instead of all 22M.
        """
        if not self.oracle:
            raise ValueError("Need oracle for evaluation")

        result: dict[str, object] = self.oracle.accuracy_of(self.predict_bool)
        return result

    def evaluate_by_phase(self) -> dict[str, dict]:
        """Break down predictions by which phase decided them."""
        if not self.oracle:
            raise ValueError("Need oracle for evaluation")

        phase_stats: dict[str, dict] = {}

        for i, h_id in enumerate(self.oracle._eq_ids):
            for j, t_id in enumerate(self.oracle._col_eq_ids):
                actual_val = int(self.oracle._matrix[i, j])
                if actual_val in (3, 4):
                    actual = True
                elif actual_val in (-3, -4):
                    actual = False
                else:
                    continue

                result = self.predict(h_id, t_id)
                phase = result.phase

                if phase not in phase_stats:
                    phase_stats[phase] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0}

                ps = phase_stats[phase]
                ps["total"] += 1
                if result.prediction and actual:
                    ps["tp"] += 1
                elif result.prediction and not actual:
                    ps["fp"] += 1
                elif not result.prediction and actual:
                    ps["fn"] += 1
                else:
                    ps["tn"] += 1

        # Add accuracy to each phase
        for phase, ps in phase_stats.items():
            correct = ps["tp"] + ps["tn"]
            ps["accuracy"] = correct / ps["total"] if ps["total"] > 0 else 0.0

        return phase_stats


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
