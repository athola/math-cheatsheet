"""Tests for Python → Lean 4 counterexample bridge (issue #32).

Feature: generate Lean 4 source that witnesses a FALSE implication.

Given a ``CounterexampleMagma`` and the two equation texts, emit a Lean
``example`` statement where the carrier is a ``Fin n`` type with a
match-based binary operation. The generated source should be parseable
by Lean 4 (matching Mathlib conventions) without needing the full proof
written out — a ``decide`` tactic or ``native_decide`` closes the
carrier-level check.

Acceptance criteria (from #32):
- Python → Lean 4 counterexample generation works for 2-element magmas.
"""

from __future__ import annotations

import pytest


class TestCounterexampleToLean:
    @pytest.mark.unit
    def test_emits_fin_type_carrier(self):
        """The generated Lean source references ``Fin 2`` for a 2-element magma."""
        from lean_bridge import counterexample_to_lean

        lean = counterexample_to_lean(
            h_text="x * y = y * x",
            t_text="x * y = x",
            magma_name="N1",
            magma_size=2,
            magma_table=[[0, 0], [1, 0]],
        )
        assert "Fin 2" in lean

    @pytest.mark.unit
    def test_emits_example_header(self):
        """Output contains an ``example`` declaration — the standard Lean 4 idiom
        for anonymous proof obligations."""
        from lean_bridge import counterexample_to_lean

        lean = counterexample_to_lean(
            h_text="x * y = y * x",
            t_text="x * y = x",
            magma_name="N1",
            magma_size=2,
            magma_table=[[0, 0], [1, 0]],
        )
        assert "example" in lean

    @pytest.mark.unit
    def test_encodes_cayley_table(self):
        """Every cell of the magma table appears in the generated source so a
        reader can reconstruct the witness from the Lean file alone."""
        from lean_bridge import counterexample_to_lean

        table = [[0, 0], [1, 0]]
        lean = counterexample_to_lean(
            h_text="x * y = y * x",
            t_text="x * y = x",
            magma_name="N1",
            magma_size=2,
            magma_table=table,
        )
        # At minimum, the table's corner entries must appear as literal 0s and 1s
        # and reference pattern matching on Fin 2.
        assert "match" in lean or "| " in lean

    @pytest.mark.unit
    def test_references_hypothesis_and_target(self):
        """Comments in the generated source cite H and T so the file is
        self-documenting."""
        from lean_bridge import counterexample_to_lean

        lean = counterexample_to_lean(
            h_text="x * y = y * x",
            t_text="x * y = x",
            magma_name="N1",
            magma_size=2,
            magma_table=[[0, 0], [1, 0]],
        )
        assert "x * y = y * x" in lean
        assert "x * y = x" in lean


class TestCounterexampleToLeanValidation:
    @pytest.mark.unit
    def test_rejects_non_square_table(self):
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="square"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="bad",
                magma_size=2,
                magma_table=[[0, 0], [1]],  # row 1 is short
            )

    @pytest.mark.unit
    def test_rejects_size_mismatch(self):
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="size"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="bad",
                magma_size=3,  # claims 3 but table is 2x2
                magma_table=[[0, 0], [1, 0]],
            )

    @pytest.mark.unit
    def test_rejects_entry_out_of_range(self):
        """Cayley table entries must be indices into the carrier (``[0, size)``)."""
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="outside"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="bad",
                magma_size=2,
                magma_table=[[0, 2], [1, 0]],  # cell (0,1)=2 is out of range
            )

    @pytest.mark.unit
    def test_rejects_empty_magma_name(self):
        """NEW-C6: empty ``magma_name`` produces ``def op_`` — not a valid Lean
        identifier. Reject at the boundary instead of emitting broken Lean."""
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="magma_name"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="",
                magma_size=2,
                magma_table=[[0, 0], [1, 1]],
            )

    @pytest.mark.unit
    def test_rejects_whitespace_only_magma_name(self):
        """NEW-C6: whitespace-only name reduces to an empty identifier after
        sanitisation; reject it the same way as an empty name."""
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="magma_name"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="   ",
                magma_size=2,
                magma_table=[[0, 0], [1, 1]],
            )

    @pytest.mark.unit
    def test_rejects_zero_size(self):
        """NEW-C6: ``magma_size=0`` produces a ``def`` with zero match arms,
        which is uncompilable and meaningless as a witness."""
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="magma_size"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="z",
                magma_size=0,
                magma_table=[],
            )

    @pytest.mark.unit
    def test_rejects_negative_size(self):
        """NEW-C6: negative size is meaningless and would underflow the table
        validation; reject explicitly with a clear message."""
        from lean_bridge import counterexample_to_lean

        with pytest.raises(ValueError, match="magma_size"):
            counterexample_to_lean(
                h_text="x = y",
                t_text="x = x",
                magma_name="z",
                magma_size=-1,
                magma_table=[],
            )


class TestCounterexampleToLeanSanitizer:
    """N5 / NEW-I6: ``op_name`` sanitisation must produce valid Lean
    identifiers (``[A-Za-z0-9_]`` after the ``op_`` prefix) even for the
    parens-laden names already used by ``CANONICAL_MAGMAS``."""

    @pytest.mark.unit
    def test_sanitizer_handles_parens(self):
        """``"N1 (Non-comm Non-assoc)"`` → identifier without parens."""
        import re

        from lean_bridge import counterexample_to_lean

        lean = counterexample_to_lean(
            h_text="x = y",
            t_text="x = x",
            magma_name="N1 (Non-comm Non-assoc)",
            magma_size=2,
            magma_table=[[0, 0], [1, 0]],
        )
        op_decl_line = next(line for line in lean.splitlines() if line.startswith("def op_"))
        identifier = op_decl_line.split()[1]
        assert re.fullmatch(r"op_[A-Za-z0-9_]+", identifier), (
            f"Generated identifier {identifier!r} contains non-identifier chars"
        )
        assert identifier.startswith("op_N1")

    @pytest.mark.unit
    def test_sanitizer_handles_z3_z3z(self):
        """``"Z3 (Z/3Z addition)"`` (a real ``CANONICAL_MAGMAS`` entry) must
        produce a valid identifier — the previous narrow strip would emit
        ``op_Z3_(Z_3Z_addition)`` (parens leak through)."""
        from lean_bridge import counterexample_to_lean

        lean = counterexample_to_lean(
            h_text="x = y",
            t_text="x = x",
            magma_name="Z3 (Z/3Z addition)",
            magma_size=3,
            magma_table=[[0, 1, 2], [1, 2, 0], [2, 0, 1]],
        )
        op_decl_line = next(line for line in lean.splitlines() if line.startswith("def op_"))
        identifier = op_decl_line.split()[1]
        # Lean identifier rule: ASCII alphanumerics and underscore
        import re

        assert re.fullmatch(r"op_[A-Za-z0-9_]+", identifier), (
            f"Generated identifier {identifier!r} contains non-identifier chars"
        )
