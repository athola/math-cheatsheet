"""
Generate synthetic competition data for equational theories.

Since real competition data is unavailable, this script generates
representative synthetic equations and implication problems.
"""

import json
import random

from data_models import SYNTHETIC_EQUATIONS, Difficulty, EquationEntry, Problem, Property


def generate_extended_equations(count: int = 100) -> list[EquationEntry]:
    """Generate a larger set of synthetic equations.

    In production, this would be replaced with the actual 4694 equations.
    For now, we generate representative examples.
    """
    equations: list[EquationEntry] = list(SYNTHETIC_EQUATIONS)

    # Generate variations and combinations
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

        eq = EquationEntry(
            id=i + 1,
            latex=f"Equation_{i + 1}_latex",
            name=f"Synthetic Equation {i + 1}",
            properties=props,
            description=f"Generated equation with properties: {[p.value for p in props]}",
        )
        equations.append(eq)

    return equations


def generate_implication_knowledge() -> list[tuple[int, int, bool]]:
    """Generate known implication relationships.

    Returns list of (eq1_id, eq2_id, implies) tuples.
    """
    implications = []

    # Define known mathematical implications
    # Format: (stronger_id, weaker_id, True)

    # Group axioms imply components
    implications.append((13, 1, True))  # Group implies associativity
    implications.append((13, 5, True))  # Group implies two-sided identity
    implications.append((13, 8, True))  # Group implies two-sided inverse
    implications.append((16, 13, True))  # Abelian group implies group
    implications.append((15, 1, True))  # Monoid implies associativity
    implications.append((15, 5, True))  # Monoid implies identity

    # Known non-implications
    implications.append((1, 2, False))  # Associativity does NOT imply commutativity
    implications.append((2, 1, False))  # Commutativity does NOT imply associativity
    implications.append((5, 8, False))  # Identity does NOT imply inverse
    implications.append((2, 5, False))  # Commutativity does NOT imply identity

    return implications


def generate_synthetic_problems(
    num_problems: int = 1200, num_equations: int = 100
) -> list[Problem]:
    """Generate synthetic implication problems.

    Args:
        num_problems: Total problems to generate
        num_equations: Number of equations to draw from

    Returns:
        List of synthetic problems
    """
    problems = []
    implications = generate_implication_knowledge()

    for i in range(num_problems):
        # Determine difficulty
        difficulty = Difficulty.HARD if i >= 1000 else Difficulty.REGULAR

        # Select equation pair
        if i < len(implications):
            # Use known implications for early problems
            eq1_id, eq2_id, answer = implications[i]
        else:
            # Generate random pairs
            eq1_id = random.randint(1, num_equations)
            eq2_id = random.randint(1, num_equations)

            # Ensure different equations
            while eq2_id == eq1_id:
                eq2_id = random.randint(1, num_equations)

            # For synthetic data, assign answers based on some heuristics
            # In production, this would come from actual data
            answer = eq1_id < eq2_id  # Simple heuristic for synthetic data

        problem = Problem(
            id=i + 1,
            equation_1_id=eq1_id,
            equation_2_id=eq2_id,
            answer=answer,
            difficulty=difficulty,
        )
        problems.append(problem)

    return problems


def save_synthetic_data(project_root=None):
    """Save synthetic data to files.

    Args:
        project_root: Project root directory. Defaults to this file's parent.parent.
    """
    from pathlib import Path

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    project_root = Path(project_root)
    original_dir = project_root / "research" / "data" / "original"
    processed_dir = project_root / "research" / "data" / "processed"

    # Create directories
    original_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Generate equations
    equations = generate_extended_equations(count=100)
    print(f"Generated {len(equations)} synthetic equations")

    # Save equations as JSON
    equations_data = {
        "count": len(equations),
        "source": "synthetic",
        "note": "Real competition data unavailable - using synthetic examples",
        "equations": [eq.to_dict() for eq in equations],
    }

    with open(original_dir / "equations.json", "w") as f:
        json.dump(equations_data, f, indent=2)

    # Create simplified equations.txt format
    with open(original_dir / "equations.txt", "w") as f:
        f.write("# Synthetic Equations (100 total)\n")
        f.write("# Format: ID | NAME | LATEX | PROPERTIES\n")
        f.write("# NOTE: Real competition data unavailable\n\n")
        for eq in equations:
            props = ",".join([p.value for p in eq.properties])
            f.write(f"{eq.id} | {eq.name} | {eq.latex} | [{props}]\n")

    # Generate problems
    problems = generate_synthetic_problems(num_problems=1200, num_equations=100)
    print(f"Generated {len(problems)} synthetic problems")

    # Save problems
    problems_data = {
        "count": len(problems),
        "source": "synthetic",
        "note": "Real competition data unavailable - using synthetic examples",
        "problems": [prob.to_dict() for prob in problems],
    }

    with open(original_dir / "train_problems.json", "w") as f:
        json.dump(problems_data, f, indent=2)

    # Save implication knowledge
    implications = generate_implication_knowledge()
    with open(original_dir / "implications.json", "w") as f:
        json.dump(
            [{"eq1": e1, "eq2": e2, "implies": imp} for e1, e2, imp in implications], f, indent=2
        )

    print("\nSynthetic data saved to:")
    print(f"  - {original_dir / 'equations.txt'}")
    print(f"  - {original_dir / 'equations.json'}")
    print(f"  - {original_dir / 'train_problems.json'}")
    print(f"  - {original_dir / 'implications.json'}")

    return equations, problems


if __name__ == "__main__":
    save_synthetic_data()
