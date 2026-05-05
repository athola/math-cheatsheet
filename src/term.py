"""Canonical Term AST and parser (issue #27).

Replaces the independent Term/parser implementations that previously lived
in ``equation_analyzer.py`` and ``etp_equations.py``. Those modules now
re-export ``Term``, ``NodeType``, ``var``, ``op``, and the parser from
here so that:

- Bug fixes only need to be applied once.
- There is a single authoritative definition of what a term *is*.
- The domain-specific ``Equation`` wrappers (a frozen identity in
  ``equation_analyzer``, a metadata-rich catalog entry in
  ``etp_equations``, and a property-labelled ``Equation`` in
  ``data_models``) stay where they belong — they compose over the
  canonical ``Term`` rather than duplicating it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from equation_parser_utils import tokenize_equation as _tokenize


class NodeType(Enum):
    VAR = auto()
    OP = auto()


@dataclass(frozen=True)
class Term:
    """A term in the free magma: either a variable or an application of ``*``.

    Uses ``NodeType`` rather than a boolean flag so that new node kinds
    (e.g. constants for Phase 6 rewrite analysis) can be added without
    a boolean explosion.

    Field invariants (validated in ``__post_init__`` per NEW-I4 / #58):

    - VAR nodes must have a non-empty ``name`` and no children. A
      ``Term(NodeType.VAR, name="", left=op(x,y))`` previously constructed
      successfully and only raised at access time inside ``_lr()``.
    - OP nodes must have both ``left`` and ``right`` children.

    Validating at construction surfaces the malformed-term bug at the
    construction site (where the caller can see the bug) instead of at
    a downstream traversal that pays the runtime check on every access.
    """

    node_type: NodeType
    name: str = ""
    left: Term | None = None
    right: Term | None = None

    def __post_init__(self) -> None:
        if self.node_type == NodeType.VAR:
            if not self.name:
                raise ValueError("VAR node must have a non-empty name")
            if self.left is not None or self.right is not None:
                raise ValueError("VAR node must not have children")
        else:  # OP
            if self.left is None or self.right is None:
                raise ValueError("OP node must have both left and right children")

    @property
    def is_var(self) -> bool:
        """True iff this term is a leaf variable."""
        return self.node_type == NodeType.VAR

    def _lr(self) -> tuple[Term, Term]:
        """Return (left, right) for OP nodes; raises on malformed nodes."""
        if self.left is None or self.right is None:
            raise ValueError("OP node must have left and right children")
        return self.left, self.right

    def variables(self) -> set[str]:
        if self.is_var:
            return {self.name}
        lt, rt = self._lr()
        return lt.variables() | rt.variables()

    def depth(self) -> int:
        if self.is_var:
            return 0
        lt, rt = self._lr()
        return 1 + max(lt.depth(), rt.depth())

    def size(self) -> int:
        """Count the number of ``*`` operations."""
        if self.is_var:
            return 0
        lt, rt = self._lr()
        return 1 + lt.size() + rt.size()

    def substitute(self, mapping: dict[str, Term]) -> Term:
        if self.is_var:
            return mapping.get(self.name, self)
        lt, rt = self._lr()
        return Term(NodeType.OP, left=lt.substitute(mapping), right=rt.substitute(mapping))

    def evaluate(self, table: list[list[int]], assignment: dict[str, int]) -> int:
        """Evaluate this term in a finite magma given variable assignments."""
        if self.is_var:
            return assignment[self.name]
        lt, rt = self._lr()
        return table[lt.evaluate(table, assignment)][rt.evaluate(table, assignment)]

    def __str__(self) -> str:
        if self.is_var:
            return self.name
        lt, rt = self._lr()
        return f"({lt} * {rt})"


def var(name: str) -> Term:
    """Construct a variable term. Preferred over ``Term(NodeType.VAR, name=...)``."""
    return Term(NodeType.VAR, name=name)


def op(left: Term, right: Term) -> Term:
    """Construct an application term. Preferred over ``Term(NodeType.OP, ...)``."""
    return Term(NodeType.OP, left=left, right=right)


# --- Parsing ---


def _parse_expr(tokens: list[str], pos: int) -> tuple[Term, int]:
    """Parse ``primary (* primary)*`` with left-to-right associativity."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")
    left, pos = _parse_primary(tokens, pos)
    while pos < len(tokens) and tokens[pos] == "*":
        right, pos = _parse_primary(tokens, pos + 1)
        left = op(left, right)
    return left, pos


def _parse_primary(tokens: list[str], pos: int) -> tuple[Term, int]:
    """Parse a variable or a parenthesised expression."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")
    if tokens[pos] == "(":
        expr, pos = _parse_expr(tokens, pos + 1)
        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError(f"Expected ')' at position {pos}")
        return expr, pos + 1
    if tokens[pos].isalpha() and tokens[pos] != "*":
        return var(tokens[pos]), pos + 1
    raise ValueError(f"Unexpected token '{tokens[pos]}' at position {pos}")


def parse_term(text: str) -> Term:
    """Parse a single term expression (no ``=``)."""
    tokens = _tokenize(text)
    result, pos = _parse_expr(tokens, 0)
    if pos != len(tokens):
        raise ValueError(f"Unexpected trailing tokens at position {pos}: {tokens[pos:]}")
    return result


def parse_equation_terms(text: str) -> tuple[Term, Term]:
    """Parse an equation string into ``(lhs_term, rhs_term)``.

    Accepts ``*`` or ``◇``/``⋄`` as the binary operator.
    Callers wrap the returned pair in whatever ``Equation`` class fits
    their domain (frozen identity, id/text/metadata, property catalog).
    """
    text = text.strip().replace("◇", "*").replace("⋄", "*")
    parts = text.split("=", 1)
    if len(parts) != 2:
        raise ValueError(f"No '=' found in equation: {text}")
    lhs_tokens = _tokenize(parts[0])
    rhs_tokens = _tokenize(parts[1])
    lhs, pos_l = _parse_expr(lhs_tokens, 0)
    if pos_l != len(lhs_tokens):
        raise ValueError(f"Unparsed trailing tokens on LHS: {lhs_tokens[pos_l:]}")
    rhs, pos_r = _parse_expr(rhs_tokens, 0)
    if pos_r != len(rhs_tokens):
        raise ValueError(f"Unparsed trailing tokens on RHS: {rhs_tokens[pos_r:]}")
    return lhs, rhs


__all__ = [
    "NodeType",
    "Term",
    "var",
    "op",
    "parse_term",
    "parse_equation_terms",
]
