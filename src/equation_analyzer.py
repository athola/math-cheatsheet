"""Equation structure analyzer for equational implication problems.

Implements the v3 cheatsheet decision procedure as computable functions:
- Phase 1: Instant decisions (tautology, collapse, identity)
- Phase 2: Variable analysis (new variables in target)
- Phase 3: Substitution detection (variable merging)
- Phase 4: Counterexample testing (canonical + exhaustive magmas)
- Phase 4b: Exhaustive 2-element search
- Phase 5: Determined operation detection (absorption, constant law)
- Phase 6: Rewrite analysis (orient H as a rule, reduce T to a normal form)
- Phase 7: Structural heuristics (side-swap, depth, op-count)
- Phase 8: Default (inconclusive → FALSE)

Based on techniques from the Equational Theories Project (Tao et al., 2024-2025)
and Birkhoff's completeness theorem for equational logic.
"""

from __future__ import annotations

import functools
import itertools
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from term import (
    NodeType,
    Term,
    op,
    parse_equation_terms,
    var,
)

logger = logging.getLogger(__name__)

# Observability of Phase 6 rewriting (NEW-I1 / regression #60).
# Callers that care about the *cause* of a rewrite stopping (normal form
# vs. step-budget exhaustion vs. cycle detection) can inspect this status
# alongside the rewritten term.
RewriteStatus = Literal["normal_form", "budget", "cycle"]

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


@dataclass(frozen=True)
class CounterexampleMagma:
    """A small magma stamped onto a single Cayley table.

    Frozen and tuple-fielded so module-level constants like
    :data:`CANONICAL_MAGMAS` cannot be mutated by callers and so that
    instances are hashable / cache-friendly (NEW-I3 / regression #58).
    The table is stored as ``tuple[tuple[int, ...], ...]`` and ``properties``
    as ``tuple[str, ...]``.
    """

    name: str
    size: int
    table: tuple[tuple[int, ...], ...]
    properties: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Normalise list-of-list / list-of-str inputs to tuple form so
        # callers that wrote constants with literal lists still compose.
        # The standard escape hatch for frozen dataclasses (object.__setattr__)
        # is required; assignment via self.field = ... raises FrozenInstanceError.
        if not (
            isinstance(self.table, tuple) and all(isinstance(row, tuple) for row in self.table)
        ):
            object.__setattr__(self, "table", tuple(tuple(row) for row in self.table))
        if not isinstance(self.properties, tuple):
            object.__setattr__(self, "properties", tuple(self.properties))

    def satisfies(self, eq: Equation) -> bool:
        # holds_in expects a list-of-list interface; tuples honour the
        # same indexing protocol so no conversion is needed.
        return eq.holds_in(self.table, self.size)  # type: ignore[arg-type]


# The 7 canonical magmas from the v3 cheatsheet.
# Exposed as a tuple so the module-level constant cannot be mutated by callers
# (regression #41). Iteration semantics are identical to the former list.
CANONICAL_MAGMAS: tuple[CounterexampleMagma, ...] = (
    CounterexampleMagma(
        "LP (Left Projection)",
        2,
        ((0, 0), (1, 1)),
        ("associative", "idempotent", "NOT commutative"),
    ),
    CounterexampleMagma(
        "RP (Right Projection)",
        2,
        ((0, 1), (0, 1)),
        ("associative", "idempotent", "NOT commutative"),
    ),
    CounterexampleMagma(
        "C0 (Constant Zero)",
        2,
        ((0, 0), (0, 0)),
        ("associative", "commutative", "NOT idempotent"),
    ),
    CounterexampleMagma(
        "XR (XOR / Z2 addition)",
        2,
        ((0, 1), (1, 0)),
        ("commutative", "associative", "has identity", "NOT idempotent"),
    ),
    CounterexampleMagma(
        "CM (Commutative Non-Associative)",
        2,
        ((1, 1), (1, 0)),
        ("commutative", "NOT associative"),
    ),
    CounterexampleMagma(
        "N1 (Non-comm Non-assoc)",
        2,
        ((0, 0), (1, 0)),
        ("NOT commutative", "NOT associative"),
    ),
    CounterexampleMagma(
        "Z3 (Z/3Z addition)",
        3,
        ((0, 1, 2), (1, 2, 0), (2, 0, 1)),
        ("commutative", "associative", "has identity", "NOT idempotent"),
    ),
)

