#!/usr/bin/env python3
"""
TLA+ Bridge for Automated Counterexample Generation

This module provides Python integration with TLA+ model checker
for automated counterexample finding in finite magmas.

When the compiled Rust extension `magma_core` is available, generation
and property checks run 20-60x faster. Falls back to pure Python otherwise.
"""

from __future__ import annotations

import functools
import logging
import os
import tempfile
from typing import Any

# Requires PYTHONPATH=src:tla/python (set by Makefile)
from data_models import Counterexample, Magma

_logger = logging.getLogger(__name__)

try:
    from magma_core import generate_all_magmas as _rust_generate  # type: ignore[import-not-found]
except ImportError:
    _rust_generate = None
    _logger.warning(
        "magma_core Rust extension not available; falling back to pure Python "
        "(20-60x slower). Build with: cd rust && maturin develop --release"
    )


@functools.lru_cache(maxsize=8)
def generate_all_magmas(size: int) -> tuple:
    """
    Generate all magmas of a given size.

    Warning: This grows as n^(n^2), so only use for small n.
    Returns a tuple (hashable for caching).

    When the Rust extension is available, returns ``magma_core.Magma``
    objects (~20x faster generation, ~20x faster property checks).
    Falls back to ``data_models.Magma`` otherwise.
    Both expose the same API: op(), is_associative(), is_commutative(),
    has_identity(), is_idempotent(), cayley_table_str(), to_tla().
    """
    if _rust_generate is not None:
        return tuple(_rust_generate(size))

    if size > 4:
        raise ValueError(f"Size {size} too large for exhaustive generation")

    magmas = []
    n = size
    total = n ** (n * n)

    for i in range(total):
        table = [[0] * n for _ in range(n)]
        temp = i
        for row in range(n):
            for col in range(n):
                table[row][col] = temp % n
                temp //= n

        magmas.append(Magma(size=size, elements=list(range(n)), operation=table))

    return tuple(magmas)


def to_python_magma(magma) -> Magma:
    """Convert a Rust Magma to a data_models.Magma (for serialization methods)."""
    if isinstance(magma, Magma):
        return magma
    return Magma(
        size=magma.size,
        elements=list(magma.elements),
        operation=[list(row) for row in magma.operation],
    )


def search_counterexample(
    equations_holding: list[int], equation_to_test: int, max_size: int = 4
) -> Counterexample | None:
    """
    Search for a magma where all `equations_holding` are true
    but `equation_to_test` is false.
    """
    raise NotImplementedError(
        "Counterexample search requires equation evaluation. "
        "Use explore_magmas.find_implication_counterexamples() for property-based search."
    )


def evaluate_equation(magma: Magma, equation: str, assignment: dict[str, int]) -> bool:
    """
    Evaluate an equation in a magma given variable assignment.
    """
    raise NotImplementedError(
        "Equation evaluation requires a term parser. "
        "See lean/EquationalTheories/Core.lean for term representation."
    )


class TLAModelChecker:
    """Interface to TLA+ model checker."""

    def __init__(self, tla_dir: str):
        self.tla_dir = tla_dir
        self.tla_modules = ["Magma", "EquationChecking", "MagmaModel"]

    def check_property(
        self, module: str, property_name: str, constants: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Run TLC model checker to verify a property.

        Returns (is_valid, counterexample_trace).
        """
        config = self._generate_config(constants)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config)
            config_path = f.name

        try:
            raise NotImplementedError(
                "TLC invocation requires tla2tools.jar. "
                "Install TLA+ Toolbox and set TLA_TOOLS_PATH."
            )
        finally:
            os.unlink(config_path)

    def _generate_config(self, constants: dict[str, Any]) -> str:
        lines = ["------- MODULE MagmaModelConf -------"]
        for name, value in constants.items():
            lines.append(f"{name} == {self._format_tla_value(value)}")
        lines.append("=================================")
        return "\n".join(lines)

    def _format_tla_value(self, value: Any) -> str:
        if isinstance(value, set):
            return "{" + ", ".join(self._format_tla_value(v) for v in value) + "}"
        elif isinstance(value, list):
            return "<<" + ", ".join(self._format_tla_value(v) for v in value) + ">>"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, str):
            return f'"{value}"'
        else:
            return str(value)


# Predefined counterexamples for common non-implications
COUNTEREXAMPLES: dict[tuple[int, int], Magma] = {}


def get_counterexample(premise_id: int, conclusion_id: int) -> Magma | None:
    """Get known counterexample for implication premise_id => conclusion_id."""
    return COUNTEREXAMPLES.get((premise_id, conclusion_id))


if __name__ == "__main__":
    print("Generating magmas of size 2...")
    magmas = generate_all_magmas(2)
    print(f"Found {len(magmas)} magmas")

    associative_count = sum(1 for m in magmas if m.is_associative())
    commutative_count = sum(1 for m in magmas if m.is_commutative())

    print(f"Associative: {associative_count}/{len(magmas)}")
    print(f"Commutative: {commutative_count}/{len(magmas)}")

    m = magmas[0]
    print("\nExample magma:")
    print(m.cayley_table_str())
