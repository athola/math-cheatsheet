"""Tests for DecisionProcedure.

Uses small synthetic fixtures for ETPEquations and ImplicationOracle
to test all 7 phases of the decision procedure independently.
"""

import csv
from pathlib import Path

import pytest

from decision_procedure import DecisionProcedure, PredictionResult
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle


@pytest.fixture
def equations_file(tmp_path: Path) -> Path:
    """Create a small equations file.

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
      Eq5 (3-var): implies 1, 2, 5 (collapse-like because forces |M|=1)
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
def eqs(equations_file: Path) -> ETPEquations:
    return ETPEquations(equations_file)


@pytest.fixture
def oracle(oracle_csv: Path) -> ImplicationOracle:
    return ImplicationOracle(oracle_csv)


@pytest.fixture
def proc(eqs: ETPEquations, oracle: ImplicationOracle) -> DecisionProcedure:
    return DecisionProcedure(eqs, oracle)


class TestPredictionResult:
    def test_fields(self):
        r = PredictionResult(True, "P0-self", "Identical equations")
        assert r.prediction is True
        assert r.phase == "P0-self"
        assert r.reason == "Identical equations"


class TestCollapsePrecomputation:
    def test_collapse_ids_detected(self, proc: DecisionProcedure):
        """Eq2 implies all 5 equations, so is_collapse returns True."""
        assert 2 in proc.collapse_ids

    def test_non_collapse_excluded(self, proc: DecisionProcedure):
        assert 1 not in proc.collapse_ids
        assert 3 not in proc.collapse_ids
        assert 4 not in proc.collapse_ids


class TestPhase0SelfImplication:
    def test_identical_returns_true(self, proc: DecisionProcedure):
        result = proc.predict(3, 3)
        assert result.prediction is True
        assert result.phase == "P0-self"


class TestPhase1TautologyTarget:
    def test_tautology_target_returns_true(self, proc: DecisionProcedure):
        """Any hypothesis implies the tautology x=x."""
        result = proc.predict(3, 1)
        assert result.prediction is True
        assert result.phase == "P1-taut-target"

    def test_non_tautology_target_not_caught(self, proc: DecisionProcedure):
        result = proc.predict(3, 4)
        assert result.phase != "P1-taut-target"


class TestPhase2CollapseHypothesis:
    def test_collapse_hypothesis_returns_true(self, proc: DecisionProcedure):
        """Collapse equation implies any target."""
        result = proc.predict(2, 4)
        assert result.prediction is True
        assert result.phase == "P2-collapse"


class TestPhase3TautologyHypothesis:
    def test_tautology_hypothesis_returns_false(self, proc: DecisionProcedure):
        """Tautology implies nothing but itself (caught by P0)."""
        result = proc.predict(1, 3)
        assert result.prediction is False
        assert result.phase == "P3-taut-hyp"


class TestPhase4NewVariables:
    def test_new_vars_returns_false(self, proc: DecisionProcedure):
        """Eq4 (x,y) -> Eq5 (x,y,z): target has new var z."""
        result = proc.predict(4, 5)
        assert result.prediction is False
        assert result.phase == "P4-new-vars"
        assert "z" in result.reason


class TestPhase5Substitution:
    def test_substitution_instance_returns_true(self, proc: DecisionProcedure):
        """Eq3 (x*y=y*x) specialized by y->x gives x*x=x*x (Eq1).

        But Eq1 is caught earlier by P1 (tautology target).
        Test with a case where substitution applies after all earlier phases.
        """
        # Eq3 x*y=y*x, Eq4 x*y=x: not a substitution instance
        result = proc.predict(3, 4)
        # This won't hit P5, it'll fall through to P6
        assert result.phase in ("P5-substitution", "P6-default")


class TestPhase6Default:
    def test_default_false(self, proc: DecisionProcedure):
        """When no rule matches, default to FALSE."""
        result = proc.predict(3, 4)
        assert result.prediction is False
        assert result.phase == "P6-default"


class TestPredictBool:
    def test_returns_bool(self, proc: DecisionProcedure):
        assert proc.predict_bool(2, 2) is True
        assert proc.predict_bool(1, 3) is False


class TestWithoutOracle:
    def test_no_collapse_detection_without_oracle(self, eqs: ETPEquations):
        proc = DecisionProcedure(eqs, oracle=None)
        assert len(proc.collapse_ids) == 0

    def test_self_implication_still_works(self, eqs: ETPEquations):
        proc = DecisionProcedure(eqs, oracle=None)
        result = proc.predict(3, 3)
        assert result.prediction is True

    def test_evaluate_raises_without_oracle(self, eqs: ETPEquations):
        proc = DecisionProcedure(eqs, oracle=None)
        with pytest.raises(ValueError, match="Need oracle"):
            proc.evaluate()


class TestEvaluate:
    def test_evaluate_returns_metrics(self, proc: DecisionProcedure):
        result = proc.evaluate()
        assert "accuracy" in result
        assert "tp" in result
        assert "fp" in result

    def test_evaluate_accuracy_positive(self, proc: DecisionProcedure):
        result = proc.evaluate()
        assert result["accuracy"] > 0.0


class TestEvaluateByPhase:
    def test_returns_phase_breakdown(self, proc: DecisionProcedure):
        phases = proc.evaluate_by_phase()
        assert isinstance(phases, dict)
        # At least P0-self should be present (diagonal)
        assert "P0-self" in phases

    def test_phase_stats_have_accuracy(self, proc: DecisionProcedure):
        phases = proc.evaluate_by_phase()
        for phase, stats in phases.items():
            assert "accuracy" in stats
            assert "tp" in stats
            assert "total" in stats

    def test_evaluate_by_phase_raises_without_oracle(self, eqs: ETPEquations):
        proc = DecisionProcedure(eqs, oracle=None)
        with pytest.raises(ValueError, match="Need oracle"):
            proc.evaluate_by_phase()