# All 16 possible 2-element magma tables (tuple to prevent mutation — #41).
ALL_SIZE_2_MAGMAS: tuple[CounterexampleMagma, ...] = tuple(
    CounterexampleMagma(
        f"M2_{i:04b}",
        2,
        ((i >> 3 & 1, i >> 2 & 1), (i >> 1 & 1, i & 1)),
    )
    for i in range(16)
)


# NEW-I5 (#58): bounded cache so long-running consumers (notebooks, batch
# runs over multiple corpora, server processes) cannot leak memory linearly
# in the number of distinct equations seen. 8192 is plenty for a single
# 4.7K-equation corpus and keeps a typical 8-byte-key entry under ~100KB
# total even at saturation.
@functools.lru_cache(maxsize=8192)
def _size_2_satisfactions(eq: Equation) -> frozenset[int]:
    """Indices of ``ALL_SIZE_2_MAGMAS`` that satisfy ``eq``.

    Cached per Equation (the dataclass is frozen and hashable) so that
    Phase 4b does not re-evaluate the same equation against the 16 size-2
    magmas on every pair it appears in. For a full-corpus run over
    ~4.7K equations, this turns the cost from O(n_pairs × 16 × evals)
    into O(n_equations × 16 × evals + n_pairs). The cache is per-process
    only — it does not persist across runs, so cold-start runs pay the
    full per-equation cost (S12 / regression #62). Bounded to 8192
    entries so long-running consumers don't grow unbounded (NEW-I5 / #58).
    """
    return frozenset(
        i
        for i, magma in enumerate(ALL_SIZE_2_MAGMAS)
        if eq.holds_in(magma.table, magma.size)  # type: ignore[arg-type]
    )


# --- Analysis Functions ---


