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

from lean_coverage import compute_coverage, scan_lean_declarations


class TestLeanScanner:
    @pytest.mark.unit
    def test_scan_finds_theorems_in_lean_file(self, tmp_path: Path):
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
        (tmp_path / "Draft.lean").write_text(
            "theorem placeholder : True := by sorry\ntheorem finished : True := by trivial\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        by_name = {d.name: d for d in decls}
        assert by_name["placeholder"].unfinished is True
        assert by_name["finished"].unfinished is False

    @pytest.mark.unit
    def test_does_not_flag_sorry_in_line_comment(self, tmp_path: Path):
        """NEW-C3: ``-- sorry`` in a line comment must not mark a finished
        proof as unfinished. The previous regex matched the bare keyword
        anywhere in the declaration text, including inside comments."""
        (tmp_path / "Draft.lean").write_text(
            "theorem done : True := by trivial -- TODO: remove sorry\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        assert decls[0].name == "done"
        assert decls[0].unfinished is False

    @pytest.mark.unit
    def test_does_not_flag_admit_in_block_comment(self, tmp_path: Path):
        """NEW-C3: ``/- admit -/`` block comments must not trigger the
        unfinished flag. Lean block comments can nest, but for the dashboard
        a single-level strip is sufficient (matches conventional usage)."""
        (tmp_path / "Draft.lean").write_text(
            "theorem also_done : True := by trivial /- once admitted; now proved -/\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        assert decls[0].name == "also_done"
        assert decls[0].unfinished is False

    @pytest.mark.unit
    def test_does_not_flag_sorry_in_string_literal(self, tmp_path: Path):
        """NEW-C3: a string literal mentioning ``sorry`` must not count as
        a placeholder. Lean strings use double quotes; conservative strip
        before the placeholder scan."""
        (tmp_path / "Draft.lean").write_text(
            'theorem msg_done : True := by have _ := "say sorry"; trivial\n',
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        assert decls[0].name == "msg_done"
        assert decls[0].unfinished is False


class TestLeanScannerExtendedSyntax:
    """NEW-C5: ``_DECLARATION_RE`` previously required the keyword at line
    start, missing real-world Lean syntax: ``@[simp] theorem``, ``private``
    /``protected``/``noncomputable`` modifiers, ``instance``, ``structure``."""

    @pytest.mark.unit
    def test_finds_attribute_prefixed_theorem(self, tmp_path: Path):
        (tmp_path / "Attr.lean").write_text(
            "@[simp] theorem simp_lemma : True := by trivial\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        names = [d.name for d in decls]
        assert "simp_lemma" in names

    @pytest.mark.unit
    def test_finds_private_theorem(self, tmp_path: Path):
        (tmp_path / "Vis.lean").write_text(
            "private theorem hidden_thm : True := by trivial\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        names = [d.name for d in decls]
        assert "hidden_thm" in names

    @pytest.mark.unit
    def test_finds_noncomputable_def(self, tmp_path: Path):
        (tmp_path / "NC.lean").write_text(
            "noncomputable def some_def : Nat := 0\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        kinds = {(d.kind, d.name) for d in decls}
        assert ("def", "some_def") in kinds

    @pytest.mark.unit
    def test_finds_instance_declaration(self, tmp_path: Path):
        (tmp_path / "Inst.lean").write_text(
            "instance my_inst : Inhabited Nat := ⟨0⟩\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        kinds = {d.kind for d in decls}
        assert "instance" in kinds

    @pytest.mark.unit
    def test_finds_structure_declaration(self, tmp_path: Path):
        (tmp_path / "Struct.lean").write_text(
            "structure MyPair where\n  fst : Nat\n  snd : Nat\n",
            encoding="utf-8",
        )
        decls = scan_lean_declarations(tmp_path)
        kinds = {d.kind for d in decls}
        assert "structure" in kinds


class TestCoverageReport:
    @pytest.mark.unit
    def test_coverage_percentage(self, tmp_path: Path):
        """With 3 finished theorems and 1 unfinished, coverage is 75%."""
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
        (tmp_path / "Empty.lean").write_text("-- just comments\n", encoding="utf-8")
        decls = scan_lean_declarations(tmp_path)
        coverage = compute_coverage(decls)
        assert coverage.total == 0
        assert coverage.percentage == 0.0
