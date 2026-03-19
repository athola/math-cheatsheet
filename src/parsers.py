"""
Data parsers for equational theories competition.

Parses equations.txt and train_problems.json into structured data.
"""

import json
from pathlib import Path
from typing import Any

from data_models import Equation, Problem, Property


class ParseError(Exception):
    """Raised when parsing fails."""

    pass


def parse_equations(filepath: str) -> list[Equation]:
    """Parse equations from file.

    Args:
        filepath: Path to equations file (txt or json)

    Returns:
        List of Equation objects

    Raises:
        ParseError: If file format is invalid
    """
    path = Path(filepath)

    if not path.exists():
        raise ParseError(f"File not found: {filepath}")

    # Determine format by extension
    if path.suffix == ".json":
        return _parse_equations_json(path)
    elif path.suffix == ".txt":
        return _parse_equations_txt(path)
    else:
        raise ParseError(f"Unsupported file format: {path.suffix}")


def _parse_equations_json(path: Path) -> list[Equation]:
    """Parse equations from JSON format."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    equations = []
    for eq_data in data.get("equations", []):
        # Convert property strings back to Property enum
        properties = []
        for prop_str in eq_data.get("properties", []):
            try:
                properties.append(Property(prop_str))
            except ValueError:
                import logging
                logging.getLogger(__name__).debug("Unknown property value: %s", prop_str)

        equation = Equation(
            id=eq_data["id"],
            latex=eq_data["latex"],
            name=eq_data["name"],
            properties=properties,
            description=eq_data.get("description", ""),
        )
        equations.append(equation)

    return equations


def _parse_equations_txt(path: Path) -> list[Equation]:
    """Parse equations from text format.

    Expected format:
    ID | NAME | LATEX | [PROPERTIES]
    """
    equations = []

    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse line
            parts = line.split("|")
            if len(parts) < 4:
                continue

            try:
                eq_id = int(parts[0].strip())
                name = parts[1].strip()
                latex = parts[2].strip()
                props_str = parts[3].strip()

                # Parse properties
                properties = []
                if props_str.startswith("[") and props_str.endswith("]"):
                    props_str = props_str[1:-1]
                    for prop_str in props_str.split(","):
                        prop_str = prop_str.strip()
                        if prop_str:
                            try:
                                properties.append(Property(prop_str))
                            except ValueError:
                                import logging
                                logging.getLogger(__name__).debug(
                                    "Unknown property value: %s", prop_str
                                )

                equation = Equation(
                    id=eq_id, latex=latex, name=name, properties=properties, description=""
                )
                equations.append(equation)

            except (ValueError, IndexError) as exc:
                import logging
                logging.getLogger(__name__).debug("Skipping malformed line %d: %s", line_num, exc)
                continue

    return equations


def parse_problems(filepath: str) -> list[Problem]:
    """Parse problems from JSON file.

    Args:
        filepath: Path to problems JSON file

    Returns:
        List of Problem objects

    Raises:
        ParseError: If file format is invalid
    """
    path = Path(filepath)

    if not path.exists():
        raise ParseError(f"File not found: {filepath}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    problems = []
    for prob_data in data.get("problems", []):
        problem = Problem(
            id=prob_data["id"],
            equation_1_id=prob_data["equation_1"],
            equation_2_id=prob_data["equation_2"],
            answer=prob_data.get("answer"),
            difficulty=prob_data.get("difficulty", "regular"),
        )
        problems.append(problem)

    return problems


def validate_equations(equations: list[Equation]) -> dict[str, Any]:
    """Validate equation data.

    Returns:
        Dictionary with validation results
    """
    errors: list[str] = []
    warnings: list[str] = []
    by_property: dict[str, int] = {}

    ids = set()
    for eq in equations:
        if eq.id in ids:
            errors.append(f"Duplicate equation ID: {eq.id}")
        ids.add(eq.id)

        if not eq.properties:
            warnings.append(f"Equation {eq.id} has no properties")

        for prop in eq.properties:
            by_property[prop.value] = by_property.get(prop.value, 0) + 1

    return {
        "errors": errors,
        "warnings": warnings,
        "stats": {"total": len(equations), "by_property": by_property},
    }


def validate_problems(problems: list[Problem], max_equation_id: int) -> dict[str, Any]:
    """Validate problem data.

    Args:
        problems: List of problems to validate
        max_equation_id: Maximum valid equation ID

    Returns:
        Dictionary with validation results
    """
    errors: list[str] = []
    warnings: list[str] = []
    by_difficulty: dict[str, int] = {"regular": 0, "hard": 0}
    with_answer = 0

    ids = set()
    for prob in problems:
        if prob.id in ids:
            errors.append(f"Duplicate problem ID: {prob.id}")
        ids.add(prob.id)

        if prob.equation_1_id < 1 or prob.equation_1_id > max_equation_id:
            errors.append(f"Problem {prob.id}: equation_1_id {prob.equation_1_id} out of range")

        if prob.equation_2_id < 1 or prob.equation_2_id > max_equation_id:
            errors.append(f"Problem {prob.id}: equation_2_id {prob.equation_2_id} out of range")

        if prob.difficulty in by_difficulty:
            by_difficulty[prob.difficulty] += 1

        if prob.answer is not None:
            with_answer += 1

    return {
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "total": len(problems),
            "by_difficulty": by_difficulty,
            "with_answer": with_answer,
        },
    }


if __name__ == "__main__":
    # Test parsers
    print("Testing equation parser...")
    equations = parse_equations("research/data/original/equations.json")
    print(f"Parsed {len(equations)} equations")

    validation = validate_equations(equations)
    print(f"Validation: {len(validation['errors'])} errors, {len(validation['warnings'])} warnings")
    print(f"Stats: {validation['stats']}")

    print("\nTesting problem parser...")
    problems = parse_problems("research/data/original/train_problems.json")
    print(f"Parsed {len(problems)} problems")

    prob_validation = validate_problems(problems, max_equation_id=len(equations))
    n_err = len(prob_validation["errors"])
    n_warn = len(prob_validation["warnings"])
    print(f"Validation: {n_err} errors, {n_warn} warnings")
    print(f"Stats: {prob_validation['stats']}")
