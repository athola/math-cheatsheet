"""Tests for tla_bridge.py - TLA+ Python bridge functions.

Feature: TLA+ bridge utilities for equation evaluation and counterexample search
    As a competition evaluator
    I want Python functions that evaluate equations in magmas and search for counterexamples
    So that the TLA+ bridge provides working utilities, not just stubs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_models import Counterexample, Magma
from tla_bridge import (
    COUNTEREXAMPLES,
    TLAModelChecker,
    evaluate_equation,
    get_counterexample,
    search_counterexample,
)

_ETP_PATH = (
    Path(__file__).resolve().parent.parent / "research" / "data" / "etp" / "equations.txt"
)
_HAS_ETP = _ETP_PATH.exists()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _commutative_magma() -> Magma:
    """2-element commutative magma: a◇b = min(a,b)."""
    return Magma(size=2, operation=[[0, 0], [0, 1]])


def _non_commutative_magma() -> Magma:
    """2-element non-commutative magma: 0◇1=1, 1◇0=0."""
    return Magma(size=2, operation=[[0, 1], [0, 1]])


# ──────────────────────────────────────────────────────────────────────────────
# evaluate_equation
# ──────────────────────────────────────────────────────────────────────────────


class TestEvaluateEquation:
    """Feature: evaluate an equation in a magma under a specific variable assignment."""

    @pytest.mark.unit
    def test_commutativity_holds_with_matching_assignment(self):
        """
        Scenario: Commutativity holds for a specific assignment in a commutative magma
        Given a commutative magma and assignment x=0, y=1
        When I evaluate 'x ◇ y = y ◇ x'
        Then the result should be True (0◇1 == 1◇0 in a min-magma)
        """
        result = evaluate_equation(_commutative_magma(), "x ◇ y = y ◇ x", {"x": 0, "y": 1})
        assert result is True

    @pytest.mark.unit
    def test_commutativity_fails_on_non_commutative_magma(self):
        """
        Scenario: Commutativity fails in a non-commutative magma
        Given a non-commutative magma where 0◇1=1 but 1◇0=0
        And assignment x=0, y=1
        When I evaluate 'x ◇ y = y ◇ x'
        Then the result should be False
        """
        result = evaluate_equation(_non_commutative_magma(), "x ◇ y = y ◇ x", {"x": 0, "y": 1})
        assert result is False

    @pytest.mark.unit
    def test_tautology_always_holds(self):
        """
        Scenario: x = x holds under any element assignment
        Given a non-commutative magma
        When I evaluate 'x = x' for every element
        Then the result is always True
        """
        magma = _non_commutative_magma()
        for x in range(magma.size):
            assert evaluate_equation(magma, "x = x", {"x": x}) is True

    @pytest.mark.unit
    def test_star_notation_accepted(self):
        """
        Scenario: Star notation is accepted as alternative to ◇
        Given the equation string 'x * y = y * x' (using * instead of ◇)
        When I evaluate it on a commutative magma
        Then it parses and evaluates correctly
        """
        result = evaluate_equation(_commutative_magma(), "x * y = y * x", {"x": 0, "y": 1})
        assert result is True

    @pytest.mark.unit
    def test_single_element_magma(self):
        """
        Scenario: Single-element magma satisfies every equation
        Given a 1-element magma (trivial)
        When I evaluate any equation with assignment x=0, y=0
        Then the result is True
        """
        trivial = Magma(size=1, operation=[[0]])
        assert evaluate_equation(trivial, "x ◇ y = y ◇ x", {"x": 0, "y": 0}) is True
        assert evaluate_equation(trivial, "x ◇ (y ◇ z) = (x ◇ y) ◇ z", {"x": 0, "y": 0, "z": 0}) is True


# ──────────────────────────────────────────────────────────────────────────────
# search_counterexample
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not _HAS_ETP, reason="equations.txt not available")
class TestSearchCounterexample:
    """Feature: find a counterexample magma witnessing a FALSE ETP implication."""

    @pytest.mark.unit
    def test_tautology_implies_itself_no_counterexample(self):
        """
        Scenario: eq1 (x=x) implies itself — no counterexample exists
        Given the trivially true implication eq1 => eq1
        When I search for a counterexample
        Then None is returned
        """
        result = search_counterexample([1], 1, max_size=2)
        assert result is None

    @pytest.mark.unit
    def test_commutativity_does_not_imply_associativity(self):
        """
        Scenario: eq43 (commutativity) does NOT imply eq4512 (associativity)
        Given the FALSE implication eq43 => eq4512
        When I search for a counterexample up to size 2
        Then a Counterexample is returned
        And its magma is commutative but not associative
        """
        result = search_counterexample([43], 4512, max_size=2)
        assert result is not None
        assert isinstance(result, Counterexample)

        m = result.magma
        # Witness must satisfy commutativity (eq43)
        for a in range(m.size):
            for b in range(m.size):
                assert m.op(a, b) == m.op(b, a), "Witness must be commutative"
        # Witness must violate associativity (eq4512)
        is_assoc = all(
            m.op(m.op(a, b), c) == m.op(a, m.op(b, c))
            for a in range(m.size)
            for b in range(m.size)
            for c in range(m.size)
        )
        assert not is_assoc, "Witness must not be associative"

    @pytest.mark.unit
    def test_conclusion_id_recorded_correctly(self):
        """
        Scenario: Returned counterexample records the target equation ID
        Given eq43 => eq4512 search
        When a counterexample is found
        Then its conclusion_id equals 4512
        """
        result = search_counterexample([43], 4512, max_size=2)
        assert result is not None
        assert result.conclusion_id == 4512

    @pytest.mark.unit
    def test_invalid_equation_id_raises(self):
        """
        Scenario: Equation ID 0 is out of range (equations are 1-indexed)
        Given an invalid equation ID of 0
        When search_counterexample is called
        Then ValueError is raised mentioning 'out of range'
        """
        with pytest.raises(ValueError, match="out of range"):
            search_counterexample([0], 1, max_size=2)


# ──────────────────────────────────────────────────────────────────────────────
# TLAModelChecker.check_property
# ──────────────────────────────────────────────────────────────────────────────


class TestTLAModelCheckerCheckProperty:
    """Feature: invoke TLC model checker and parse its result."""

    def _checker(self, tla_dir: str = "/fake/tla") -> TLAModelChecker:
        return TLAModelChecker(tla_dir=tla_dir)

    @pytest.mark.unit
    def test_raises_runtime_error_when_jar_not_found(self):
        """
        Scenario: tla2tools.jar is not installed
        Given _find_tla_tools() returns None
        When check_property is called
        Then RuntimeError is raised with setup instructions
        """
        checker = self._checker()
        with patch.object(TLAModelChecker, "_find_tla_tools", return_value=None):
            with pytest.raises(RuntimeError, match="tla2tools"):
                checker.check_property("Magma", "TypeOK", {})

    @pytest.mark.unit
    def test_raises_file_not_found_when_tla_missing(self, tmp_path):
        """
        Scenario: The requested .tla file does not exist in tla_dir
        Given a valid jar path but no .tla file
        When check_property is called
        Then FileNotFoundError is raised
        """
        checker = TLAModelChecker(tla_dir=str(tmp_path))
        with patch.object(
            TLAModelChecker, "_find_tla_tools", return_value=Path("/fake/tla2tools.jar")
        ):
            with pytest.raises(FileNotFoundError):
                checker.check_property("NonExistent", "SomeProp", {})

    @pytest.mark.unit
    def test_returns_true_none_when_tlc_passes(self, tmp_path):
        """
        Scenario: TLC verifies all properties successfully
        Given TLC output contains 'No error has been found'
        When check_property is called
        Then (True, None) is returned
        """
        (tmp_path / "Magma.tla").write_text("---- MODULE Magma ----\n====\n")
        checker = TLAModelChecker(tla_dir=str(tmp_path))

        mock_proc = MagicMock()
        mock_proc.stdout = "Model checking completed. No error has been found.\n"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with patch.object(
            TLAModelChecker, "_find_tla_tools", return_value=Path("/fake/tla2tools.jar")
        ):
            with patch("subprocess.run", return_value=mock_proc):
                result, trace = checker.check_property("Magma", "TypeOK", {"N": 2})

        assert result is True
        assert trace is None

    @pytest.mark.unit
    def test_returns_false_with_trace_when_tlc_finds_violation(self, tmp_path):
        """
        Scenario: TLC finds a property violation
        Given TLC output contains 'Error: Invariant ... is violated'
        When check_property is called
        Then (False, trace_string) is returned where trace contains 'Error'
        """
        (tmp_path / "Magma.tla").write_text("---- MODULE Magma ----\n====\n")
        checker = TLAModelChecker(tla_dir=str(tmp_path))

        mock_proc = MagicMock()
        mock_proc.stdout = "Error: Invariant TypeOK is violated.\nState 1: x = 1\n"
        mock_proc.stderr = ""
        mock_proc.returncode = 12

        with patch.object(
            TLAModelChecker, "_find_tla_tools", return_value=Path("/fake/tla2tools.jar")
        ):
            with patch("subprocess.run", return_value=mock_proc):
                result, trace = checker.check_property("Magma", "TypeOK", {})

        assert result is False
        assert trace is not None
        assert "Error" in trace

    @pytest.mark.unit
    def test_config_generation_includes_constants(self):
        """
        Scenario: Generated TLC config file contains CONSTANTS section
        Given constants dict {"N": 2, "Elements": {0, 1}}
        When _generate_config is called
        Then the returned string contains each constant name
        """
        checker = self._checker()
        cfg = checker._generate_config({"N": 2, "Elements": {0, 1}})
        assert "N" in cfg
        assert "Elements" in cfg


# ──────────────────────────────────────────────────────────────────────────────
# get_counterexample / COUNTEREXAMPLES cache
# ──────────────────────────────────────────────────────────────────────────────


class TestGetCounterexample:
    """Feature: look up known counterexamples from the module-level cache."""

    @pytest.mark.unit
    def test_returns_none_when_pair_not_in_cache(self):
        """
        Scenario: No counterexample stored for this pair
        Given COUNTEREXAMPLES has no entry for (99999, 99998)
        When get_counterexample(99999, 99998) is called
        Then None is returned
        """
        result = get_counterexample(99999, 99998)
        assert result is None

    @pytest.mark.unit
    def test_returns_magma_from_populated_cache(self):
        """
        Scenario: Counterexample stored in cache is retrieved correctly
        Given COUNTEREXAMPLES[(43, 4512)] is pre-populated with a known magma
        When get_counterexample(43, 4512) is called
        Then the stored magma is returned unchanged
        """
        import tla_bridge

        magma = Magma(size=2, operation=[[0, 1], [0, 0]])
        tla_bridge.COUNTEREXAMPLES[(43, 4512)] = magma
        try:
            result = get_counterexample(43, 4512)
            assert result is magma
        finally:
            del tla_bridge.COUNTEREXAMPLES[(43, 4512)]
