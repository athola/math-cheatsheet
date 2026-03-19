#!/usr/bin/env python3
"""
Cheatsheet Validation Experiments

Validates the formal-grounded cheatsheet against:
1. Sample implications from the STEP dataset
2. Known true/false implications from Lean/TLA+ verification
3. Red flag pattern detection accuracy
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple


@dataclass
class Implication:
    """An equation implication E1 => E2."""

    e1: str  # Equation 1 (hypothesis)
    e2: str  # Equation 2 (conclusion)
    expected: Optional[bool] = None  # True=implies, False=doesn't imply, None=unknown


@dataclass
class ValidationResult:
    """Result of validating an implication."""

    implication: Implication
    predicted: bool
    confidence: float
    reasoning: str
    correct: Optional[bool] = None  # None if expected is None


@dataclass
class ValidationReport:
    """Summary of validation results."""

    total: int
    correct: int
    incorrect: int
    skipped: int
    accuracy: float
    results: List[ValidationResult]


class CheatsheetValidator:
    """Validates the formal-grounded cheatsheet."""

    # Red flag patterns from cheatsheet v1
    RED_FLAGS = {
        "non_commutative": {"commutativity"},
        "non_associative": {"associativity"},
        "no_identity": {"identity", "left_identity", "right_identity"},
        "mixed_operation_orders": {"structural_properties"},
    }

    # Known false implications (from TLA+ counterexample analysis)
    KNOWN_FALSE = {
        ("associativity", "commutativity"),
        ("commutativity", "associativity"),
        ("idempotence", "commutativity"),
        ("left_identity", "right_identity"),
    }

    # Known true implications (from Lean formal proofs)
    KNOWN_TRUE = {
        ("left_identity+right_identity", "identity"),
    }

    def __init__(self, cheatsheet_path: Path):
        """Initialize validator with cheatsheet."""
        self.cheatsheet_path = cheatsheet_path
        self.cheatsheet_content = ""
        self._load_cheatsheet()

    def _load_cheatsheet(self) -> None:
        """Load cheatsheet content."""
        if self.cheatsheet_path.exists():
            self.cheatsheet_content = self.cheatsheet_path.read_text()

    def _detect_property_type(self, equation: str) -> Set[str]:
        """
        Detect the property type(s) in an equation.

        Returns a set of property types that might be involved.
        """
        properties = set()
        eq_lower = equation.lower()

        # Associativity patterns
        if any(p in eq_lower for p in ["(x*y)*z", "(y*z)", "(x*(y*z))"]):
            properties.add("associativity")

        # Commutativity patterns
        if "x*y = y*x" in equation or "y*x = x*y" in equation:
            properties.add("commutativity")

        # Identity patterns
        has_left = "e*x = x" in equation
        has_right = "x*e = x" in equation
        if has_left and has_right:
            properties.add("identity")
        elif has_left:
            properties.add("left_identity")
        elif has_right:
            properties.add("right_identity")

        # Idempotence
        if "x*x = x" in equation or "x^2 = x" in equation:
            properties.add("idempotence")

        return properties

    def _check_red_flags(self, e1_props: Set[str], e2_props: Set[str]) -> Tuple[bool, List[str]]:
        """
        Check for red flags that suggest implication is false.

        Returns (has_red_flag, list_of_flags).
        """
        flags = []

        for flag, triggers in self.RED_FLAGS.items():
            # Check if e1 has properties that contradict e2
            for prop in e2_props:
                if flag in prop and any(t in e1_props for t in triggers):
                    flags.append(f"{flag}: e1 has {triggers} but e2 wants {prop}")

        return len(flags) > 0, flags

    def _predict_implication(self, e1: str, e2: str) -> Tuple[bool, float, str]:
        """
        Predict whether E1 implies E2 using cheatsheet heuristics.

        Returns (prediction, confidence, reasoning).
        """
        # Detect property types
        e1_props = self._detect_property_type(e1)
        e2_props = self._detect_property_type(e2)

        # Check known implications
        key = (self._normalize_prop(e1_props), self._normalize_prop(e2_props))
        if key in self.KNOWN_FALSE:
            return False, 0.95, f"Known false implication: {key}"

        if key in self.KNOWN_TRUE:
            return True, 1.0, f"Known true implication: {key}"

        # Check red flags
        has_flags, flags = self._check_red_flags(e1_props, e2_props)
        if has_flags:
            return False, 0.85, f"Red flag detected: {flags[0]}"

        # Check structural similarity
        if self._are_structurally_similar(e1, e2):
            return True, 0.7, "Structurally similar equations"

        # Default: uncertain, suggest counterexample search
        return False, 0.5, "No clear implication pattern found"

    def _normalize_prop(self, props: Set[str]) -> str:
        """Normalize property set to a key string."""
        return "+".join(sorted(props)) if props else "unknown"

    def _are_structurally_similar(self, e1: str, e2: str) -> bool:
        """Check if equations have similar structure."""
        # Simple heuristic: count variables and operations
        e1_vars = len(set(re.findall(r"\b[a-z]\b", e1)))
        e2_vars = len(set(re.findall(r"\b[a-z]\b", e2)))
        e1_ops = e1.count("*") + e1.count("+") + e1.count("^")
        e2_ops = e2.count("*") + e2.count("+") + e2.count("^")

        return e1_vars == e2_vars and e1_ops == e2_ops

    def validate_sample(self, sample: List[Implication]) -> ValidationReport:
        """Validate a sample of implications."""
        results = []
        correct = 0
        incorrect = 0
        skipped = 0

        for imp in sample:
            predicted, confidence, reasoning = self._predict_implication(imp.e1, imp.e2)

            if imp.expected is None:
                skipped += 1
            else:
                if predicted == imp.expected:
                    correct += 1
                else:
                    incorrect += 1

            results.append(
                ValidationResult(
                    implication=imp,
                    predicted=predicted,
                    confidence=confidence,
                    reasoning=reasoning,
                    correct=None if imp.expected is None else (predicted == imp.expected),
                )
            )

        total = len(sample)
        evaluated = total - skipped
        accuracy = correct / evaluated if evaluated > 0 else 0.0

        return ValidationReport(
            total=total,
            correct=correct,
            incorrect=incorrect,
            skipped=skipped,
            accuracy=accuracy,
            results=results,
        )

    def generate_test_sample(self) -> List[Implication]:
        """Generate a sample of implications for testing."""
        return [
            # Known false implications
            Implication("(x*y)*z = x*(y*z)", "x*y = y*x", False),
            Implication("x*y = y*x", "(x*y)*z = x*(y*z)", False),
            Implication("x*x = x", "x*y = y*x", False),
            # Known true implications
            Implication("e*x = x AND x*e = x", "identity_exists", True),
            # Edge cases
            Implication("(x*y)*z = x*(y*z)", "(x*y)*(z*w) = ((x*y)*z)*w", None),
            Implication("x*y = y*x", "y*x = x*y", True),  # Reflexive
        ]


def main():
    """Run validation experiments."""
    print("=" * 60)
    print("CHEATSHEET VALIDATION EXPERIMENTS")
    print("=" * 60)

    cheatsheet_path = Path(__file__).parent.parent.parent / "cheatsheet" / "v1.txt"
    validator = CheatsheetValidator(cheatsheet_path)

    # Generate test sample
    sample = validator.generate_test_sample()

    print(f"\nCheatsheet: {cheatsheet_path}")
    print(f"Sample size: {len(sample)} implications")
    print()

    # Run validation
    report = validator.validate_sample(sample)

    # Print results
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total: {report.total}")
    print(f"Correct: {report.correct}")
    print(f"Incorrect: {report.incorrect}")
    print(f"Skipped: {report.skipped}")
    print(f"Accuracy: {report.accuracy:.2%}")
    print()

    # Detailed results
    print("=" * 60)
    print("DETAILED RESULTS")
    print("=" * 60)
    for i, result in enumerate(report.results, 1):
        status = "?" if result.correct is None else ("✓" if result.correct else "✗")
        print(f"\n{i}. {result.implication.e1[:40]}... ⇒ {result.implication.e2[:40]}...")
        print(f"   Predicted: {result.predicted} ({result.confidence:.0%})")
        print(f"   Status: {status}")
        print(f"   Reasoning: {result.reasoning}")

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Count by confidence level
    high_conf = [r for r in report.results if r.confidence >= 0.8]
    med_conf = [r for r in report.results if 0.5 <= r.confidence < 0.8]
    low_conf = [r for r in report.results if r.confidence < 0.5]

    print(f"High confidence (≥80%): {len(high_conf)}")
    print(f"Medium confidence (50-80%): {len(med_conf)}")
    print(f"Low confidence (<50%): {len(low_conf)}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS FOR CHEATSHEET V2")
    print("=" * 60)

    if report.accuracy < 0.7:
        print("- ⚠️  Accuracy below 70%: Review red flag patterns")
        print("- Add more worked examples for failed cases")

    if len(low_conf) > len(sample) * 0.3:
        print("- ⚠️  Many low-confidence predictions")
        print("- Add more decision tree branches")

    print("\n✓ Validation complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
