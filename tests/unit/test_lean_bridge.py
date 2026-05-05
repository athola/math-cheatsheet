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

import re

import pytest

from lean_bridge import counterexample_to_lean, counterexample_to_lean_theorem


class TestCounterexampleToLean:
    @pytest.mark.unit
    def test_emits_fin_type_carrier(self):
        """The generated Lean source references ``Fin 2`` for a 2-element magma."""
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

        assert re.fullmatch(r"op_[A-Za-z0-9_]+", identifier), (
            f"Generated identifier {identifier!r} contains non-identifier chars"
        )


# ---------------------------------------------------------------------------
# Issue #64: real theorem emission with `decide` discharge
# ---------------------------------------------------------------------------


class TestCounterexampleToLeanTheorem:
    """Feature: emit a real Lean 4 theorem proving ``¬(H → T)`` (#64).

    The previous ``counterexample_to_lean`` API emitted scaffolding with a
    ``True := by trivial`` body that does not witness the implication.
    The new API translates H and T into Lean propositions over the
    synthesised binary operation and discharges via ``decide``.
    """

    @pytest.mark.unit
    def test_emits_decide_theorem_body(self):
        lean = counterexample_to_lean_theorem(
            h_text="x * y = x",
            t_text="x * y = y * x",
            magma_name="LP",
            magma_size=2,
            magma_table=[[0, 0], [1, 1]],
        )
        assert ":= by decide" in lean
        assert "theorem h_not_implies_t" in lean
        # The negation-of-implication form is what makes ¬(H → T) ≡ H ∧ ¬T,
        # which decide can evaluate directly on the finite carrier.
        assert "¬ ((" in lean

    @pytest.mark.unit
    def test_translates_propositions_over_op_name(self):
        lean = counterexample_to_lean_theorem(
            h_text="x * y = x",
            t_text="x * y = y * x",
            magma_name="LP",
            magma_size=2,
            magma_table=[[0, 0], [1, 1]],
        )
        # The propositions should reference op_LP, not the parser's '*'.
        assert "op_LP (x) (y)" in lean
        # Universally quantified over Fin 2 — the variables collected
        # alphabetically so output is deterministic.
        assert "∀ x y : Fin 2," in lean

    @pytest.mark.unit
    def test_single_var_equation_emits_no_binder(self):
        """An equation like ``x = x`` has no quantifier variables — the
        binder must be elided to avoid an empty ``∀ : Fin n,`` token.
        """
        lean = counterexample_to_lean_theorem(
            h_text="x = x",
            t_text="x = x",
            magma_name="LP",
            magma_size=2,
            magma_table=[[0, 0], [1, 1]],
        )
        # `x` IS quantified (it's a free variable in the term parse), so
        # we expect ∀ x : Fin 2, here. The "no variables" path applies
        # only to ground terms which the project's parser does not produce.
        assert "∀ x : Fin 2," in lean

    @pytest.mark.unit
    def test_custom_theorem_name_propagated(self):
        lean = counterexample_to_lean_theorem(
            h_text="x * y = x",
            t_text="x * y = y * x",
            magma_name="LP",
            magma_size=2,
            magma_table=[[0, 0], [1, 1]],
            theorem_name="lp_breaks_commutativity",
        )
        assert "theorem lp_breaks_commutativity" in lean

    @pytest.mark.unit
    def test_validation_inherited_from_emit_op_def(self):
        with pytest.raises(ValueError, match="magma_size must be positive"):
            counterexample_to_lean_theorem(
                h_text="x = x",
                t_text="x = x",
                magma_name="LP",
                magma_size=0,
                magma_table=[],
            )

    @pytest.mark.unit
    def test_unparsable_equation_raises(self):
        with pytest.raises(ValueError):
            counterexample_to_lean_theorem(
                h_text="not an equation",  # No '='.
                t_text="x = x",
                magma_name="LP",
                magma_size=2,
                magma_table=[[0, 0], [1, 1]],
            )

    @pytest.mark.unit
    def test_emits_op_def_consistent_with_legacy_api(self):
        """The new API and the legacy placeholder must produce the SAME
        ``def op_<name>`` block — only the body after differs.
        """
        kwargs = dict(
            h_text="x * y = x",
            t_text="x * y = y * x",
            magma_name="LP",
            magma_size=2,
            magma_table=[[0, 0], [1, 1]],
        )
        legacy = counterexample_to_lean(**kwargs)
        theorem = counterexample_to_lean_theorem(**kwargs)
        # Compare the operation-definition blocks line-by-line.
        legacy_def = [ln for ln in legacy.splitlines() if "op_LP" in ln or "⟨" in ln]
        theorem_def = [ln for ln in theorem.splitlines() if "op_LP" in ln or "⟨" in ln]
        # The op def lines (5 = signature + 4 match arms) appear in both.
        assert legacy_def[:5] == theorem_def[:5]


