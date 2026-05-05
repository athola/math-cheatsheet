"""Python → Lean 4 bridge for Stage 2 formal verification (issues #32, #64).

Takes a Python-side implication outcome (typically a ``PredictionResult``
plus the underlying ``CounterexampleMagma``) and emits a self-contained
Lean 4 source snippet that restates the finding in a form ``lean`` can
type-check.

Two entry points:

- :func:`counterexample_to_lean` — original placeholder scaffolding from
  PR #57. Emits the binary-operation ``def`` plus an
  ``example : True := by trivial`` body. Type-checks but does **not**
  witness the implication. Kept for backward compatibility with
  callers that pre-date #64.

- :func:`counterexample_to_lean_theorem` — issue #64 upgrade. Emits the
  binary-operation ``def`` plus a real theorem
  ``¬ (H_prop → T_prop) := by decide`` where ``H_prop`` and ``T_prop``
  are the equations translated into Lean propositions over ``Fin n``.
  ``decide`` discharges the obligation because every quantifier ranges
  over a finite type with decidable equality.

Callers intending to verify with ``lean --stdin`` should concatenate the
snippet after whatever imports they need (for the theorem variant,
``import Mathlib.Data.Fin.Basic`` is sufficient on stock Mathlib).
"""

from __future__ import annotations

import re

from term import NodeType, Term, parse_equation_terms

# Allowed Lean identifier body chars after the ``op_`` prefix. We collapse any
# run of disallowed chars into a single underscore and trim leading/trailing
# underscores so names like ``"Z3 (Z/3Z addition)"`` produce ``op_Z3_Z_3Z_addition``
# rather than ``op_Z3_(Z_3Z_addition)`` (NEW-I6 / N5).
_OP_NAME_INVALID_RE = re.compile(r"[^A-Za-z0-9_]+")


def _sanitize_op_name(magma_name: str) -> str:
    """Convert a magma label into a valid Lean identifier body.

    Collapses any run of non-identifier characters to ``_`` and strips
    leading/trailing underscores. Caller is responsible for ensuring the
    input has at least one identifier character (see input validation in
    ``counterexample_to_lean``).
    """
    return _OP_NAME_INVALID_RE.sub("_", magma_name).strip("_")


def counterexample_to_lean(
    *,
    h_text: str,
    t_text: str,
    magma_name: str,
    magma_size: int,
    magma_table: list[list[int]],
) -> str:
    """Emit a Lean 4 ``example`` block witnessing that H does not imply T.

    Args:
        h_text: Hypothesis equation, e.g. ``"x * y = y * x"``. Rendered as
            a comment so a reader knows what the carrier is supposed to
            disprove.
        t_text: Target equation (also rendered as a comment).
        magma_name: Short label (e.g. ``"N1"``) used in the generated
            definition name so emitted snippets don't collide when stacked.
        magma_size: ``n`` — number of elements in the carrier. Must be
            consistent with ``magma_table``.
        magma_table: 2D list where ``magma_table[i][j]`` is ``i * j``.

    Returns:
        Lean 4 source as a single string. Contains one ``def`` for the
        binary operation and one ``example : True := by trivial`` block
        annotated with both equation texts. The placeholder body type-checks
        but does **not** discharge the implication — it is scaffolding so
        the file compiles. Callers wanting a real theorem proof should
        use :func:`counterexample_to_lean_theorem` (issue #64).

    Raises:
        ValueError: if ``magma_name`` is empty / whitespace-only, if
            ``magma_size`` is not positive, or if ``magma_table`` isn't a
            size×size square matrix with entries in ``[0, magma_size)``.
    """
    op_name, arms_block = _emit_op_def(magma_name, magma_size, magma_table)
    return f"""\
-- Counterexample witnessing that H does not imply T.
--   H: {h_text}
--   T: {t_text}
--   Magma: {magma_name} (size {magma_size}), Cayley table = {magma_table}

def {op_name} : Fin {magma_size} → Fin {magma_size} → Fin {magma_size}
{arms_block}

-- The carrier satisfies H but not T; therefore H ⇏ T.
-- (Equation-level obligations should be discharged with `decide`
-- once the match definition is in scope.)
example : True := by trivial
"""


