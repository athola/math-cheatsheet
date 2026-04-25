"""Parse and analyze all 4694 ETP equations.

Each equation is a universally quantified identity over magmas (sets with
a binary operation ◇). Line N of equations.txt is Equation N.

Structural features extracted:
- Variable set and count
- Term depth and operation count
- Collapse detection (forces |M|=1)
- Tautology detection (LHS == RHS)
- Whether LHS is a single variable
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from implication_oracle import ImplicationOracle
from term import Term, op, parse_equation_terms, var

__all__ = [
    "Term",
    "op",
    "var",
    "parse_equation",
    "Equation",
    "ETPEquations",
    "StructuralClass",
]

StructuralClass = Literal["tautology", "collapse", "trivial_lhs", "trivial_rhs", "balanced"]


@dataclass
class Equation:
    """A parsed equation with structural metadata."""

    id: int
    text: str
    lhs: Term
    rhs: Term

    # Cached structural features
    variables: frozenset[str] = field(default_factory=frozenset)
    var_count: int = 0
    max_depth: int = 0
    total_ops: int = 0
    lhs_is_var: bool = False
    rhs_is_var: bool = False
    is_tautology: bool = False

    def __post_init__(self):
        self.variables = self.lhs.variables() | self.rhs.variables()
        self.var_count = len(self.variables)
        self.max_depth = max(self.lhs.depth(), self.rhs.depth())
        self.total_ops = self.lhs.size() + self.rhs.size()
        self.lhs_is_var = self.lhs.is_var
        self.rhs_is_var = self.rhs.is_var
        self.is_tautology = self.lhs == self.rhs


def parse_equation(eq_id: int, text: str) -> Equation:
    """Parse an equation string like ``x ◇ y = y ◇ x``."""
    text = text.strip()
    try:
        lhs, rhs = parse_equation_terms(text)
    except ValueError as exc:
        raise ValueError(f"Failed to parse equation {eq_id}: {exc}") from exc
    return Equation(id=eq_id, text=text, lhs=lhs, rhs=rhs)


class ETPEquations:
    """All 4694 ETP equations, parsed and indexed."""

    def __init__(self, equations_path: str | Path):
        self.equations: dict[int, Equation] = {}
        self._load(Path(equations_path))

    def _load(self, path: Path):
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    self.equations[i] = parse_equation(i, line)

    def __getitem__(self, eq_id: int) -> Equation:
        return self.equations[eq_id]

    def __len__(self) -> int:
        return len(self.equations)

    def __contains__(self, eq_id: int) -> bool:
        return eq_id in self.equations

    def ids(self) -> list[int]:
        return sorted(self.equations.keys())

    def is_collapse_structural(self, eq_id: int) -> bool:
        """Detect collapse equations from structure alone.

        A collapse equation forces |M|=1. Key patterns:
        - x = y (distinct vars equated directly)
        - x = y ◇ z (var equals op of two other vars)
        - More complex: LHS is a variable, RHS contains variables not in LHS
          and the equation forces all elements equal.

        Conservative approach: if LHS is a single variable and RHS introduces
        a new variable not in LHS, this MAY be collapse. But we need to be
        more careful.

        The definitive test: an equation is collapse iff it's satisfied only
        by magmas of size 1. We check this against the oracle externally.
        """
        eq = self.equations[eq_id]

        # x = y pattern: two distinct variables equated
        if eq.lhs.is_var and eq.rhs.is_var and eq.lhs.name != eq.rhs.name:
            return True

        # x = y ◇ z where y,z are vars not equal to x
        if eq.lhs.is_var and not eq.rhs.is_var:
            lhs_vars = eq.lhs.variables()
            rhs_vars = eq.rhs.variables()
            new_vars = rhs_vars - lhs_vars
            # If RHS has 2+ new vars AND it's a single operation, likely collapse
            if len(new_vars) >= 2 and eq.rhs.size() == 1:
                return True

        # Symmetric: y ◇ z = x
        if eq.rhs.is_var and not eq.lhs.is_var:
            lhs_vars = eq.lhs.variables()
            rhs_vars = eq.rhs.variables()
            new_vars = lhs_vars - rhs_vars
            if len(new_vars) >= 2 and eq.lhs.size() == 1:
                return True

        return False

    def vars_in_target_not_in_hypothesis(self, h_id: int, t_id: int) -> frozenset[str]:
        """Variables in target equation not present in hypothesis."""
        h = self.equations[h_id]
        t = self.equations[t_id]
        return t.variables - h.variables

    def classify_structural(self, eq_id: int) -> StructuralClass:
        """Classify an equation by structural features alone (no oracle).

        Categories:
        - tautology: LHS == RHS (e.g. x = x)
        - collapse: forces |M|=1 (detected structurally)
        - trivial_lhs: LHS is a single variable (not tautology/collapse)
        - trivial_rhs: RHS is a single variable (not tautology/collapse)
        - balanced: both sides have operations
        """
        eq = self.equations[eq_id]
        if eq.is_tautology:
            return "tautology"
        if self.is_collapse_structural(eq_id):
            return "collapse"
        if eq.lhs_is_var:
            return "trivial_lhs"
        if eq.rhs_is_var:
            return "trivial_rhs"
        return "balanced"

    def is_substitution_instance(self, h_id: int, t_id: int) -> bool:
        """Check if target can be obtained from hypothesis by variable merging."""
        h = self.equations[h_id]
        t = self.equations[t_id]

        h_vars = sorted(h.variables)
        if len(h_vars) < 2:
            return False

        # Try all pairwise variable merges
        for i, v1 in enumerate(h_vars):
            for v2 in h_vars[i + 1 :]:
                mapping = {v2: var(v1)}
                specialized = Equation(
                    id=0,
                    text="",
                    lhs=h.lhs.substitute(mapping),
                    rhs=h.rhs.substitute(mapping),
                )
                if specialized.lhs == t.lhs and specialized.rhs == t.rhs:
                    return True
        return False


class ETPDataset:
    """Unified query interface combining ETPEquations + ImplicationOracle.

    Provides one-stop access to structural features, implication queries,
    and classifications for the full ETP dataset.
    """

    def __init__(
        self,
        equations_path: str | Path = "research/data/etp/equations.txt",
        implications_path: str | Path = "research/data/etp/implications.csv",
    ):
        self.equations = ETPEquations(equations_path)
        self.oracle = ImplicationOracle(implications_path)

    def implies(self, hypothesis_id: int, target_id: int) -> bool | None:
        """Query whether hypothesis implies target."""
        result: bool | None = self.oracle.query(hypothesis_id, target_id)
        return result

    def classify(self, eq_id: int) -> str:
        """Oracle-based classification (collapse/tautology/weak/mid/strong)."""
        result: str = self.oracle.classify(eq_id)
        return result

    def get_equation(self, eq_id: int) -> Equation:
        """Retrieve the parsed equation object."""
        return self.equations[eq_id]

    def equation_info(self, eq_id: int) -> dict:
        """Return combined structural + oracle info for an equation."""
        eq = self.equations[eq_id]
        return {
            "id": eq_id,
            "text": eq.text,
            "var_count": eq.var_count,
            "max_depth": eq.max_depth,
            "total_ops": eq.total_ops,
            "is_tautology": eq.is_tautology,
            "variables": sorted(eq.variables),
            "structural_class": self.equations.classify_structural(eq_id),
            "oracle_class": self.oracle.classify(eq_id),
            "implies_count": self.oracle.row_true_count(eq_id),
            "implied_by_count": self.oracle.col_true_count(eq_id),
        }

    def summary(self) -> dict:
        """Return dataset-level summary statistics."""
        oracle_counts: Counter[str] = Counter()
        structural_counts: Counter[str] = Counter()
        for eq_id in self.equations.ids():
            oracle_counts[self.oracle.classify(eq_id)] += 1
            structural_counts[self.equations.classify_structural(eq_id)] += 1

        return {
            "total_equations": len(self.equations),
            "matrix_shape": self.oracle.shape,
            "classification_counts": dict(oracle_counts),
            "structural_counts": dict(structural_counts),
        }


if __name__ == "__main__":
    eqs = ETPEquations("research/data/etp/equations.txt")
    print(f"Loaded {len(eqs)} equations")

    # Show some examples
    for i in [1, 2, 3, 4, 5, 6, 7, 43, 46, 4512]:
        if i in eqs:
            eq = eqs[i]
            print(f"  E{i}: {eq.text}  (vars={eq.var_count} depth={eq.max_depth})")

    # Count structural collapse detection
    structural_collapse = sum(1 for i in eqs.ids() if eqs.is_collapse_structural(i))
    print(f"\nStructural collapse detection: {structural_collapse}")

    # Structural classification distribution
    struct_classes: Counter[str] = Counter()
    for eq_id in eqs.ids():
        struct_classes[eqs.classify_structural(eq_id)] += 1
    print("\nStructural classification:")
    for cls, count in struct_classes.most_common():
        print(f"  {cls}: {count}")