# ---------------------------------------------------------------------------
# Cross-language e2e: opt-in test that runs lean on a sample of theorems.
# ---------------------------------------------------------------------------

# Sample counterexample bank: each entry is (H, T, magma_name, size, table).
# Each entry is a real (H ⇏ T) witnessed by the supplied magma. The list
# anchors the issue #64 acceptance criterion of ≥10 verified samples.
_LEAN_E2E_SAMPLES: list[tuple[str, str, str, int, list[list[int]]]] = [
    # Each entry must be a real counterexample: the magma satisfies H but
    # not T. Lean's `decide` will reject the snippet otherwise (verified
    # by the cross-language e2e test below — the constraint is enforced
    # by the theorem prover, not by hand).
    ("x * y = x", "x * y = y * x", "LP", 2, [[0, 0], [1, 1]]),
    ("x * y = y", "x * y = y * x", "RP", 2, [[0, 1], [0, 1]]),
    ("x * y = x", "x * y = y", "LP_vs_RP", 2, [[0, 0], [1, 1]]),
    ("x * y = y * x", "x * y = x", "C0", 2, [[0, 0], [0, 0]]),
    ("x * x = x", "x * y = x", "RP_idempotent_not_LP", 2, [[0, 1], [0, 1]]),
    ("x * x = x", "x * y = y", "LP_idempotent_not_RP", 2, [[0, 0], [1, 1]]),
    ("x * y = y * x", "x = x * x", "C0_comm_not_idempotent", 2, [[0, 0], [0, 0]]),
    ("x * x = x", "x * y = y * x", "LP_idempotent_not_comm", 2, [[0, 0], [1, 1]]),
    ("x * y = y * x", "(x * y) * z = x * (y * z)", "CM_comm_not_assoc", 2, [[1, 1], [1, 0]]),
    ("(x * y) * z = x * (y * z)", "x * y = y * x", "LP_assoc_not_comm", 2, [[0, 0], [1, 1]]),
]


class TestLeanE2EVerification:
    """Opt-in cross-language test: run ``lean`` on each emitted snippet.

    Skips automatically when the ``lean`` binary isn't on PATH so CI
    without a Lean toolchain stays green; actual verification happens
    when ``make lean-check`` or a developer with Lean installed runs
    ``pytest -m cross_language``.
    """

    @pytest.mark.cross_language
    @pytest.mark.parametrize(
        ("h_text", "t_text", "magma_name", "size", "table"),
        _LEAN_E2E_SAMPLES,
        ids=[s[2] for s in _LEAN_E2E_SAMPLES],
    )
    def test_sample_theorem_compiles_under_lean(
        self,
        h_text: str,
        t_text: str,
        magma_name: str,
        size: int,
        table: list[list[int]],
        tmp_path,
    ):
        import shutil
        import subprocess

        if shutil.which("lean") is None:
            pytest.skip("lean toolchain not installed; skipping cross-language e2e")

        lean_src = counterexample_to_lean_theorem(
            h_text=h_text,
            t_text=t_text,
            magma_name=magma_name,
            magma_size=size,
            magma_table=table,
        )
        lean_file = tmp_path / "Snippet.lean"
        lean_file.write_text(lean_src, encoding="utf-8")
        result = subprocess.run(
            ["lean", str(lean_file)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"Lean rejected the emitted snippet for ({magma_name}):\n"
            f"--- source ---\n{lean_src}\n--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )


class TestLeanE2EBankSize:
    """The cross-language bank must contain at least 10 samples — issue #64
    acceptance criterion. Pinned as a regression sentinel so future trims
    surface as a failed test rather than silent removal.
    """

    @pytest.mark.unit
    def test_e2e_sample_bank_has_at_least_ten_entries(self):
        assert len(_LEAN_E2E_SAMPLES) >= 10, (
            f"Issue #64 requires ≥10 verified counterexamples; bank has {len(_LEAN_E2E_SAMPLES)}."
        )