def counterexample_to_lean_theorem(
    *,
    h_text: str,
    t_text: str,
    magma_name: str,
    magma_size: int,
    magma_table: list[list[int]],
    theorem_name: str = "h_not_implies_t",
) -> str:
    """Emit a Lean 4 theorem proving that H does not imply T (#64).

    Translates ``h_text`` and ``t_text`` into Lean propositions of the form
    ``∀ x y ... : Fin n, lhs = rhs`` over the synthesised binary
    operation ``op_<sanitized_name>``, then emits::

        theorem h_not_implies_t :
            ¬ ((∀ ... : Fin n, ...) → (∀ ... : Fin n, ...)) := by decide

    The body discharges via ``decide`` because every quantifier ranges
    over ``Fin n`` (a ``Fintype`` with decidable equality), making both
    propositions decidable. Lean's kernel evaluates the implication in
    finite time and closes the goal.

    The negation-of-implication form ``¬ (H → T)`` is logically
    equivalent to ``H ∧ ¬ T``; for a counterexample magma both
    conjuncts hold, so the proposition is True and ``decide`` succeeds.

    Args:
        h_text: Hypothesis equation in the project's parser syntax
            (``x * y = y * x``, ``x ◇ y = y ◇ x``, etc.).
        t_text: Target equation, same syntax.
        magma_name: Short label (e.g. ``"N1"``) used to derive the
            ``op_<name>`` definition.
        magma_size: ``n`` — carrier size; consistent with ``magma_table``.
        magma_table: 2D list, ``magma_table[i][j] = i * j``.
        theorem_name: Lean identifier for the emitted theorem. Defaults
            to ``h_not_implies_t``; callers stacking multiple emissions
            in one file should pick distinct names.

    Returns:
        Lean 4 source as a single string. Contains the operation ``def``
        and the theorem with ``decide`` body. Self-contained except for
        ``import Mathlib.Data.Fin.Basic``.

    Raises:
        ValueError: same conditions as :func:`counterexample_to_lean`,
            plus ``ValueError`` if either equation cannot be parsed.
    """
    op_name, arms_block = _emit_op_def(magma_name, magma_size, magma_table)
    h_lhs, h_rhs = parse_equation_terms(h_text)
    t_lhs, t_rhs = parse_equation_terms(t_text)
    h_prop = _equation_to_lean_prop(h_lhs, h_rhs, op_name, magma_size)
    t_prop = _equation_to_lean_prop(t_lhs, t_rhs, op_name, magma_size)
    return f"""\
-- Counterexample witnessing that H does not imply T (issue #64).
--   H: {h_text}
--   T: {t_text}
--   Magma: {magma_name} (size {magma_size}), Cayley table = {magma_table}

def {op_name} : Fin {magma_size} → Fin {magma_size} → Fin {magma_size}
{arms_block}

-- H_prop and T_prop are decidable because every quantifier ranges over
-- Fin {magma_size}; ¬(H → T) ≡ H ∧ ¬T, and `decide` evaluates the
-- conjunction directly on the finite carrier.
theorem {theorem_name} :
    ¬ (({h_prop}) → ({t_prop})) := by decide
"""


def _emit_op_def(magma_name: str, magma_size: int, magma_table: list[list[int]]) -> tuple[str, str]:
    """Validate inputs and return ``(op_name, arms_block)`` for the operation def.

    Shared between :func:`counterexample_to_lean` and
    :func:`counterexample_to_lean_theorem` so the operation-emission rules
    (sanitisation, table validation, ``Fin`` match arms) live in one place.
    """
    if magma_size <= 0:
        raise ValueError(f"magma_size must be positive, got {magma_size}")
    sanitized = _sanitize_op_name(magma_name)
    if not sanitized:
        raise ValueError(f"magma_name {magma_name!r} reduces to an empty Lean identifier")
    _validate_table(magma_size, magma_table)
    op_name = f"op_{sanitized}"
    # Each match arm writes one (i, j) → table[i][j] case. For a 2-element
    # carrier this is four arms; scales quadratically in size.
    arms_block = "\n".join(
        f"  | ⟨{i}, _⟩, ⟨{j}, _⟩ => ⟨{magma_table[i][j]}, by decide⟩"
        for i in range(magma_size)
        for j in range(magma_size)
    )
    return op_name, arms_block


def _equation_to_lean_prop(lhs: Term, rhs: Term, op_name: str, magma_size: int) -> str:
    """Render ``lhs = rhs`` as ``∀ vars : Fin n, lean_lhs = lean_rhs``.

    Variables are sorted alphabetically for deterministic output (so two
    runs over the same equation produce identical Lean source).
    """
    variables = sorted(lhs.variables() | rhs.variables())
    binder = f"∀ {' '.join(variables)} : Fin {magma_size}," if variables else ""
    body = f"{_term_to_lean(lhs, op_name)} = {_term_to_lean(rhs, op_name)}"
    return f"{binder} {body}".strip()


def _term_to_lean(term: Term, op_name: str) -> str:
    """Recursively render a Term as a Lean expression over ``op_name``.

    VAR nodes become bare identifiers (matching the universal binder);
    OP nodes become ``op_name (left) (right)`` with parentheses to
    disambiguate associativity in the emitted source.
    """
    if term.node_type == NodeType.VAR:
        return term.name
    lt, rt = term._lr()
    return f"{op_name} ({_term_to_lean(lt, op_name)}) ({_term_to_lean(rt, op_name)})"


def _validate_table(size: int, table: list[list[int]]) -> None:
    """Reject malformed Cayley tables with a message that points at the fault."""
    if len(table) != size:
        raise ValueError(f"magma size {size} does not match table row count {len(table)}")
    for row_index, row in enumerate(table):
        if len(row) != size:
            raise ValueError(
                f"table is not square: row {row_index} has {len(row)} entries, expected {size}"
            )
        for col_index, cell in enumerate(row):
            if not (0 <= cell < size):
                raise ValueError(
                    f"table entry [{row_index}][{col_index}]={cell} is outside [0, {size})"
                )


__all__ = [
    "counterexample_to_lean",
    "counterexample_to_lean_theorem",
]
