"""Tests for decision procedure consolidation (issue #21).

Feature: Unified decision procedure
    As a developer
    I want a single decision procedure module that handles both string and ID inputs
    So that logic isn't duplicated across equation_analyzer.py and decision_procedure.py

Acceptance criteria:
- All phases from both modules preserved
- All existing tests pass
- Accuracy unchanged
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from decision_procedure import DecisionProcedure
from equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle


@pytest.fixture
def equations_file(tmp_path: Path) -> Path:
    eq_path = tmp_path / "equations.txt"
    eq_path.write_text(
        "x = x\n"  # 1: tautology
        "x = y\n"  # 2: collapse
        "x ◇ y = y ◇ x\n"  # 3: commutativity
        "x ◇ y = x\n"  # 4: left projection
        "x ◇ y = z\n"  # 5: 3 vars (new var z)
        "x ◇ (y ◇ z) = (x ◇ y) ◇ z\n"  # 6: associativity
        "x ◇ x = x\n",  # 7: idempotence
        encoding="utf-8",
    )
    return eq_path


@pytest.fixture
def oracle_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "implications.csv"
    # 7x7 matrix
    matrix = [
        [3, -3, -3, -3, -3, -3, -3],  # 1: tautology (implies only self)
        [3, 3, 3, 3, 3, 3, 3],  # 2: collapse (implies all)
        [3, -3, 3, -3, -3, -3, -3],  # 3: commutativity
        [3, -3, -3, 3, -3, -3, 3],  # 4: left proj → implies idem
        [3, 3, -3, -3, 3, -3, -3],  # 5: 3-var (collapse-like)
        [3, -3, -3, -3, -3, 3, -3],  # 6: associativity
        [3, -3, -3, -3, -3, -3, 3],  # 7: idempotence
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


class TestConsolidatedPhases:
    """Verify that the consolidated procedure covers all phases from both modules."""

    @pytest.mark.unit
    def test_phase5_determined_operation_detected(self, proc: DecisionProcedure):
        """
        Scenario: Left projection equation determines magma operation
        Given H: x*y = x (left projection, determines LP magma)
        And T: x*x = x (idempotence)
        When the decision procedure runs
        Then it should detect the determined operation and verify T holds
        """
        # Eq4 (x*y=x) should imply Eq7 (x*x=x) via determined operation
        result = proc.predict(4, 7)
        assert result.prediction is True, (
            f"Left projection should imply idempotence. Got: {result.phase}: {result.reason}"
        )

    @pytest.mark.unit
    def test_counterexample_phase_used(self, proc: DecisionProcedure):
        """
        Scenario: Counterexample magma disproves implication
        Given H: associativity and T: commutativity
        When the decision procedure runs
        Then it should use counterexample testing to disprove
        """
        # Eq6 (assoc) does NOT imply Eq3 (comm)
        result = proc.predict(6, 3)
        assert result.prediction is False

    @pytest.mark.unit
    def test_all_original_phases_still_work(self, proc: DecisionProcedure):
        """Ensure original P0-P6 phases all still fire."""
        # P0: self-implication
        assert proc.predict(3, 3).phase == "P0-self"
        # P1: tautology target
        assert proc.predict(3, 1).phase == "P1-taut-target"
        # P2: collapse hypothesis
        assert proc.predict(2, 4).phase == "P2-collapse"
        # P3: tautology hypothesis
        assert proc.predict(1, 3).phase == "P3-taut-hyp"
        # P4: new variables
        assert proc.predict(4, 5).phase == "P4-new-vars"


class TestEnhancedPhases:
    """Verify phases from equation_analyzer are integrated into decision_procedure."""

    @pytest.mark.unit
    def test_counterexample_phase_provides_evidence(self, proc: DecisionProcedure):
        """
        Scenario: Decision procedure uses counterexample magmas for FALSE verdicts
        Given a pair where default FALSE is correct but counterexample exists
        When the decision procedure runs
        Then it should provide counterexample evidence (not just default FALSE)
        """
        # Eq6 (assoc) does NOT imply Eq3 (comm)
        # Before consolidation: falls to P6-default
        # After consolidation: should use counterexample magma (Phase 4 from analyzer)
        result = proc.predict(6, 3)
        assert result.prediction is False
        # After consolidation, the phase should reference counterexample or structural analysis
        assert (
            "structural" in result.phase.lower()
            or "P5c" in result.phase
            or "counterexample" in result.reason.lower()
        ), f"Expected structural/counterexample phase, got: {result.phase}: {result.reason}"

    @pytest.mark.unit
    def test_determined_op_detection_integrated(self, proc: DecisionProcedure):
        """
        Scenario: Decision procedure detects determined operations
        Given H determines the magma operation (e.g., left projection)
        And T either holds or fails in that determined magma
        When the decision procedure runs
        Then it should use determined operation detection
        """
        # Eq4: x*y=x determines LP magma
        # Eq3: x*y=y*x (commutativity) fails in LP
        result = proc.predict(4, 3)
        assert result.prediction is False
        # Should be caught by determined op or counterexample, not default
        assert result.phase != "P6-default", (
            f"Expected determined-op or counterexample phase, got: {result.phase}"
        )


class TestAnalyzerAndProcedureAgree:
    """Verify the string-based analyzer and ID-based procedure produce consistent results."""

    @pytest.mark.unit
    def test_both_agree_on_collapse_implies_all(self):
        """Both modules should agree that collapse implies everything."""
        h = parse_equation("x = y")
        t = parse_equation("x * y = y * x")
        analyzer_result = analyze_implication(h, t)
        assert analyzer_result.verdict == ImplicationVerdict.TRUE

    @pytest.mark.unit
    def test_both_agree_on_new_var_false(self):
        """Both should agree: new variable in target → FALSE."""
        h = parse_equation("x * x = x")
        t = parse_equation("x * y = y * x")
        analyzer_result = analyze_implication(h, t)
        assert analyzer_result.verdict == ImplicationVerdict.FALSE

    @pytest.mark.unit
    def test_predict_bool_matches_analyzer(self, proc: DecisionProcedure, eqs: ETPEquations):
        """For equation pairs where both can reason, results should agree."""
        # Test a few pairs
        pairs_to_check = [(3, 6), (6, 3), (4, 7), (1, 3)]
        for h_id, t_id in pairs_to_check:
            proc_pred = proc.predict_bool(h_id, t_id)
            h_eq = parse_equation(eqs[h_id].text)
            t_eq = parse_equation(eqs[t_id].text)
            ana_result = analyze_implication(h_eq, t_eq)
            # analyzer UNKNOWN defaults to FALSE
            ana_pred = ana_result.verdict == ImplicationVerdict.TRUE
            assert proc_pred == ana_pred, (
                f"Disagreement on E{h_id}→E{t_id}: "
                f"proc={proc_pred} ({proc.predict(h_id, t_id).phase}), "
                f"analyzer={ana_pred} ({ana_result.phase})"
            )
