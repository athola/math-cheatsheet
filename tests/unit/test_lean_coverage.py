"""Tests for the Lean proof coverage dashboard (issue #25).

Feature: Lean proof inventory scanner
    Walks the ``lean/`` tree, extracts ``theorem``/``def``/``example``
    declarations, and classifies each as a "proven implication" (tagged
    via a comment) versus scaffolding. Cross-referenced against the
    oracle's implication matrix to report coverage.

Acceptance criteria (from #25):
- Lean proof inventory generated.
- Coverage percentage reported.
- Gaps prioritized by competition relevance.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestLeanScanner:
    @pytest.mark.unit
    def test_scan_finds_theorems_in_lean_file(self, tmp_path: Path):
        from lean_coverage import scan_lean_declarations

        lean_file = tmp_path / "Sample.lean"
        lean_file.write_text(
            "theorem implication_reflexivity (e : Equation) : implies e e := by\n"
            "  sorry\n"
            "def knownTrueImplications : List ImplicationEntry := []\n"
            "example : True := by trivial\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        kinds = sorted({d.kind for d in decls})
        assert "theorem" in kinds
        assert "def" in kinds
        assert "example" in kinds

    @pytest.mark.unit
    def test_scan_captures_name_for_named_declarations(self, tmp_path: Path):
        from lean_coverage import scan_lean_declarations

        (tmp_path / "File.lean").write_text(
            "theorem my_thm : True := by trivial\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        names = [d.name for d in decls if d.kind == "theorem"]
        assert "my_thm" in names

    @pytest.mark.unit
    def test_flags_sorry_as_unfinished(self, tmp_path: Path):
        """Declarations containing ``sorry`` or ``admit`` count as unfinished."""
        from lean_coverage import scan_lean_declarations

        (tmp_path / "Draft.lean").write_text(
            "theorem placeholder : True := by sorry\ntheorem finished : True := by trivial\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        by_name = {d.name: d for d in decls}
        assert by_name["placeholder"].unfinished is True
        assert by_name["finished"].unfinished is False


class TestCoverageReport:
    @pytest.mark.unit
    def test_coverage_percentage(self, tmp_path: Path):
        """With 3 finished theorems and 1 unfinished, coverage is 75%."""
        from lean_coverage import compute_coverage, scan_lean_declarations

        (tmp_path / "File.lean").write_text(
            "theorem a : True := by trivial\n"
            "theorem b : True := by trivial\n"
            "theorem c : True := by trivial\n"
            "theorem d : True := by sorry\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        coverage = compute_coverage(decls)
        assert coverage.total == 4
        assert coverage.finished == 3
        assert coverage.percentage == pytest.approx(75.0)

    @pytest.mark.unit
    def test_coverage_zero_theorems(self, tmp_path: Path):
        """No theorems → 0% (no division by zero)."""
        from lean_coverage import compute_coverage, scan_lean_declarations

        (tmp_path / "Empty.lean").write_text("-- just comments\n", encoding="utf-8")
        decls = scan_lean_declarations(tmp_path)
        coverage = compute_coverage(decls)
        assert coverage.total == 0
        assert coverage.percentage == 0.0
