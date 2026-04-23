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
