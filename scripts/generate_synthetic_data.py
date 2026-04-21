#!/usr/bin/env python3
"""Generate synthetic competition data for equational theories.

Since real competition data is unavailable, this script generates
representative synthetic equations and implication problems based on
the SYNTHETIC_EQUATIONS catalog in data_models.py.

Output is written to research/data/original/ by default.

Usage:
    python scripts/generate_synthetic_data.py [--output-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_models import SYNTHETIC_EQUATIONS, Equation, Problem, Property

_DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "research" / "data" / "original"


def generate_extended_equations(count: int = 100) -> list[Equation]:
    """Generate a list of equations up to ``count``, starting from SYNTHETIC_EQUATIONS.

    Equations beyond the base set are generated with properties assigned by
    modular arithmetic rules (even→associative, divisible-by-3→commutative, etc.).
    """
    equations: list[Equation] = list(SYNTHETIC_EQUATIONS)

    for i in range(len(SYNTHETIC_EQUATIONS), count):
        props = []
        if i % 2 == 0:
            props.append(Property.ASSOCIATIVE)
        if i % 3 == 0:
            props.append(Property.COMMUTATIVE)
        if i % 5 == 0:
            props.append(Property.BIDENTITY)
        if i % 7 == 0 and Property.BIDENTITY in props:
            props.append(Property.INVERSE)
        if not props:
            props = [Property.IDEMPOTENT]

        equations.append(
            Equation(
                id=i + 1,
                latex=f"Equation_{i + 1}_latex",
                name=f"Synthetic Equation {i + 1}",
                properties=props,
                description=f"Generated equation with properties: {[p.value for p in props]}",
            )
        )

    return equations


def generate_implication_knowledge() -> list[tuple[int, int, bool]]:
    """Return known implication relationships as (eq1_id, eq2_id, implies) triples."""
    return [
        # True implications
        (13, 1, True),   # Group implies associativity
        (13, 5, True),   # Group implies two-sided identity
        (13, 8, True),   # Group implies two-sided inverse
        (16, 13, True),  # Abelian group implies group
        (15, 1, True),   # Monoid implies associativity
        (15, 5, True),   # Monoid implies identity
        # Non-implications
        (1, 2, False),   # Associativity does NOT imply commutativity
        (2, 1, False),   # Commutativity does NOT imply associativity
        (5, 8, False),   # Identity does NOT imply inverse
        (2, 5, False),   # Commutativity does NOT imply identity
    ]


def generate_synthetic_problems(
    num_problems: int = 1200, num_equations: int = 100
) -> list[Problem]:
    """Generate ``num_problems`` implication problems.

    The first len(known_implications) problems use the known implication data;
    the remainder use random equation pairs with a simple heuristic answer.
    Problems with id > 1000 are marked 'hard'.
    """
    known = generate_implication_knowledge()
    problems = []

    for i in range(num_problems):
        difficulty = "hard" if i >= 1000 else "regular"

        if i < len(known):
            eq1_id, eq2_id, answer = known[i]
        else:
            eq1_id = random.randint(1, num_equations)
            eq2_id = random.randint(1, num_equations)
            while eq2_id == eq1_id:
                eq2_id = random.randint(1, num_equations)
            answer = eq1_id < eq2_id

        problems.append(
            Problem(
                id=i + 1,
                equation_1_id=eq1_id,
                equation_2_id=eq2_id,
                answer=answer,
                difficulty=difficulty,
            )
        )

    return problems


def save_synthetic_data(
    output_dir: Path | None = None,
) -> tuple[list[Equation], list[Problem]]:
    """Generate and save synthetic data to ``output_dir``.

    Args:
        output_dir: Directory to write output files. Defaults to
                    ``research/data/original/`` relative to the project root.

    Returns:
        (equations, problems) tuple of the generated data.
    """
    out = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    equations = generate_extended_equations(count=100)
    print(f"Generated {len(equations)} synthetic equations")

    (out / "equations.json").write_text(
        json.dumps(
            {
                "count": len(equations),
                "source": "synthetic",
                "note": "Real competition data unavailable - using synthetic examples",
                "equations": [eq.to_dict() for eq in equations],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Synthetic Equations (100 total)",
        "# Format: ID | NAME | LATEX | PROPERTIES",
        "# NOTE: Real competition data unavailable",
        "",
    ]
    for eq in equations:
        props = ",".join(p.value for p in eq.properties)
        lines.append(f"{eq.id} | {eq.name} | {eq.latex} | [{props}]")
    (out / "equations.txt").write_text("\n".join(lines), encoding="utf-8")

    problems = generate_synthetic_problems(num_problems=1200, num_equations=100)
    print(f"Generated {len(problems)} synthetic problems")

    (out / "train_problems.json").write_text(
        json.dumps(
            {
                "count": len(problems),
                "source": "synthetic",
                "note": "Real competition data unavailable - using synthetic examples",
                "problems": [prob.to_dict() for prob in problems],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    implications = generate_implication_knowledge()
    (out / "implications.json").write_text(
        json.dumps(
            [{"eq1": e1, "eq2": e2, "implies": imp} for e1, e2, imp in implications],
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nSynthetic data saved to: {out}")
    return equations, problems


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic equations and implication problems",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {_DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()
    save_synthetic_data(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
