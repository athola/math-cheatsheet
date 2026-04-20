"""Automated counterexample generation pipeline for FALSE equational implications.

Generates magma tables exhaustively and searches for counterexamples:
a magma where the hypothesis equation holds but the target does not.

Classes:
- MagmaGenerator: enumerate all magma tables of a given size
- CounterexampleFinder: find a single counterexample for H !=> T
- BatchCounterexampleSearch: search counterexamples for many pairs with caching
- OptimalMagmaDiscovery: find magmas that witness the most FALSE pairs

Usage:
    python src/counterexample_generator.py [--size N] [--top-magmas N]
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
                        table=table,
                    )
        return None


class BatchCounterexampleSearch:
    """Search counterexamples for multiple equation pairs with caching.

    Caches which magmas satisfy each equation to avoid redundant evaluation.
    """

    def search_batch(
        self,
        pairs: list[tuple[Equation, Equation]],
        max_size: int = 2,
    ) -> dict[int, CounterexampleMagma]:
        """Search counterexamples for a list of (hypothesis, target) pairs.

        Args:
            pairs: List of (hypothesis, target) equation pairs.
            max_size: Maximum carrier size to search.

        Returns:
            Dict mapping pair index to the found CounterexampleMagma.
            Only includes entries where a counterexample was found.
        """
        results: dict[int, CounterexampleMagma] = {}

        for size in range(2, max_size + 1):
            tables = MagmaGenerator.generate_all(size)

            # Cache: equation id -> set of table indices where it holds
            sat_cache: dict[int, set[int]] = {}

            # Collect unique equations from remaining unsolved pairs
            unsolved = [i for i in range(len(pairs)) if i not in results]
            if not unsolved:
                break

            unique_eqs: dict[int, Equation] = {}
            for idx in unsolved:
                h, t = pairs[idx]
                unique_eqs[id(h)] = h
                unique_eqs[id(t)] = t

            # Populate cache for all unique equations at this size
            for eq_id, eq in unique_eqs.items():
                if eq_id not in sat_cache:
                    sat_set = set()
                    for ti, table in enumerate(tables):
                        if eq.holds_in(table, size):
                            sat_set.add(ti)
                    sat_cache[eq_id] = sat_set

            # Find counterexamples using the cache
            for idx in unsolved:
                h, t = pairs[idx]
                h_sat = sat_cache[id(h)]
                t_sat = sat_cache[id(t)]
                # Magmas where h holds but t does not
                witnesses = h_sat - t_sat
                if witnesses:
                    ti = min(witnesses)  # deterministic: pick smallest index
                    results[idx] = CounterexampleMagma(
                        name=f"size-{size} magma #{ti}",
                        size=size,
                        table=tables[ti],
                    )

        return results


class OptimalMagmaDiscovery:
    """Find magmas that witness the most FALSE implication pairs."""

    def find_optimal_magmas(
        self,
        equations: list[Equation],
        false_pairs: list[tuple[int, int]],
        n_magmas: int = 10,
        size: int = 2,
    ) -> list[tuple[list[list[int]], int]]:
        """Find the N magmas that witness the most FALSE pairs.

        For each magma of the given size, count how many of the provided
        FALSE pairs (h_idx, t_idx) it can witness (h holds, t fails).

        Args:
            equations: List of equations, indexed by position.
            false_pairs: List of (hypothesis_index, target_index) pairs known to be FALSE.
            n_magmas: Maximum number of magmas to return.
            size: Carrier size for magma generation.

        Returns:
            List of (table, witness_count) sorted by witness_count descending.
            Only includes magmas with witness_count > 0.
        """
        tables = MagmaGenerator.generate_all(size)

        # Cache: equation index -> set of table indices where it holds
        eq_sat: dict[int, set[int]] = {}
        needed_indices = set()
        for h_idx, t_idx in false_pairs:
            needed_indices.add(h_idx)
            needed_indices.add(t_idx)

        for eq_idx in needed_indices:
            sat_set = set()
            for ti, table in enumerate(tables):
                if equations[eq_idx].holds_in(table, size):
                    sat_set.add(ti)
            eq_sat[eq_idx] = sat_set

        # Score each magma
        scored: list[tuple[list[list[int]], int]] = []
        for ti, table in enumerate(tables):
            count = 0
            for h_idx, t_idx in false_pairs:
                if ti in eq_sat.get(h_idx, set()) and ti not in eq_sat.get(t_idx, set()):
                    count += 1
            if count > 0:
                scored.append((table, count))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n_magmas]


def main():
    """CLI entry point for counterexample generation."""
    parser = argparse.ArgumentParser(
        description="Automated counterexample generation for equational implications"
    )
    parser.add_argument(
        "--size", type=int, default=2, help="Maximum magma size to search (default: 2)"
    )
    parser.add_argument(
        "--top-magmas", type=int, default=10, help="Number of top magmas to report (default: 10)"
    )
    args = parser.parse_args()

    print(f"=== Counterexample Generation Pipeline (size <= {args.size}) ===\n")

    # Demo: classic FALSE implications
    classic_pairs = [
        ("x * (y * z) = (x * y) * z", "x * y = y * x", "assoc !=> comm"),
        ("x * y = y * x", "x * (y * z) = (x * y) * z", "comm !=> assoc"),
        ("x * (y * z) = (x * y) * z", "x * x = x", "assoc !=> idem"),
        ("x * x = x", "x * y = y * x", "idem !=> comm"),
    ]

    print("--- Counterexample Search ---")
    finder = CounterexampleFinder()
    equations_for_optimal: list[Equation] = []
    eq_strings: list[str] = []

    for h_str, t_str, label in classic_pairs:
        h = parse_equation(h_str)
        t = parse_equation(t_str)
        result = finder.find_counterexample(h, t, max_size=args.size)
        if result is not None:
            print(f"  {label}: FOUND {result.name}, table={result.table}")
        else:
            print(f"  {label}: no counterexample found (up to size {args.size})")

        # Collect unique equations for optimal magma search
        if h_str not in eq_strings:
            eq_strings.append(h_str)
            equations_for_optimal.append(h)
        if t_str not in eq_strings:
            eq_strings.append(t_str)
            equations_for_optimal.append(t)

    # Build false_pairs indices
    false_pairs_idx: list[tuple[int, int]] = []
    for h_str, t_str, _ in classic_pairs:
        h_idx = eq_strings.index(h_str)
        t_idx = eq_strings.index(t_str)
        false_pairs_idx.append((h_idx, t_idx))

    print(f"\n--- Optimal Magma Discovery (top {args.top_magmas}, size {args.size}) ---")
    discovery = OptimalMagmaDiscovery()
    optimal = discovery.find_optimal_magmas(
        equations=equations_for_optimal,
        false_pairs=false_pairs_idx,
        n_magmas=args.top_magmas,
        size=args.size,
    )
    for rank, (table, count) in enumerate(optimal, 1):
        print(f"  #{rank}: table={table} witnesses {count} FALSE pair(s)")

    print(f"\nTotal size-{args.size} magmas: {args.size ** (args.size**2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
