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


class TestRunHarness:
    """Cover ``run_harness`` subprocess invocation and SystemExit path (#51).

    Previously the only paths exercised were through patched ``run_harness``;
    the function's own ``subprocess.run`` invocation and the
    ``raise SystemExit`` branch on non-zero return code had no coverage.
    """

    @pytest.mark.unit
    def test_returns_combined_stdout_and_stderr_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """A zero-status subprocess returns its stdout+stderr concatenated."""
        from types import SimpleNamespace

        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["cwd"] = kwargs.get("cwd")
            captured["check"] = kwargs.get("check")
            return SimpleNamespace(returncode=0, stdout="Accuracy: 99.10%\n", stderr="info\n")

        monkeypatch.setattr(gate.subprocess, "run", fake_run)
        result = gate.run_harness(tmp_path / "cheatsheet.txt")
        assert "Accuracy: 99.10%" in result
        assert "info" in result
        # The harness must be invoked via ``-m cheatsheet_harness accuracy``.
        assert "cheatsheet_harness" in " ".join(captured["cmd"])
        # check=False so we control the failure path ourselves.
        assert captured["check"] is False

    @pytest.mark.unit
    def test_nonzero_returncode_raises_systemexit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """A non-zero subprocess return must surface as SystemExit (not return)."""
        from types import SimpleNamespace

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=2, stdout="boom\n", stderr="traceback\n")

        monkeypatch.setattr(gate.subprocess, "run", fake_run)
        with pytest.raises(SystemExit, match="status 2"):
            gate.run_harness(tmp_path / "cheatsheet.txt")