class ImplicationVerdict(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AnalysisResult:
    """Outcome of one ``analyze_implication`` call.

    Frozen (NEW-I3 / regression #58) so downstream consumers cannot mutate
    a verdict after the fact. All fields are constructed once and read-only.
    """

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

    # Phase 4b: Exhaustive 2-element search (cached per equation — #34).
    # Look up the set of size-2 magmas satisfying H and T once each, then
    # subtract: any magma satisfying H but not T is a counterexample.
    h_sat = _size_2_satisfactions(h)
    t_sat = _size_2_satisfactions(t)
    diff = h_sat - t_sat
    if diff:
        magma = ALL_SIZE_2_MAGMAS[min(diff)]  # deterministic: smallest index
        return AnalysisResult(
            ImplicationVerdict.FALSE,
            "Phase 4b",
            f"Counterexample: {magma.name} table={magma.table}",
            magma,
        )

    # Phase 6: Rewrite analysis — orient H as a rewrite rule and reduce T
    rewrite_proof = _phase6_rewrite(h, t)
    if rewrite_proof is not None:
        return rewrite_proof

    # Phase 7: Structural heuristics
    # 7a. Side-swap identity: ``a = b`` and ``b = a`` are the same universally
    # quantified law. If T is H with LHS/RHS swapped, return TRUE. This is not
    # caught by Phase 1a (which tests h == t strictly) or Phase 3 (which only
    # merges variables, not sides).
    if h.lhs == t.rhs and h.rhs == t.lhs:
        return AnalysisResult(
            ImplicationVerdict.TRUE,
            "Phase 7",
            "T is H with LHS/RHS swapped — same equational law",
        )

    # 7b. Depth divergence: target is too deep to be reached by substitution.
    if t.max_depth() > h.max_depth() + 1:
        return AnalysisResult(
            ImplicationVerdict.FALSE,
            "Phase 7",
            f"Target depth ({t.max_depth()}) >> hypothesis depth ({h.max_depth()})",
        )

    # 7c. Op-count divergence: analog of depth for wide-but-shallow terms.
    # Substitution of a variable with a k-op subterm can at most double op
    # count per step; with one step allowed, ``T.ops > 2*H.ops + 2`` exceeds
    # what any single substitution can produce, so H cannot imply T.
    #
    # Soundness precondition (NEW-C1): the bound assumes each variable in H
    # appears once. When a variable repeats k times, substituting it with a
    # term of size m amplifies T.ops by ``k*m`` rather than ``m``, breaking
    # the bound. Gate the rule on globally-unique variable occurrences so the
    # broken case (e.g. H = ``x*x = x``) cannot reach this branch.
    if _h_vars_unique(h) and t.total_ops() > 2 * h.total_ops() + 2:
        return AnalysisResult(
            ImplicationVerdict.FALSE,
            "Phase 7",
            f"Target op count ({t.total_ops()}) >> hypothesis op count ({h.total_ops()})",
        )

    return AnalysisResult(
        ImplicationVerdict.UNKNOWN,
        "Phase 8",
        # S11 (#62): keep the verdict and the reason narrative consistent
        # — Phase 8 emits UNKNOWN to signal "no rule fired", and the
        # caller (DecisionProcedure) decides whether to treat that as
        # FALSE. Embedding "default FALSE" in this analyzer's reason
        # leaks the upstream policy and contradicts the verdict.
        "Inconclusive — no rule fired",
    )


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


# --- Phase 6 helpers: rewrite analysis ---

# Cap on rewrite steps per orientation per side of T.
# Depth 8 is generous for single-rule systems (idempotence closes in 2 steps on
# depth-3 terms; associativity normalisation is bounded by term size) and keeps
# the worst case on a 10-token target well under a millisecond.
_PHASE6_MAX_STEPS = 8


def _match_pattern(pattern: Term, target: Term, bindings: dict[str, Term]) -> bool:
    """Non-linear first-order match: is ``target`` an instance of ``pattern``?

    The matcher is *non-linear in the pattern*: every occurrence of the
    same pattern variable must bind to the same target sub-term. That
    non-linearity is what enables rules such as ``x*x → x`` (the two
    leaf ``x`` positions must collapse to the same sub-term). A purely
    linear matcher would miss them.

    Extends ``bindings`` in place on success. On failure the dict is
    rolled back to the snapshot captured on entry (NEW-I2 / regression
    #60), so it is safe to reuse a single ``bindings`` dict across
    sibling sub-matches: the right-side recursion no longer leaks
    partial left-side bindings if the right side fails. Today's
    ``_rewrite_once`` allocates a fresh dict per call and is unaffected,
    but any AC-matching extension or pattern-cache reuse would have
    silently produced wrong matches without this snapshot/restore.
    """
    if pattern.node_type == NodeType.VAR:
        existing = bindings.get(pattern.name)
        if existing is None:
            bindings[pattern.name] = target
            return True
        return existing == target
    # pattern is an OP; target must also be an OP to match.
    if target.node_type != NodeType.OP:
        return False
    p_l, p_r = pattern._lr()
    t_l, t_r = target._lr()
    snapshot = bindings.copy()
    if not _match_pattern(p_l, t_l, bindings):
        # Left side itself rolls back on failure; nothing extra to do.
        return False
    if not _match_pattern(p_r, t_r, bindings):
        # Right side failed but left side may have committed bindings —
        # restore the snapshot so the caller sees a clean state.
        bindings.clear()
        bindings.update(snapshot)
        return False
    return True


def _rewrite_once(term: Term, rule_lhs: Term, rule_rhs: Term) -> Term | None:
    """Apply rule ``rule_lhs → rule_rhs`` at the outermost leftmost position.

    Returns the rewritten term, or None if no position matches. Tries the
    whole term first, then the left child, then the right child. This is the
    standard leftmost-outermost (normal-order) rewrite strategy — it avoids
    wasted work on sub-terms that will be rewritten at the parent.

    S2 (#63): uses Term._lr() for OP-children access so the malformed-OP
    invariant is enforced consistently with the rest of this module
    (Term.__post_init__ already validates at construction; _lr provides
    the runtime access guard for any defensive remaining call site).
    """
    bindings: dict[str, Term] = {}
    if _match_pattern(rule_lhs, term, bindings):
        return rule_rhs.substitute(bindings)
    if term.node_type == NodeType.OP:
        left, right = term._lr()
        left_new = _rewrite_once(left, rule_lhs, rule_rhs)
        if left_new is not None:
            return op(left_new, right)
        right_new = _rewrite_once(right, rule_lhs, rule_rhs)
        if right_new is not None:
            return op(left, right_new)
    return None


def _rewrite_to_normal_form(
    term: Term, rule_lhs: Term, rule_rhs: Term, max_steps: int = _PHASE6_MAX_STEPS
) -> tuple[Term, RewriteStatus]:
    """Apply the rule until nothing matches, a cycle is detected, or the budget is spent.

    Returns ``(final_term, status)`` where ``status`` is one of:

    - ``"normal_form"`` — no further match exists; rewriting is complete.
    - ``"cycle"`` — the next rewrite would re-enter a previously seen term;
      the rule never terminates from here, so rewriting was aborted.
    - ``"budget"`` — ``max_steps`` was exhausted without reaching either
      condition; the result may not be a normal form.

    Reporting the cause of termination (NEW-I1 / regression #60) lets the
    caller distinguish "no further reductions exist" from "we ran out of
    steps" and tune ``max_steps`` if the budget is biting in practice.
    Phase 6 verdict TRUE remains sound (each rewrite step is sound), but
    silently missing implications because of a budget hit is now
    observable at DEBUG level.
    """
    seen: set[Term] = set()
    current = term
    for _ in range(max_steps):
        if current in seen:
            return current, "cycle"
        seen.add(current)
        next_term = _rewrite_once(current, rule_lhs, rule_rhs)
        if next_term is None:
            return current, "normal_form"
        current = next_term
    return current, "budget"


def _rule_is_sound(rule_lhs: Term, rule_rhs: Term) -> bool:
    """A rewrite rule is sound iff every variable on the RHS appears on the LHS.

    Otherwise the rule would introduce fresh (unbound) variables — applying
    ``x → y*x`` to a concrete term would invent a ``y`` that isn't in the
    original universal quantification. We silently skip unsound orientations
    rather than signal an error, because many equations have at least one
    orientation that is sound.
    """
    return rule_rhs.variables() <= rule_lhs.variables()


def _phase6_rewrite(h: Equation, t: Equation) -> AnalysisResult | None:
    """Use H as a bidirectional rewrite rule to collapse T to a tautology.

    Tries both orientations of H (LHS→RHS and RHS→LHS). For each sound
    orientation, reduces both sides of T to a normal form; if the two sides
    reach the same term, the target holds as an instance of H-derivation.
    Returns the phase result on success, or None if neither orientation
    closes T.

    Logs at DEBUG level when an orientation hits the rewrite step budget
    (NEW-I1 / #60) so practitioners can identify implications that might
    be discoverable by raising ``_PHASE6_MAX_STEPS``.
    """
    for lhs, rhs, label in (
        (h.lhs, h.rhs, "LHS→RHS"),
        (h.rhs, h.lhs, "RHS→LHS"),
    ):
        if not _rule_is_sound(lhs, rhs):
            continue
        reduced_t_lhs, status_lhs = _rewrite_to_normal_form(t.lhs, lhs, rhs)
        reduced_t_rhs, status_rhs = _rewrite_to_normal_form(t.rhs, lhs, rhs)
        if "budget" in (status_lhs, status_rhs):
            logger.debug(
                "Phase 6 budget exhausted (%s) on H=%s, T=%s — verdict may be incomplete",
                label,
                h,
                t,
            )
        if reduced_t_lhs == reduced_t_rhs:
            return AnalysisResult(
                ImplicationVerdict.TRUE,
                "Phase 6",
                f"T closes under H-rewrite ({label}): both sides normalise to {reduced_t_lhs}",
            )
    return None


def _iter_vars(term: Term) -> Iterator[str]:
    """Yield variable names in a term, including duplicates.

    S5 (#63): uses a structural ``match`` on ``term.node_type`` instead
    of an if/else chain. The project already targets py3.10+ via the
    ``X | None`` syntax, so match statements are in scope.
    """
    match term.node_type:
        case NodeType.VAR:
            yield term.name
        case NodeType.OP:
            lt, rt = term._lr()
            yield from _iter_vars(lt)
            yield from _iter_vars(rt)


def _h_vars_unique(h: Equation) -> bool:
    """True iff every variable in ``h`` appears exactly once across both sides.

    Phase 7c's ``2*ops + 2`` bound is sound only under this condition. When a
    variable repeats ``k`` times in H, substituting it with a term of size
    ``m`` adds ``k*m`` ops rather than ``m`` ops, and the bound can wrongly
    rule out valid implications (NEW-C1 reproducer: H = ``x*x = x``).
    """
    occurrences = list(_iter_vars(h.lhs)) + list(_iter_vars(h.rhs))
    return len(occurrences) == len(set(occurrences))


def _detect_determined_operation(eq: Equation) -> tuple[list[list[int]], str] | None:
    """Detect if an equation completely determines the magma operation.

    Returns (table, name) if determined, None otherwise.
    Uses a 2-element magma for testing.

    Notes:
        "left absorption" here means ``x = x*y`` (forces left projection).
        This differs from Lean's ``StdEqn.leftAbsorption`` which is the
        standard absorption law ``x*(x*y) = x*y``. Naming difference is
        intentional: this function detects operation-determining
        equations, not absorption proper.

    S1 (#63): the four absorption branches (x=x*y, x*y=x, x=y*x, y*x=x)
    are collapsed into a single canonical-orientation pass that orders
    the equation as ``(var_side, op_side)`` regardless of which side of
    ``=`` the variable came from. This drops ~30 lines of repeated
    AST-shape checks down to one shared shape match.
    """
    # Canonicalise: identify which side is the bare variable. If both
    # sides are OPs we fall through to the constant-operation branch.
    var_side, op_side = _canonical_var_op_sides(eq)
    if var_side is not None and op_side is not None:
        # Both children of op_side must be variables for a determined-
        # operation conclusion. The "anchor" variable is var_side.name;
        # it must appear once in op_side, and the partner variable must
        # differ from it (otherwise we have x = x*x — idempotence — not
        # a determined operation).
        anchor = var_side.name
        op_left, op_right = op_side._lr()
        if op_left.node_type == NodeType.VAR and op_right.node_type == NodeType.VAR:
            # Left projection: x = x*y or x*y = x — anchor matches op.left,
            # partner is op.right and differs.
            if op_left.name == anchor and op_right.name != anchor:
                return [[0, 0], [1, 1]], "left projection (x*y=x)"
            # Right projection: x = y*x or y*x = x — anchor matches op.right,
            # partner is op.left and differs.
            if op_right.name == anchor and op_left.name != anchor:
                return [[0, 1], [0, 1]], "right projection (x*y=y)"

    # Generalized constant law: LHS and RHS are both OP trees with disjoint
    # variable sets, AND each variable appears exactly once. When variables
    # repeat (e.g. (x*y)*x), the disjoint condition alone is insufficient —
    # a 3-element counterexample exists.
    if eq.lhs.node_type == NodeType.OP and eq.rhs.node_type == NodeType.OP:
        lhs_vars = eq.lhs.variables()
        rhs_vars = eq.rhs.variables()
        lhs_var_count = sum(1 for _ in _iter_vars(eq.lhs))
        rhs_var_count = sum(1 for _ in _iter_vars(eq.rhs))
        no_repeats = (lhs_var_count == len(lhs_vars)) and (rhs_var_count == len(rhs_vars))
        if len(lhs_vars & rhs_vars) == 0 and no_repeats:
            return [[0, 0], [0, 0]], "constant operation (x*y=c)"

    return None


def _canonical_var_op_sides(eq: Equation) -> tuple[Term | None, Term | None]:
    """Return ``(var_side, op_side)`` if the equation has the form
    ``var = op`` or ``op = var``; otherwise ``(None, None)``.

    S1 (#63) helper: collapses the four "which side is the variable"
    branches that previously duplicated absorption detection logic.
    """
    if eq.lhs.node_type == NodeType.VAR and eq.rhs.node_type == NodeType.OP:
        return eq.lhs, eq.rhs
    if eq.rhs.node_type == NodeType.VAR and eq.lhs.node_type == NodeType.OP:
        return eq.rhs, eq.lhs
    return None, None
