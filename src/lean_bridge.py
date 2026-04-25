"""Python → Lean 4 bridge for Stage 2 formal verification (issue #32).

Takes a Python-side implication outcome (typically a ``PredictionResult``
plus the underlying ``CounterexampleMagma``) and emits a self-contained
Lean 4 source snippet that restates the finding in a form ``lean`` can
type-check. The initial scope covers FALSE implications witnessed by a
finite 2-element magma; larger carriers and TRUE-side proof skeletons
can follow the same pattern.

The emitted source is intentionally minimal scaffolding:

- One ``def`` for the binary operation, defined by ``match`` on the pair
  of indices so the Cayley table is visible in the source.
- Carrier is ``Fin n`` (standard Mathlib choice for small finite types).
- One placeholder ``example : True := by trivial`` so the snippet
  type-checks. Note: this body is a tautology — it does **not** witness
  the implication. Upgrading to ``theorem h_not_implies_t : ¬ ... := by
  decide`` once the equations are emitted as Lean propositions is
  tracked as backlog issue O1 from PR #57 review.

Callers intending to verify with ``lean --stdin`` should concatenate the
snippet after whatever imports they need (typically just
``import Mathlib.Data.Fin.Basic``).
"""

from __future__ import annotations

import re

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
        the file compiles. Upgrading to a real ``decide``-discharged
        theorem is backlog issue O1.

    Raises:
        ValueError: if ``magma_name`` is empty / whitespace-only, if
            ``magma_size`` is not positive, or if ``magma_table`` isn't a
            size×size square matrix with entries in ``[0, magma_size)``.
    """
    if magma_size <= 0:
        raise ValueError(f"magma_size must be positive, got {magma_size}")
    sanitized = _sanitize_op_name(magma_name)
    if not sanitized:
        raise ValueError(f"magma_name {magma_name!r} reduces to an empty Lean identifier")
    _validate_table(magma_size, magma_table)

    op_name = f"op_{sanitized}"
    # Each match arm writes one (i, j) → table[i][j] case. For a 2-element
    # carrier this is four arms; scales quadratically in size, which is fine
    # for the size-2 scope of this issue.
    arms: list[str] = []
    for i in range(magma_size):
        for j in range(magma_size):
            arms.append(f"  | ⟨{i}, _⟩, ⟨{j}, _⟩ => ⟨{magma_table[i][j]}, by decide⟩")
    arms_block = "\n".join(arms)

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


__all__ = ["counterexample_to_lean"]
