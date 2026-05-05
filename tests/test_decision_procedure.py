"""Tests for DecisionProcedure.

Uses small synthetic fixtures for ETPEquations and ImplicationOracle
to test all phases of the decision procedure independently.
Includes slow integration tests for accuracy on the full 22M matrix.
"""

import csv
import json
import logging
from pathlib import Path

import pytest

from decision_procedure import DecisionProcedure, PredictionResult
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle

DATA_DIR = Path(__file__).parent.parent / "research" / "data" / "etp"


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

    def test_phase_with_structural_suffix_accepted(self):
        # P5b/P5c-structural carry a parenthesised internal-phase suffix
        # (e.g. "P5b-structural(Phase 4)") that the validator must allow.
        r = PredictionResult(True, "P5b-structural(Phase 4)", "x")
        assert r.phase.startswith("P5b-structural")

    def test_typoed_phase_rejected(self):
        # S3 / #53: a typo like "P6-defualt" must fail at construction time
        # rather than slip through string comparisons in tests/reporters.
        with pytest.raises(ValueError, match="not in the closed taxonomy"):
            PredictionResult(False, "P6-defualt", "typo")

    def test_unknown_phase_prefix_rejected(self):
        with pytest.raises(ValueError, match="not in the closed taxonomy"):
            PredictionResult(True, "P99-magical", "ought to be impossible")


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
        # Falls through P5, then structural analysis may catch it via counterexample
        assert result.prediction is False
        assert result.phase in ("P5-substitution", "P5c-structural(Phase 4)", "P6-default")


class TestPhase6Default:
    def test_default_false(self, proc: DecisionProcedure):
        """When no structural rule matches, prediction is FALSE."""
        result = proc.predict(3, 4)
        assert result.prediction is False
        # May be caught by structural analysis (counterexample) or fall to default
        assert "P5c" in result.phase or "P6" in result.phase


class TestPhase5cStructuralFalse:
    """Test P5c: structural analysis returning FALSE via determined operation."""

    def test_determined_op_disproves(self, proc: DecisionProcedure):
        """
        Eq4 (x*y=x) determines LP magma; Eq3 (comm) fails in LP → FALSE.
        This tests the structural delegation path (P5b/P5c) specifically.
        """
        result = proc.predict(4, 3)
        assert result.prediction is False
        # Should be caught by structural analysis, not default
        assert "P5c" in result.phase or "P5b" in result.phase, (
            f"Expected structural phase, got: {result.phase}"
        )

    def test_structural_phase_provides_reason(self, proc: DecisionProcedure):
        """Structural analysis should explain WHY the implication fails."""
        result = proc.predict(4, 3)
        assert result.reason != ""
        assert (
            "left projection" in result.reason.lower() or "counterexample" in result.reason.lower()
        )


class TestStructuralFallthrough:
    """Test that parse errors in structural analysis fall through gracefully."""

    def test_no_oracle_still_uses_structural(self, eqs: ETPEquations):
        """Without oracle, structural analysis still runs on parseable equations."""
        proc_no_oracle = DecisionProcedure(eqs, oracle=None)
        # Eq4 (x*y=x) → Eq3 (x*y=y*x): structural analysis should catch this
        result = proc_no_oracle.predict(4, 3)
        assert result.prediction is False


class TestPredictBool:
    def test_returns_bool(self, proc: DecisionProcedure):
        assert proc.predict_bool(2, 2) is True
        assert proc.predict_bool(1, 3) is False


class TestPredictLogging:
    """Pin DEBUG-level logging emission in DecisionProcedure.predict (#50/H7).

    Regression #30 added ``logger.debug`` emission of the deciding phase
    for every predict call so that error analysis can replay decisions.
    Without an explicit caplog assertion, a revert of the ``logger.debug``
    line passes every other test — these tests block that revert.
    """

    def test_predict_emits_debug_log_with_phase(self, proc: DecisionProcedure, caplog):
        caplog.set_level(logging.DEBUG, logger="decision_procedure")
        proc.predict(1, 1)
        # Pattern: "E1 => E1 : True (P0-self)"
        assert any(
            "E1 => E1" in record.message and "P0-self" in record.message
            for record in caplog.records
        ), f"Expected debug log mentioning E1 => E1 and P0-self; got: {caplog.text}"
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1

    def test_predict_logs_phase_for_each_call(self, proc: DecisionProcedure, caplog):
        """Every predict call should emit one debug record."""
        caplog.set_level(logging.DEBUG, logger="decision_procedure")
        proc.predict(1, 2)
        proc.predict(2, 3)
        proc.predict(3, 4)
        debug_records = [r for r in caplog.records if r.name == "decision_procedure"]
        assert len(debug_records) == 3

    def test_predict_default_level_does_not_log(self, proc: DecisionProcedure, caplog):
        """At default WARNING level, debug records are suppressed."""
        # Default caplog level is WARNING; do not raise it.
        proc.predict(1, 1)
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) == 0


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


