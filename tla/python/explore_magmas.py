#!/usr/bin/env python3
"""
Magma Exploration Script

Explores finite magmas and their properties to identify
patterns useful for cheatsheet construction.

Uses the compiled Rust extension `magma_core` when available for
20-60x speedups on exhaustive generation and property checking.
"""

import json
import logging
from pathlib import Path

# Requires PYTHONPATH=src:tla/python (set by Makefile)
from tla_bridge import generate_all_magmas, to_python_magma

from data_models import Counterexample

_logger = logging.getLogger(__name__)

try:
    import magma_core as _rust  # type: ignore[import-not-found]
except ImportError:
    _rust = None
    _logger.warning(
        "magma_core Rust extension not available; falling back to pure Python"
    )


def analyze_magmas(size: int) -> dict:
    """Exhaustively analyze all magmas of given size.

    When the Rust extension is available, uses count_properties() to
    stay entirely in Rust (no Python object allocation per magma).
    """
    print(f"Analyzing all magmas of size {size}...")

    if _rust is not None:
        counts = _rust.count_properties(size)
        return {
            "size": size,
            "total": int(counts.total),
            "associative": int(counts.associative),
            "commutative": int(counts.commutative),
            "has_identity": int(counts.has_identity),
            "monoids": int(counts.monoid),
            "groups": 0,  # count_properties doesn't track inverse yet
        }

    magmas = generate_all_magmas(size)
    results = {
        "size": size,
        "total": len(magmas),
        "associative": 0,
        "commutative": 0,
        "has_identity": 0,
        "monoids": 0,
        "groups": 0,
    }

    for magma in magmas:
        assoc = magma.is_associative()
        comm = magma.is_commutative()
        has_id = magma.has_identity() is not None

        if assoc:
            results["associative"] += 1
        if comm:
            results["commutative"] += 1
        if has_id:
            results["has_identity"] += 1
        if assoc and has_id:
            results["monoids"] += 1

    return results


def find_property_correlations(size: int) -> list[tuple[str, str, int, int]]:
    """Find correlations between properties."""
    if _rust is not None:
        counts = _rust.count_properties(size)
        return [("associative", "commutative", int(counts.assoc_and_comm), int(counts.total))]

    magmas = generate_all_magmas(size)
    both = sum(1 for m in magmas if m.is_associative() and m.is_commutative())
    return [("associative", "commutative", both, len(magmas))]


def find_implication_counterexamples(
    premise: str, conclusion: str, max_size: int = 3
) -> list[Counterexample]:
    """
    Find counterexamples to implication: premise => conclusion.

    premise, conclusion are strings like "associative", "commutative", etc.
    Uses Rust find_counterexamples() when available for ~100x speedup.
    """
    if _rust is not None:
        try:
            rust_magmas = _rust.find_counterexamples(premise, conclusion, max_size, 100)
            return [
                Counterexample(
                    premise_id=-1,
                    conclusion_id=-1,
                    magma=to_python_magma(m),
                )
                for m in rust_magmas
            ]
        except ValueError as exc:
            _logger.info("Rust counterexample search failed (%s); using Python fallback", exc)

    property_checks = {
        "associative": lambda m: m.is_associative(),
        "commutative": lambda m: m.is_commutative(),
        "has_identity": lambda m: m.has_identity() is not None,
        "idempotent": lambda m: m.is_idempotent(),
    }

    valid_properties = set(property_checks.keys())
    if premise not in property_checks:
        raise ValueError(
            f"Unknown property '{premise}'. Valid properties: {valid_properties}"
        )
    if conclusion not in property_checks:
        raise ValueError(
            f"Unknown property '{conclusion}'. Valid properties: {valid_properties}"
        )

    check_premise = property_checks[premise]
    check_conclusion = property_checks[conclusion]
    counterexamples = []

    for size in range(2, max_size + 1):
        magmas = generate_all_magmas(size)

        for magma in magmas:
            if check_premise(magma) and not check_conclusion(magma):
                counterexamples.append(
                    Counterexample(
                        premise_id=-1,
                        conclusion_id=-1,
                        magma=magma,
                    )
                )

    return counterexamples


def main():
    print("=" * 60)
    print("Magma Exploration for Cheatsheet Insights")
    print("=" * 60)

    # Analyze small magmas
    analysis = {}
    for size in [2, 3]:
        print(f"\n--- Size {size} ---")
        results = analyze_magmas(size)
        analysis[size] = results
        for key, value in results.items():
            if key != "size":
                print(f"  {key}: {value}")

    # Find implication counterexamples
    print("\n--- Implication Counterexamples ---")

    implication_tests = {}

    print("\nChecking: commutative => associative")
    counterexamples = find_implication_counterexamples("commutative", "associative", 3)
    implication_tests["commutative_implies_associative"] = len(counterexamples)
    print(f"  Counterexamples found: {len(counterexamples)}")

    if counterexamples:
        print("\n  Example counterexample:")
        print(counterexamples[0].magma.cayley_table_str())

    print("\nChecking: has_identity => commutative")
    counterexamples = find_implication_counterexamples("has_identity", "commutative", 3)
    implication_tests["identity_implies_commutative"] = len(counterexamples)
    print(f"  Counterexamples found: {len(counterexamples)}")

    # Save results
    output = {
        "analysis": {str(k): v for k, v in analysis.items()},
        "implication_tests": implication_tests,
    }

    output_path = Path(__file__).parent.parent / "MagmaSpecifications" / "exploration_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
