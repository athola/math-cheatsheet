#!/usr/bin/env python3
"""Evaluate the v3 cheatsheet decision procedure on test problems.

Tests the programmatic implementation of the v3 cheatsheet heuristics
against known-answer equational implication problems.
"""

from pathlib import Path

from src.equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)

# Known implication problems with verified answers.
# Format: (hypothesis, target, expected_answer, source)
KNOWN_PROBLEMS = [
    # === PHASE 1: Instant decisions ===
    # Reflexive (identical equations)
    ("x * y = y * x", "x * y = y * x", True, "reflexive"),
    ("x * (y * z) = (x * y) * z", "x * (y * z) = (x * y) * z", True, "reflexive"),
    # Tautology target
    ("x * y = y * x", "x = x", True, "tautology target"),
    # Collapse hypothesis
    ("x = y", "x * y = y * x", True, "collapse H"),
    ("x = y", "x * (y * z) = (x * y) * z", True, "collapse H"),
    # Collapse target with non-collapse H
    ("x * x = x", "x = y", False, "collapse T, non-collapse H"),
    # Tautology H with non-tautology T
    ("x = x", "x * y = y * x", False, "tautology H"),

    # === PHASE 2: Variable analysis ===
    # New variable in target
    ("x * (x * x) = x", "x * y = y * x", False, "new var y"),
    ("x * x = x", "x * y = y * x", False, "new var y"),

    # === PHASE 3: Substitution ===
    # Associativity specializations
    ("x * (y * z) = (x * y) * z", "x * (x * z) = (x * x) * z", True, "y:=x"),
    ("x * (y * z) = (x * y) * z", "x * (y * y) = (x * y) * y", True, "z:=y"),

    # === PHASE 4: Counterexample testing ===
    # Independence of standard properties
    ("x * (y * z) = (x * y) * z", "x * y = y * x", False, "assoc !=> comm"),
    ("x * y = y * x", "x * (y * z) = (x * y) * z", False, "comm !=> assoc"),
    ("x * x = x", "x * y = y * x", False, "idem !=> comm"),
    ("x * (y * z) = (x * y) * z", "x * x = x", False, "assoc !=> idem"),

    # === PHASE 5: Absorption laws ===
    # Left absorption determines LP
    ("x = x * y", "x * x = x", True, "left abs => idem"),
    ("x = x * y", "x * (y * z) = (x * y) * z", True, "left abs => assoc"),
    ("x = x * y", "x * y = y * x", False, "left abs !=> comm"),

    # Constant law
    ("x * y = z * w", "x * y = y * x", True, "constant => comm"),

    # === ETP-inspired problems ===
    # Commutativity does not imply idempotency
    ("x * y = y * x", "x * x = x", False, "comm !=> idem"),
]


def main():
    correct = 0
    incorrect = 0
    unknown = 0
    errors = []

    print("=" * 70)
    print("CHEATSHEET v3 DECISION PROCEDURE EVALUATION")
    print("=" * 70)
    print()

    for h_str, t_str, expected, source in KNOWN_PROBLEMS:
        try:
            h = parse_equation(h_str)
            t = parse_equation(t_str)
            result = analyze_implication(h, t)

            predicted = result.verdict == ImplicationVerdict.TRUE
            if result.verdict == ImplicationVerdict.UNKNOWN:
                # Default FALSE per cheatsheet
                predicted = False

            is_correct = predicted == expected
            status = "OK" if is_correct else "WRONG"

            if is_correct:
                correct += 1
            else:
                incorrect += 1
                errors.append((h_str, t_str, expected, result))

            if not is_correct:
                print(f"  [{status}] H: {h_str}")
                print(f"         T: {t_str}")
                print(f"         Expected: {expected}, Got: {result.verdict.value}")
                print(f"         Phase: {result.phase}, Reason: {result.reason}")
                print()
        except Exception as e:
            unknown += 1
            print(f"  [ERROR] H: {h_str}, T: {t_str}")
            print(f"          {e}")
            print()

    total = correct + incorrect + unknown
    accuracy = correct / total * 100 if total > 0 else 0

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total problems: {total}")
    print(f"Correct:        {correct} ({accuracy:.1f}%)")
    print(f"Incorrect:      {incorrect}")
    print(f"Errors:         {unknown}")
    print()

    if errors:
        print("ERRORS:")
        for h_str, t_str, expected, result in errors:
            print(f"  H: {h_str}")
            print(f"  T: {t_str}")
            print(f"  Expected: {expected}, Got: {result.verdict.value} ({result.phase})")
            print()

    # Byte count check
    v3_path = Path(__file__).parent.parent / "cheatsheet" / "v3.txt"
    if v3_path.exists():
        size = v3_path.stat().st_size
        print(f"Cheatsheet v3 size: {size:,} / 10,240 bytes ({size/10240*100:.1f}%)")
        if size > 10240:
            print("  WARNING: Exceeds 10KB limit!")
        else:
            print(f"  Remaining budget: {10240 - size:,} bytes")


if __name__ == "__main__":
    main()
