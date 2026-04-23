"""Tests for scripts/check_accuracy_gate.py (regression #23).

Feature: Parse accuracy from harness output and gate on a configurable
threshold. The parser must accept both ``Accuracy: 98.50%`` and
``Accuracy: 0.9850`` forms.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_accuracy_gate as gate  # noqa: E402


class TestParseAccuracyPct:
    """
    Feature: Extract accuracy as a percentage from the harness output.

    As a CI operator
    I want a single regex-based parser
    So that the harness can evolve its format without breaking the gate.
    """

    @pytest.mark.unit
    def test_percentage_form(self):
        """Scenario: harness prints ``Accuracy: 98.50%`` → parser returns 98.5."""
        assert gate.parse_accuracy_pct("Accuracy: 98.50%") == pytest.approx(98.5)

    @pytest.mark.unit
    def test_decimal_form(self):
        """Scenario: harness prints ``Accuracy: 0.9801`` → parser returns 98.01."""
        assert gate.parse_accuracy_pct("Accuracy: 0.9801") == pytest.approx(98.01)

    @pytest.mark.unit
    def test_with_surrounding_noise(self):
        """Scenario: extra output around the accuracy line is tolerated."""
        text = (
            "=== Decision Procedure Harness ===\n"
            "Phase hits: P0=4694 ...\n"
            "  Accuracy: 94.25% (1131/1200)\n"
            "Elapsed: 12.3s\n"
        )
        assert gate.parse_accuracy_pct(text) == pytest.approx(94.25)

    @pytest.mark.unit
    def test_absent_returns_none(self):
        """Scenario: no accuracy line anywhere → returns None."""
        assert gate.parse_accuracy_pct("nothing to see here") is None


class TestMain:
    """
    Feature: ``main`` exits zero on pass, non-zero on fail.

    The harness invocation is patched so the test does not require the
    full ETP dataset.
    """

    @pytest.mark.unit
    def test_pass_when_above_threshold(self, monkeypatch: pytest.MonkeyPatch):
        """Scenario: measured 99% > threshold 98% → exit 0."""
        monkeypatch.setattr(gate, "run_harness", lambda _p: "Accuracy: 99.00%\n")
        assert gate.main(["--threshold", "98.0"]) == 0

    @pytest.mark.unit
    def test_fail_when_below_threshold(self, monkeypatch: pytest.MonkeyPatch):
        """Scenario: measured 90% < threshold 98% → exit 1."""
        monkeypatch.setattr(gate, "run_harness", lambda _p: "Accuracy: 90.00%\n")
        assert gate.main(["--threshold", "98.0"]) == 1

    @pytest.mark.unit
    def test_unparseable_returns_two(self, monkeypatch: pytest.MonkeyPatch):
        """Scenario: harness output has no accuracy line → exit 2."""
        monkeypatch.setattr(gate, "run_harness", lambda _p: "harness broke\n")
        assert gate.main(["--threshold", "98.0"]) == 2
