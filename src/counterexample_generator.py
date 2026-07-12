"""Automated counterexample generation pipeline for FALSE equational implications.

Generates magma tables exhaustively and searches for counterexamples:
a magma where the hypothesis equation holds but the target does not.

Classes:
- MagmaGenerator: enumerate all magma tables of a given size
- CounterexampleFinder: find a single counterexample for H !=> T

Usage:
    python src/counterexample_generator.py [--size N]
"""

from __future__ import annotations

import argparse
import itertools
import sys
import time
from collections.abc import Callable

from equation_analyzer import (
    CounterexampleMagma,
    Equation,
    parse_equation,
)


class MagmaGenerator:
    """Generate all magma operation tables of a given carrier size."""

    @staticmethod
    def generate_all(size: int) -> list[list[list[int]]]:
        """Generate all magma tables for a carrier set {0, ..., size-1}.

        A magma table is a size x size matrix where entry [i][j] is in {0, ..., size-1}.
        Total count: size^(size^2).

        Args:
            size: Number of elements in the carrier set. Must be >= 1.

        Returns:
            List of all possible operation tables.
        """
        if size < 1:
            raise ValueError(f"Size must be at least 1, got {size}")
        if size > 3:
            raise ValueError(
                f"Size {size} would generate {size ** (size**2):,} tables. Max safe size is 3."
            )

        n_entries = size * size
        tables = []
        for flat in itertools.product(range(size), repeat=n_entries):
            table = [list(flat[i * size : (i + 1) * size]) for i in range(size)]
            tables.append(table)
        return tables


class CounterexampleFinder:
    """Find a counterexample magma for a FALSE implication H !=> T."""

    def find_counterexample(
        self,
        hypothesis: Equation,
        target: Equation,
        max_size: int = 3,
        timeout_seconds: float | None = None,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> CounterexampleMagma | None:
        """Search for a magma where hypothesis holds but target does not.

        Iterates sizes from 2 up to max_size, testing all magmas at each size.
        Size 1 is skipped because any equation with matching variable structure
        trivially holds in a 1-element magma.

        Args:
            hypothesis: The equation that must hold.
            target: The equation that must fail.
            max_size: Maximum carrier size to search. Size 3 iterates
                ``3**9 = 19683`` magmas; size 4 would blow up to ~4 billion.
            timeout_seconds: Optional wall-clock limit. When exceeded the
                search returns ``None`` early (regression #43/S5). A ``None``
                value disables the limit.
            progress_callback: Optional ``callback(size, index, total)`` invoked
                every 256 tables so long-running calls can surface progress
                instead of hanging silently at size 3.

        Returns:
            A CounterexampleMagma if found, otherwise None.
        """
        deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
        for size in range(2, max_size + 1):
            tables = MagmaGenerator.generate_all(size)
            total = len(tables)
            for i, table in enumerate(tables):
                if deadline is not None and time.monotonic() > deadline:
                    return None
                if progress_callback is not None and i and i % 256 == 0:
                    progress_callback(size, i, total)
                if hypothesis.holds_in(table, size) and not target.holds_in(table, size):
                    return CounterexampleMagma(
                        name=f"size-{size} magma #{i}",
                        size=size,
                        # CounterexampleMagma is frozen with tuple-of-tuples
                        # storage (#58); MagmaGenerator yields list-of-list, so
                        # convert at the call site rather than weakening the
                        # type contract.
                        table=tuple(tuple(row) for row in table),
                    )
        return None


def main():
    """CLI entry point for counterexample generation."""
    parser = argparse.ArgumentParser(
        description="Automated counterexample generation for equational implications"
    )
    parser.add_argument(
        "--size", type=int, default=2, help="Maximum magma size to search (default: 2)"
    )
    args = parser.parse_args()

    print(f"=== Counterexample Generation Pipeline (size <= {args.size}) ===\n")

    classic_pairs = [
        ("x * (y * z) = (x * y) * z", "x * y = y * x", "assoc !=> comm"),
        ("x * y = y * x", "x * (y * z) = (x * y) * z", "comm !=> assoc"),
        ("x * (y * z) = (x * y) * z", "x * x = x", "assoc !=> idem"),
        ("x * x = x", "x * y = y * x", "idem !=> comm"),
    ]

    finder = CounterexampleFinder()
    for h_str, t_str, label in classic_pairs:
        h = parse_equation(h_str)
        t = parse_equation(t_str)
        result = finder.find_counterexample(h, t, max_size=args.size)
        if result is not None:
            print(f"  {label}: FOUND {result.name}, table={result.table}")
        else:
            print(f"  {label}: no counterexample found (up to size {args.size})")

    print(f"\nTotal size-{args.size} magmas: {args.size ** (args.size**2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
