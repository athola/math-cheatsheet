"""Tests for Lean proof template generation (issue #15).

Feature: Automated Lean proof generation scaffolding
    As a researcher
    I want to generate Lean 4 proof stubs from decision procedure results
    So that I can systematically expand formal verification coverage
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


class TestTrueProofTemplate:
    """Feature: Generate Lean proof templates for TRUE implications."""

    @pytest.mark.unit
    def test_template_contains_theorem_name(self):
        """
        Scenario: Generate a TRUE proof template
        Given equation IDs 43 and 4512
        When a TRUE proof template is generated
        Then it should contain a properly named theorem
        """
        from generate_lean_proofs import generate_true_proof_template

        result = generate_true_proof_template(
            43, 4512, "P5-substitution", "Target is specialization"
        )
        assert "e43_implies_e4512" in result
        assert "sorry" in result  # Proof stub

    @pytest.mark.unit
    def test_template_includes_phase_info(self):
        """
        Scenario: Template includes decision procedure metadata
        Given a prediction with phase P2-collapse
        When the template is generated
        Then it should document the phase and reason
        """
        from generate_lean_proofs import generate_true_proof_template

        result = generate_true_proof_template(2, 100, "P2-collapse", "Hypothesis is collapse")
        assert "P2-collapse" in result
        assert "collapse" in result.lower()


class TestFalseWitnessTemplate:
    """Feature: Generate Lean counterexample witnesses for FALSE implications."""

    @pytest.mark.unit
    def test_false_template_uses_negation(self):
        """
        Scenario: FALSE template uses negation in theorem statement
        Given a FALSE implication
        When the template is generated
        Then it should contain ¬ (negation) in the type
        """
        from generate_lean_proofs import generate_false_witness_template

        result = generate_false_witness_template(100, 200, "P4-new-vars", "New variable z")
        assert "not_implies" in result
        assert "sorry" in result

    @pytest.mark.unit
    def test_false_template_documents_counterexample(self):
        """
        Scenario: FALSE template documents the counterexample reason
        Given a FALSE prediction from counterexample testing
        When the template is generated
        Then it should include the counterexample info
        """
        from generate_lean_proofs import generate_false_witness_template

        result = generate_false_witness_template(
            6, 3, "P5c-structural(Phase 4)", "Counterexample: LP"
        )
        assert "Counterexample" in result
        assert "e6_not_implies_e3" in result
