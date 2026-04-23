"""Equation structure analyzer for equational implication problems.

Implements the v3 cheatsheet decision procedure as computable functions:
- Phase 1: Instant decisions (tautology, collapse, identity)
- Phase 2: Variable analysis (new variables in target)
- Phase 3: Substitution detection (variable merging)
- Phase 4: Counterexample testing (canonical + exhaustive magmas)
- Phase 4b: Exhaustive 2-element search
- Phase 5: Determined operation detection (absorption, constant law)
- Phase 7: Structural heuristics (depth comparison)
- Phase 8: Default (inconclusive → FALSE)

Based on techniques from the Equational Theories Project (Tao et al., 2024-2025)
and Birkhoff's completeness theorem for equational logic.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum

from term import (
    NodeType,
    Term,
    op,
    parse_equation_terms,
    var,
)

# Re-export canonical names for existing callers.
__all__ = [
    "NodeType",
    "Term",
    "Equation",
    "parse_equation",
    "var",
    "op",
]


@dataclass(frozen=True)
class Equation:
    """An equational law: lhs = rhs, universally quantified."""

    lhs: Term
    rhs: Term

    def variables(self) -> set[str]:
        return self.lhs.variables() | self.rhs.variables()

    def max_depth(self) -> int:
        return max(self.lhs.depth(), self.rhs.depth())

    def total_ops(self) -> int:
        return self.lhs.size() + self.rhs.size()

    def substitute(self, mapping: dict[str, Term]) -> Equation:
        return Equation(self.lhs.substitute(mapping), self.rhs.substitute(mapping))

    def holds_in(self, table: list[list[int]], n: int) -> bool:
        """Check if this equation holds in the magma with n elements."""
        variables = sorted(self.variables())
        for assignment_tuple in itertools.product(range(n), repeat=len(variables)):
            assignment = dict(zip(variables, assignment_tuple))
            if self.lhs.evaluate(table, assignment) != self.rhs.evaluate(table, assignment):
                return False
        return True

    def __str__(self) -> str:
        return f"{self.lhs} = {self.rhs}"


def parse_equation(s: str) -> Equation:
    """Parse an equation string like ``x * (y * z) = (x * y) * z``."""
    lhs, rhs = parse_equation_terms(s)
    return Equation(lhs, rhs)


# --- Canonical Counterexample Magmas ---


@dataclass
class CounterexampleMagma:
    name: str
    size: int
    table: list[list[int]]
    properties: list[str] = field(default_factory=list)

    def satisfies(self, eq: Equation) -> bool:
        return eq.holds_in(self.table, self.size)


# The 7 canonical magmas from the v3 cheatsheet.
# Exposed as a tuple so the module-level constant cannot be mutated by callers
# (regression #41). Iteration semantics are identical to the former list.
CANONICAL_MAGMAS: tuple[CounterexampleMagma, ...] = (
    CounterexampleMagma(
        "LP (Left Projection)",
        2,
        [[0, 0], [1, 1]],
        ["associative", "idempotent", "NOT commutative"],
    ),
    CounterexampleMagma(
        "RP (Right Projection)",
        2,
        [[0, 1], [0, 1]],
        ["associative", "idempotent", "NOT commutative"],
    ),
    CounterexampleMagma(
        "C0 (Constant Zero)",
        2,
        [[0, 0], [0, 0]],
        ["associative", "commutative", "NOT idempotent"],
    ),
    CounterexampleMagma(
        "XR (XOR / Z2 addition)",
        2,
        [[0, 1], [1, 0]],
        ["commutative", "associative", "has identity", "NOT idempotent"],
    ),
    CounterexampleMagma(
        "CM (Commutative Non-Associative)",
        2,
        [[1, 1], [1, 0]],
        ["commutative", "NOT associative"],
    ),
    CounterexampleMagma(
        "N1 (Non-comm Non-assoc)",
        2,
        [[0, 0], [1, 0]],
        ["NOT commutative", "NOT associative"],
    ),
    CounterexampleMagma(
        "Z3 (Z/3Z addition)",
        3,
        [[0, 1, 2], [1, 2, 0], [2, 0, 1]],
        ["commutative", "associative", "has identity", "NOT idempotent"],
    ),
)

# All 16 possible 2-element magma tables (tuple to prevent mutation — #41).
ALL_SIZE_2_MAGMAS: tuple[CounterexampleMagma, ...] = tuple(
    CounterexampleMagma(f"M2_{i:04b}", 2, [[i >> 3 & 1, i >> 2 & 1], [i >> 1 & 1, i & 1]])
    for i in range(16)
)


# --- Analysis Functions ---


class ImplicationVerdict(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


@dataclass
class AnalysisResult:
    verdict: ImplicationVerdict
    phase: str
    reason: str
    counterexample: CounterexampleMagma | None = None


def analyze_implication(h: Equation, t: Equation) -> AnalysisResult:
    """Apply the v3 cheatsheet decision procedure programmatically."""

    # Phase 1: Instant decisions
    if h == t:
        return AnalysisResult(ImplicationVerdict.TRUE, "Phase 1a", "Identical equations")

    if _is_tautology(t):
        return AnalysisResult(ImplicationVerdict.TRUE, "Phase 1b", "Target is tautology")

    if _is_collapse(h):
        return AnalysisResult(ImplicationVerdict.TRUE, "Phase 1c", "Hypothesis is collapse law")

    if _is_collapse(t) and not _is_collapse(h):
        return AnalysisResult(ImplicationVerdict.FALSE, "Phase 1d", "Target is collapse, H is not")

    if _is_tautology(h) and not _is_tautology(t):
        return AnalysisResult(
            ImplicationVerdict.FALSE, "Phase 1e", "Hypothesis is tautology, T is not"
        )

    # Phase 5 (before Phase 2): Absorption and constant law detection
    # These determine the operation completely, overriding variable analysis.
    determined = _detect_determined_operation(h)
    if determined is not None:
        table, name = determined
        magma_size = len(table)
        if t.holds_in(table, magma_size):
            return AnalysisResult(
                ImplicationVerdict.TRUE, "Phase 5", f"H determines {name}; T holds in that magma"
            )
        else:
            return AnalysisResult(
                ImplicationVerdict.FALSE, "Phase 5", f"H determines {name}; T fails in that magma"
            )

    # Phase 2: Variable analysis
    h_vars = h.variables()
    t_vars = t.variables()
    new_vars = t_vars - h_vars

    if new_vars:
        return AnalysisResult(
            ImplicationVerdict.FALSE,
            "Phase 2",
            f"Target has new variable(s) {new_vars} not in hypothesis",
        )

    # Phase 3: Substitution check (simple cases)
    sub_result = _check_simple_substitutions(h, t)
    if sub_result is not None:
        return sub_result

    # Phase 4: Counterexample testing (canonical magmas)
    for magma in CANONICAL_MAGMAS:
        if magma.satisfies(h) and not magma.satisfies(t):
            return AnalysisResult(
                ImplicationVerdict.FALSE, "Phase 4", f"Counterexample: {magma.name}", magma
            )

    # Phase 4b: Exhaustive 2-element search
    for magma in ALL_SIZE_2_MAGMAS:
        if magma.satisfies(h) and not magma.satisfies(t):
            return AnalysisResult(
                ImplicationVerdict.FALSE,
                "Phase 4b",
                f"Counterexample: {magma.name} table={magma.table}",
                magma,
            )

    # Phase 7: Structural heuristics
    if t.max_depth() > h.max_depth() + 1:
        return AnalysisResult(
            ImplicationVerdict.FALSE,
            "Phase 7",
            f"Target depth ({t.max_depth()}) >> hypothesis depth ({h.max_depth()})",
        )

    return AnalysisResult(ImplicationVerdict.UNKNOWN, "Phase 8", "Inconclusive - default FALSE")


def _is_tautology(eq: Equation) -> bool:
    """Check if both sides of the equation are structurally identical."""
    return eq.lhs == eq.rhs


def _is_collapse(eq: Equation) -> bool:
    """Check if the equation forces |M|=1 (singleton/collapse).

    Covers both "x = y" and extended forms like "x = f(y,z,...)" where x
    does not appear in f.  Proof: fix any p,q ∈ M; assign the "fresh"
    variable to p and all others to q — the equation gives p = q.
    """
    if eq.lhs.node_type == NodeType.VAR and eq.lhs.name not in eq.rhs.variables():
        return True
    if eq.rhs.node_type == NodeType.VAR and eq.rhs.name not in eq.lhs.variables():
        return True
    return False


def _check_simple_substitutions(h: Equation, t: Equation) -> AnalysisResult | None:
    """Check if T can be obtained from H by setting variables equal.

    Tries both merge directions (v→u and u→v) at each step, plus two-step
    chaining (apply a second merge after the first).  All these specialisations
    are universally sound: if H[σ] = T then H implies T.
    """
    h_vars = sorted(h.variables())
    if len(h_vars) < 2:
        return None

    for i, v1 in enumerate(h_vars):
        for v2 in h_vars[i + 1 :]:
            for merged, survivor in ((v2, v1), (v1, v2)):
                step1 = h.substitute({merged: Term(NodeType.VAR, name=survivor)})
                if step1 == t:
                    return AnalysisResult(
                        ImplicationVerdict.TRUE,
                        "Phase 3",
                        f"T obtained from H by setting {merged}:={survivor}",
                    )
                # Two-step chaining: apply one more merge/rename to step1.
                # The target may be any var from step1 OR from T (enabling
                # renames like z→y after y was merged into x).
                step1_vars = sorted(step1.variables())
                t_vars = sorted(t.variables())
                candidate_targets = sorted(set(step1_vars) | set(t_vars))
                for m2 in step1_vars:
                    for s2 in candidate_targets:
                        if m2 == s2:
                            continue
                        step2 = step1.substitute({m2: Term(NodeType.VAR, name=s2)})
                        if step2 == t:
                            return AnalysisResult(
                                ImplicationVerdict.TRUE,
                                "Phase 3",
                                f"T obtained from H by {merged}:={survivor} then {m2}:={s2}",
                            )
    return None


def _iter_vars(term: Term) -> Iterator[str]:
    """Yield variable names in a term, including duplicates."""

    if term.node_type == NodeType.VAR:
        yield term.name
    else:
        lt, rt = term._lr()
        yield from _iter_vars(lt)
        yield from _iter_vars(rt)


def _detect_determined_operation(eq: Equation) -> tuple[list[list[int]], str] | None:
    """Detect if an equation completely determines the magma operation.

    Returns (table, name) if determined, None otherwise.
    Uses a 2-element magma for testing.
    """
    # Note: "left absorption" here means x = x*y (forces left projection).
    # This differs from Lean's StdEqn.leftAbsorption which is x*(x*y) = x*y
    # (the standard absorption law). The naming difference is intentional:
    # this function detects operation-determining equations.

    # Left absorption: x = x * y → forces left projection
    # Both children of OP must be vars, and the "other" var must differ.
    if (
        eq.lhs.node_type == NodeType.VAR
        and eq.rhs.node_type == NodeType.OP
        and eq.rhs.left is not None
        and eq.rhs.right is not None
        and eq.rhs.left.node_type == NodeType.VAR
        and eq.rhs.right.node_type == NodeType.VAR
        and eq.rhs.left.name == eq.lhs.name
        and eq.rhs.right.name != eq.lhs.name
    ):
        return [[0, 0], [1, 1]], "left projection (x*y=x)"

    # Also check reversed: x * y = x
    if (
        eq.rhs.node_type == NodeType.VAR
        and eq.lhs.node_type == NodeType.OP
        and eq.lhs.left is not None
        and eq.lhs.right is not None
        and eq.lhs.left.node_type == NodeType.VAR
        and eq.lhs.right.node_type == NodeType.VAR
        and eq.lhs.left.name == eq.rhs.name
        and eq.lhs.right.name != eq.rhs.name
    ):
        return [[0, 0], [1, 1]], "left projection (x*y=x)"

    # Right absorption: x = y * x → forces right projection
    if (
        eq.lhs.node_type == NodeType.VAR
        and eq.rhs.node_type == NodeType.OP
        and eq.rhs.right is not None
        and eq.rhs.right.node_type == NodeType.VAR
        and eq.rhs.right.name == eq.lhs.name
    ):
        rhs_left_var = eq.rhs.left
        if (
            rhs_left_var is not None
            and rhs_left_var.node_type == NodeType.VAR
            and rhs_left_var.name != eq.lhs.name
        ):
            return [[0, 1], [0, 1]], "right projection (x*y=y)"

    # Also check reversed: y * x = x
    if (
        eq.rhs.node_type == NodeType.VAR
        and eq.lhs.node_type == NodeType.OP
        and eq.lhs.right is not None
        and eq.lhs.right.node_type == NodeType.VAR
        and eq.lhs.right.name == eq.rhs.name
    ):
        lhs_left_var = eq.lhs.left
        if (
            lhs_left_var is not None
            and lhs_left_var.node_type == NodeType.VAR
            and lhs_left_var.name != eq.rhs.name
        ):
            return [[0, 1], [0, 1]], "right projection (x*y=y)"

    # Generalized constant law: LHS and RHS are both OP trees with disjoint variable sets,
    # AND each variable appears exactly once in the equation (no repeats).
    # When variables repeat (e.g. (x*y)*x), the disjoint condition alone is insufficient —
    # a 3-element counterexample exists. With unique variables, x*y=z*w style reasoning holds.
    if eq.lhs.node_type == NodeType.OP and eq.rhs.node_type == NodeType.OP:
        lhs_vars = eq.lhs.variables()
        rhs_vars = eq.rhs.variables()
        lhs_var_count = sum(1 for _ in _iter_vars(eq.lhs))
        rhs_var_count = sum(1 for _ in _iter_vars(eq.rhs))
        no_repeats = (lhs_var_count == len(lhs_vars)) and (rhs_var_count == len(rhs_vars))
        if len(lhs_vars & rhs_vars) == 0 and no_repeats:
            return [[0, 0], [0, 0]], "constant operation (x*y=c)"

    return None