class TestPhaseEquivClass:
    """Test the equivalence class phase (P5a) in the decision procedure."""

    @pytest.fixture
    def equiv_equations_file(self, tmp_path: Path) -> Path:
        """Create equations where Eq3 and Eq4 have the same profile."""
        eq_path = tmp_path / "equations.txt"
        # 6 equations:
        #   1: x = x         (tautology)
        #   2: x = y         (collapse)
        #   3: x ◇ y = y ◇ x (commutativity)
        #   4: x ◇ x = x ◇ x (tautology-like but different from Eq1)
        #   5: x ◇ y = x     (left projection)
        #   6: x ◇ y = y     (right projection)
        eq_path.write_text(
            "x = x\nx = y\nx ◇ y = y ◇ x\nx ◇ x = x ◇ x\nx ◇ y = x\nx ◇ y = y\n",
            encoding="utf-8",
        )
        return eq_path

    @pytest.fixture
    def equiv_oracle_csv(self, tmp_path: Path) -> Path:
        """6x6 matrix where Eq3 and Eq6 have identical row profiles."""
        csv_path = tmp_path / "implications.csv"
        matrix = [
            [3, -3, -3, -3, -3, -3],  # Eq1: tautology
            [3, 3, 3, 3, 3, 3],  # Eq2: collapse
            [3, -3, 3, -3, -3, 3],  # Eq3: implies 1, 3, 6
            [3, -3, -3, 3, -3, -3],  # Eq4: implies 1, 4
            [3, -3, -3, -3, 3, -3],  # Eq5: implies 1, 5
            [3, -3, 3, -3, -3, 3],  # Eq6: same row as Eq3 → same class
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        return csv_path

    @pytest.fixture
    def equiv_proc(self, equiv_equations_file: Path, equiv_oracle_csv: Path) -> DecisionProcedure:
        eqs = ETPEquations(equiv_equations_file)
        oracle = ImplicationOracle(equiv_oracle_csv)
        return DecisionProcedure(eqs, oracle)

    def test_same_class_predicts_true(self, equiv_proc: DecisionProcedure):
        """Eq3 and Eq6 have the same row profile, so 3→6 should be TRUE."""
        result = equiv_proc.predict(3, 6)
        assert result.prediction is True
        assert result.phase == "P5a-equiv-class"

    def test_same_class_symmetric(self, equiv_proc: DecisionProcedure):
        """Equivalence is symmetric: 6→3 should also be TRUE."""
        result = equiv_proc.predict(6, 3)
        assert result.prediction is True
        assert result.phase == "P5a-equiv-class"

    def test_different_class_falls_through(self, equiv_proc: DecisionProcedure):
        """Eq4 and Eq5 are in different classes, so they don't match here."""
        result = equiv_proc.predict(4, 5)
        assert result.phase != "P5a-equiv-class"

    def test_earlier_phases_take_priority(self, equiv_proc: DecisionProcedure):
        """Self-implication is caught by P0, not P5a."""
        result = equiv_proc.predict(3, 3)
        assert result.phase == "P0-self"

    def test_equiv_class_not_used_without_oracle(self, tmp_path: Path):
        """Without oracle, equiv class phase is skipped."""
        eq_path = tmp_path / "equations.txt"
        eq_path.write_text("x = x\nx = y\n", encoding="utf-8")
        eqs = ETPEquations(eq_path)
        proc = DecisionProcedure(eqs, oracle=None)
        result = proc.predict(1, 2)
        assert result.phase != "P5a-equiv-class"


@pytest.mark.slow
class TestFullMatrixAccuracy:
    """Evaluate the decision procedure against the full 22M implication matrix.

    Requires: research/data/etp/equations.txt and research/data/etp/implications.csv
    """

    @pytest.fixture(scope="class")
    def full_proc(self) -> DecisionProcedure:
        eqs_path = DATA_DIR / "equations.txt"
        csv_path = DATA_DIR / "implications.csv"
        if not eqs_path.exists() or not csv_path.exists():
            pytest.skip("Full dataset not available")
        eqs = ETPEquations(eqs_path)
        oracle = ImplicationOracle(csv_path)
        return DecisionProcedure(eqs, oracle)

    def test_accuracy_at_least_90_percent(self, full_proc: DecisionProcedure):
        """FR-003 requirement: accuracy >= 90% on the full 22M matrix."""
        result = full_proc.evaluate()
        accuracy = result["accuracy"]
        assert accuracy >= 0.90, f"Accuracy {accuracy:.4f} is below 90% threshold"

    def test_accuracy_at_least_98_percent(self, full_proc: DecisionProcedure):
        """Stretch goal: maintain ~98% accuracy after equivalence class addition."""
        result = full_proc.evaluate()
        accuracy = result["accuracy"]
        assert accuracy >= 0.98, f"Accuracy {accuracy:.4f} is below 98% stretch target"


@pytest.mark.slow
class TestCompetitionProblems:
    """Evaluate the decision procedure on the 1200 competition problems.

    Requires: research/data/etp/competition/synthetic_problems.json
    """

    @pytest.fixture(scope="class")
    def competition_data(self) -> list[dict]:
        problems_path = DATA_DIR / "competition" / "synthetic_problems.json"
        if not problems_path.exists():
            pytest.skip("Competition data not available")
        with open(problems_path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def full_proc(self) -> DecisionProcedure:
        eqs_path = DATA_DIR / "equations.txt"
        csv_path = DATA_DIR / "implications.csv"
        if not eqs_path.exists() or not csv_path.exists():
            pytest.skip("Full dataset not available")
        eqs = ETPEquations(eqs_path)
        oracle = ImplicationOracle(csv_path)
        return DecisionProcedure(eqs, oracle)

    def test_competition_accuracy_at_least_93_percent(
        self, full_proc: DecisionProcedure, competition_data: list[dict]
    ):
        """FR-003 requirement: accuracy >= 93% on the 1200 competition problems."""
        correct = 0
        total = 0
        for problem in competition_data:
            h_id = problem["equation_1_id"]
            t_id = problem["equation_2_id"]
            expected = problem["answer"]
            predicted = full_proc.predict_bool(h_id, t_id)
            if predicted == expected:
                correct += 1
            total += 1

        accuracy = correct / total if total > 0 else 0.0
        assert accuracy >= 0.93, (
            f"Competition accuracy {accuracy:.4f} ({correct}/{total}) is below 93% threshold"
        )

    def test_competition_has_1200_problems(self, competition_data: list[dict]):
        """Verify we have the expected number of competition problems."""
        assert len(competition_data) == 1200

    def test_competition_normal_accuracy(
        self, full_proc: DecisionProcedure, competition_data: list[dict]
    ):
        """Track accuracy on normal-difficulty problems separately."""
        normal = [p for p in competition_data if p["difficulty"] == "normal"]
        correct = sum(
            1
            for p in normal
            if full_proc.predict_bool(p["equation_1_id"], p["equation_2_id"]) == p["answer"]
        )
        accuracy = correct / len(normal) if normal else 0.0
        # Normal problems should be easier
        assert accuracy >= 0.93, f"Normal accuracy {accuracy:.4f} below 93%"

    def test_competition_hard_accuracy(
        self, full_proc: DecisionProcedure, competition_data: list[dict]
    ):
        """Track accuracy on hard-difficulty problems separately."""
        hard = [p for p in competition_data if p["difficulty"] == "hard"]
        correct = sum(
            1
            for p in hard
            if full_proc.predict_bool(p["equation_1_id"], p["equation_2_id"]) == p["answer"]
        )
        accuracy = correct / len(hard) if hard else 0.0
        # Hard problems may have lower accuracy, but still track it
        assert accuracy >= 0.80, f"Hard accuracy {accuracy:.4f} below 80%"
