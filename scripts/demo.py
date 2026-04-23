#!/usr/bin/env python3
"""Unified magma demo: explore algebraic properties and counterexamples.

Consolidates demo_properties.py and demo_counterexamples.py.

Usage:
    python scripts/demo.py --mode properties
    python scripts/demo.py --mode counterexamples
    python scripts/demo.py --mode all
    python scripts/demo.py --mode properties --sizes 2 3 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tla" / "python"))

from tla_bridge import generate_all_magmas


def count_properties(size: int) -> dict[str, int]:
    """Count algebraic properties across all magmas of a given carrier size.

    Returns a dict with keys: size, total, associative, commutative, identity, idempotent.
    """
    magmas = generate_all_magmas(size)
    return {
        "size": size,
        "total": len(magmas),
        "associative": sum(1 for m in magmas if m.is_associative()),
        "commutative": sum(1 for m in magmas if m.is_commutative()),
        "identity": sum(1 for m in magmas if m.has_identity() is not None),
        "idempotent": sum(1 for m in magmas if m.is_idempotent()),
    }


def find_counterexamples(size: int = 3) -> dict[str, list]:
    """Find magmas that witness classic non-implications.

    Returns a dict with keys:
      comm_not_assoc  — commutative but not associative
      assoc_not_comm  — associative but not commutative
      idemp_not_comm  — idempotent but not commutative
    """
    magmas = generate_all_magmas(size)
    return {
        "comm_not_assoc": [m for m in magmas if m.is_commutative() and not m.is_associative()],
        "assoc_not_comm": [m for m in magmas if m.is_associative() and not m.is_commutative()],
        "idemp_not_comm": [m for m in magmas if m.is_idempotent() and not m.is_commutative()],
    }


def _print_properties(sizes: list[int]) -> None:
    for size in sizes:
        r = count_properties(size)
        print(
            f"Size {r['size']}: {r['total']} magmas | "
            f"assoc={r['associative']} comm={r['commutative']} "
            f"identity={r['identity']} idemp={r['idempotent']}"
        )


def _print_counterexamples(size: int = 3) -> None:
    result = find_counterexamples(size)
    for label, key in [
        ("Comm but not Assoc", "comm_not_assoc"),
        ("Assoc but not Comm", "assoc_not_comm"),
        ("Idemp but not Comm", "idemp_not_comm"),
    ]:
        witnesses = result[key]
        print(f"{label}: {len(witnesses)} counterexamples")
        if witnesses:
            print("First counterexample Cayley table:")
            print(witnesses[0].cayley_table_str())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Magma property and counterexample demos",
    )
    parser.add_argument(
        "--mode",
        choices=["properties", "counterexamples", "all"],
        default="all",
        help="Which demo to run (default: all)",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[2, 3],
        metavar="N",
        help="Carrier sizes for properties mode (default: 2 3)",
    )
    args = parser.parse_args()

    if args.mode in ("properties", "all"):
        print("=== Magma Property Counts ===")
        _print_properties(args.sizes)

    if args.mode in ("counterexamples", "all"):
        print("\n=== Classic Non-Implication Witnesses (size 3) ===")
        _print_counterexamples(size=3)


if __name__ == "__main__":
    main()
