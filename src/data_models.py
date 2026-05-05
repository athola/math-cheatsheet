"""
Data models for equational theories competition.

Unified data structures for equations, problems, magmas, and counterexamples
used across the Python codebase (src/, tla/python/, experiments/).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import cast


class Property(Enum):
    """Common equational properties for magmas."""

    ASSOCIATIVE = "associative"
    COMMUTATIVE = "commutative"
    LEFT_IDENTITY = "left_identity"
    RIGHT_IDENTITY = "right_identity"
    BIDENTITY = "bidentity"  # Both left and right identity
    LEFT_INVERSE = "left_inverse"
    RIGHT_INVERSE = "right_inverse"
    INVERSE = "inverse"  # Both left and right inverse
    DISTRIBUTIVE = "distributive"
    IDEMPOTENT = "idempotent"
    ZERO = "zero"


@dataclass
class Equation:
    """Represents an equational law."""

    id: int
    latex: str
    name: str
    properties: list[Property]
    description: str = ""

    def __str__(self) -> str:
        return f"E{self.id}: {self.name}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "latex": self.latex,
            "name": self.name,
            "properties": [p.value for p in self.properties],
            "description": self.description,
        }


@dataclass
class Problem:
    """Represents an implication problem."""

    id: int
    equation_1_id: int
    equation_2_id: int
    answer: bool | None  # True if E1 implies E2, False otherwise
    difficulty: str  # "regular" or "hard"

    def __str__(self) -> str:
        return f"P{self.id}: Does E{self.equation_1_id} imply E{self.equation_2_id}?"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "equation_1": self.equation_1_id,
            "equation_2": self.equation_2_id,
            "answer": self.answer,
            "difficulty": self.difficulty,
        }


@dataclass
class AlgebraicEquation:
    """An algebraic equation with LHS and RHS terms (for formal checking)."""

    id: int
    lhs: str
    rhs: str

    def __str__(self) -> str:
        return f"{self.lhs} = {self.rhs}"


@dataclass(frozen=True)
class Magma:
    """A finite magma with carrier set and binary operation.

    Stores the Cayley table as a tuple-of-tuples (``operation[i][j] = i * j``).
    The dataclass is frozen and the table is hashable, so a constructed
    ``Magma`` cannot have its operation mutated post-hoc (S8 / regression
    #55: ``m.operation[0][0] = 99`` previously produced an invalid magma
    with no error). Callers may still pass ``list[list[int]]`` for
    convenience; ``__post_init__`` deep-copies into tuples via
    ``object.__setattr__`` (the standard escape hatch for frozen
    dataclasses).

    The carrier set is always ``range(size)``, exposed via the computed
    ``elements`` property so it cannot drift from ``size`` (regression #39).
    """

    size: int
    # Accepts lists or tuples at construction; normalised to tuples in
    # __post_init__ so the dataclass remains hashable and the table is
    # immutable for downstream consumers.
    operation: tuple[tuple[int, ...], ...]

    def __post_init__(self):
        if self.size < 1:
            raise ValueError(f"Magma size must be at least 1, got {self.size}")
        if len(self.operation) != self.size:
            raise ValueError(
                f"Operation table must have {self.size} rows, got {len(self.operation)}"
            )
        for i, row in enumerate(self.operation):
            if len(row) != self.size:
                raise ValueError(f"Row {i} must have {self.size} columns, got {len(row)}")
            for j, val in enumerate(row):
                if not (0 <= val < self.size):
                    raise ValueError(f"Entry [{i}][{j}]={val} out of range [0, {self.size})")
        # Freeze the table: deep-convert any list-of-list to tuple-of-tuple
        # so callers who pass a mutable nested list cannot retroactively
        # invalidate this magma. Frozen dataclasses forbid normal
        # assignment in __post_init__ — object.__setattr__ is the
        # standard escape hatch for one-shot normalisation.
        if not (
            isinstance(self.operation, tuple)
            and all(isinstance(row, tuple) for row in self.operation)
        ):
            object.__setattr__(
                self,
                "operation",
                tuple(tuple(row) for row in self.operation),
            )

    @property
    def elements(self) -> tuple[int, ...]:
        """Carrier set, always ``(0, 1, ..., size-1)``.

        Previously a stored field (duplicated ``range(size)`` at every call
        site). Exposed as a property so the invariant is expressed in one
        place and cannot drift from ``size``.
        """
        return tuple(range(self.size))

    def op(self, a: int, b: int) -> int:
        return self.operation[a][b]

    def is_associative(self) -> bool:
        for a in range(self.size):
            for b in range(self.size):
                for c in range(self.size):
                    if self.op(self.op(a, b), c) != self.op(a, self.op(b, c)):
                        return False
        return True

    def is_commutative(self) -> bool:
        for a in range(self.size):
            for b in range(self.size):
                if self.op(a, b) != self.op(b, a):
                    return False
        return True

    def has_identity(self) -> int | None:
        for e in range(self.size):
            if all(self.op(e, a) == a and self.op(a, e) == a for a in range(self.size)):
                return e
        return None

    def is_idempotent(self) -> bool:
        return all(self.op(a, a) == a for a in range(self.size))

    def cayley_table_str(self) -> str:
        result = "   " + " ".join(f"{i}" for i in range(self.size)) + "\n"
        result += "  " + "-" * (2 * self.size + 1) + "\n"
        for i in range(self.size):
            result += f"{i}| " + " ".join(f"{self.op(i, j)}" for j in range(self.size)) + "\n"
        return result

    def to_dict_operation(self) -> dict[str, int]:
        """Convert Cayley table to dict representation for JSON serialization."""
        return {
            f"{a},{b}": self.operation[a][b] for a in range(self.size) for b in range(self.size)
        }

    @classmethod
    def from_dict_operation(
        cls,
        carrier: Sequence[int] | None,
        op_dict: dict[tuple[int, int], int],
    ) -> "Magma":
        """Create from dict-based operation (counterexample_db format).

        S9 (#55): the ``carrier`` parameter has exactly one legal value —
        ``range(size)`` — because :class:`Magma` requires a 0-indexed
        contiguous carrier. The parameter is now optional: when ``None``
        the size is inferred from ``op_dict``'s keys. When a non-None
        carrier is supplied, it must equal ``range(size)`` or
        ``ValueError`` is raised. New callers should pass ``carrier=None``
        and let the size derive from the dict.
        """
        if carrier is not None:
            size = len(carrier)
        else:
            # Infer size from the largest key. The keys must already form
            # a contiguous square for the validation below to succeed.
            keys = list(op_dict.keys())
            if not keys:
                raise ValueError("from_dict_operation: op_dict is empty")
            size = max(max(a, b) for a, b in keys) + 1
        expected_keys = {(a, b) for a in range(size) for b in range(size)}
        missing = expected_keys - set(op_dict.keys())
        if missing:
            raise ValueError(f"Missing operation entries for pairs: {sorted(missing)}")
        table_rows = [[0] * size for _ in range(size)]
        for (a, b), result in op_dict.items():
            table_rows[a][b] = result
        if carrier is not None and list(carrier) != list(range(size)):
            raise ValueError(
                f"Magma carrier must be range(size); got {list(carrier)}."
                " Re-index your operation table so keys are 0..size-1, or"
                " pass carrier=None to infer size from op_dict."
            )
        return cls(
            size=size,
            operation=cast(
                tuple[tuple[int, ...], ...],
                tuple(tuple(row) for row in table_rows),
            ),
        )

    def to_tla(self) -> str:
        """Convert to TLA+ representation."""
        op_str = ", ".join(
            f"<<{a}, {b}>> |-> {self.operation[a][b]}"
            for a in range(self.size)
            for b in range(self.size)
        )
        return f"[{op_str}]"


@dataclass
class Counterexample:
    """A counterexample to an implication E1 => E2."""

    premise_id: int
    conclusion_id: int
    magma: Magma
    red_flags: set[str] = field(default_factory=set)
    assignment: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "premise_id": self.premise_id,
            "conclusion_id": self.conclusion_id,
            "magma": {
                "carrier": self.magma.elements,
                "operation": [
                    {"a": a, "b": b, "result": self.magma.operation[a][b]}
                    for a in range(self.magma.size)
                    for b in range(self.magma.size)
                ],
            },
            "red_flags": list(self.red_flags),
            "assignment": self.assignment,
        }


# Synthetic equation definitions based on common magma properties.
# Tuple, not list, so the catalog cannot be mutated by callers (#41).
SYNTHETIC_EQUATIONS: tuple["Equation", ...] = (
    Equation(
        1,
        r"(x * y) * z = x * (y * z)",
        "Associativity",
        [Property.ASSOCIATIVE],
        "Associative property",
    ),
    Equation(2, r"x * y = y * x", "Commutativity", [Property.COMMUTATIVE], "Commutative property"),
    Equation(
        3,
        r"\exists e \forall x: e * x = x",
        "Left Identity",
        [Property.LEFT_IDENTITY],
        "Left identity element exists",
    ),
    Equation(
        4,
        r"\exists e \forall x: x * e = x",
        "Right Identity",
        [Property.RIGHT_IDENTITY],
        "Right identity element exists",
    ),
    Equation(
        5,
        r"\exists e \forall x: e * x = x * e = x",
        "Two-sided Identity",
        [Property.BIDENTITY],
        "Two-sided identity element",
    ),
    Equation(
        6,
        r"\exists e \forall x \exists x^{-1}: x^{-1} * x = e",
        "Left Inverse",
        [Property.LEFT_INVERSE, Property.BIDENTITY],
        "Left inverse exists",
    ),
    Equation(
        7,
        r"\exists e \forall x \exists x^{-1}: x * x^{-1} = e",
        "Right Inverse",
        [Property.RIGHT_INVERSE, Property.BIDENTITY],
        "Right inverse exists",
    ),
    Equation(
        8,
        r"\forall x \exists x^{-1}: x * x^{-1} = x^{-1} * x = e",
        "Two-sided Inverse",
        [Property.INVERSE, Property.BIDENTITY],
        "Two-sided inverse",
    ),
    Equation(9, r"x * x = x", "Idempotence", [Property.IDEMPOTENT], "Idempotent property"),
    Equation(
        10, r"\exists 0 \forall x: 0 * x = 0", "Left Zero", [Property.ZERO], "Left zero element"
    ),
    Equation(
        11,
        r"x * (y * z) = (x * y) * (x * z)",
        "Left Self-Distributive",
        [Property.DISTRIBUTIVE],
        "Left self-distributive property",
    ),
    Equation(
        12,
        r"(x * y) * z = (x * z) * (y * z)",
        "Right Self-Distributive",
        [Property.DISTRIBUTIVE],
        "Right self-distributive property",
    ),
    # Groups
    Equation(
        13,
        "Associative + Two-sided Identity + Two-sided Inverse",
        "Group Axioms",
        [Property.ASSOCIATIVE, Property.BIDENTITY, Property.INVERSE],
        "Full group structure",
    ),
    # Semi-groups
    Equation(
        14, "Associative operation only", "Semigroup", [Property.ASSOCIATIVE], "Semigroup structure"
    ),
    # Monoids
    Equation(
        15,
        "Associative + Two-sided Identity",
        "Monoid",
        [Property.ASSOCIATIVE, Property.BIDENTITY],
        "Monoid structure",
    ),
    # Abelian groups
    Equation(
        16,
        "Group + Commutative",
        "Abelian Group",
        [Property.ASSOCIATIVE, Property.BIDENTITY, Property.INVERSE, Property.COMMUTATIVE],
        "Abelian group structure",
    ),
)
