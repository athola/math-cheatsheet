"""Unified cheatsheet validation harness.

Validates cheatsheets from five angles:
1. Compliance  — size, encoding, format constraints
2. Structure   — expected sections and technical content
3. Accuracy    — decision procedure correctness on known problems
4. Regression  — cross-version accuracy comparison
5. Competition — evaluation prompt format simulation

Usage:
    python -m src.cheatsheet_harness [ANGLE] [CHEATSHEET_PATH]
    python -m src.cheatsheet_harness compliance cheatsheet/v3.txt
    python -m src.cheatsheet_harness all cheatsheet/final.txt
    python -m src.cheatsheet_harness regression
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.equation_analyzer import (
    ImplicationVerdict,
    analyze_implication,
    parse_equation,
)

# Competition constants
MAX_CHEATSHEET_BYTES = 10_240
CHEATSHEET_DIR = Path(__file__).parent.parent / "cheatsheet"

# Known-answer problems: (hypothesis, target, expected, label)
# These are verified ground-truth implications for testing the decision procedure.
KNOWN_PROBLEMS: list[tuple[str, str, bool, str]] = [
    # --- Phase 1: Instant decisions ---
    ("x * y = y * x", "x * y = y * x", True, "reflexive"),
    ("x * (y * z) = (x * y) * z", "x * (y * z) = (x * y) * z", True, "reflexive-assoc"),
    ("x * y = y * x", "x = x", True, "tautology-target"),
    ("x = y", "x * y = y * x", True, "collapse-H"),
    ("x = y", "x * (y * z) = (x * y) * z", True, "collapse-H-assoc"),
    ("x * x = x", "x = y", False, "collapse-T-non-collapse-H"),
    ("x = x", "x * y = y * x", False, "tautology-H"),
    # --- Phase 2: Variable analysis ---
    ("x * (x * x) = x", "x * y = y * x", False, "new-var-y"),
    ("x * x = x", "x * y = y * x", False, "new-var-idem-to-comm"),
    # --- Phase 3: Substitution ---
    ("x * (y * z) = (x * y) * z", "x * (x * z) = (x * x) * z", True, "subst-y:=x"),
    ("x * (y * z) = (x * y) * z", "x * (y * y) = (x * y) * y", True, "subst-z:=y"),
    # --- Phase 4: Counterexample testing ---
    ("x * (y * z) = (x * y) * z", "x * y = y * x", False, "assoc-!=>-comm"),
    ("x * y = y * x", "x * (y * z) = (x * y) * z", False, "comm-!=>-assoc"),
    ("x * x = x", "x * y = y * x", False, "idem-!=>-comm"),
    ("x * (y * z) = (x * y) * z", "x * x = x", False, "assoc-!=>-idem"),
    # --- Phase 5: Absorption / determined operation ---
    ("x = x * y", "x * x = x", True, "left-abs=>idem"),
    ("x = x * y", "x * (y * z) = (x * y) * z", True, "left-abs=>assoc"),
    ("x = x * y", "x * y = y * x", False, "left-abs-!=>-comm"),
    ("x * y = z * w", "x * y = y * x", True, "constant=>comm"),
    # --- Phase 4 continued ---
    ("x * y = y * x", "x * x = x", False, "comm-!=>-idem"),
]


@dataclass  # Mutable: fields accumulated during validate_compliance()
class ComplianceResult:
    """Result of compliance validation."""

    path: str
    size_bytes: int
    max_bytes: int = MAX_CHEATSHEET_BYTES
    size_ok: bool = False
    is_utf8: bool = False
    no_binary: bool = False
    passed: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def size_pct(self) -> float:
        return self.size_bytes / self.max_bytes * 100

    @property
    def budget_remaining(self) -> int:
        return self.max_bytes - self.size_bytes


@dataclass  # Mutable: fields accumulated during validate_structure()
class StructureResult:
    """Result of structure validation."""

    path: str
    phases_found: list[str] = field(default_factory=list)
    phases_expected: int = 8
    has_quick_reference: bool = False
    has_worked_examples: bool = False
    magmas_found: list[str] = field(default_factory=list)
    key_terms_found: list[str] = field(default_factory=list)
    key_terms_missing: list[str] = field(default_factory=list)
    line_count: int = 0
    passed: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProblemResult:
    """Result of a single problem evaluation."""

    hypothesis: str
    target: str
    expected: bool
    predicted: bool
    correct: bool
    phase: str
    reason: str
    label: str


@dataclass  # Mutable: counters incremented during validate_accuracy()
class AccuracyResult:
    """Result of accuracy validation."""

    total: int = 0
    correct: int = 0
    incorrect: int = 0
    errors: int = 0
    accuracy: float = 0.0
    by_phase: dict[str, dict[str, int]] = field(default_factory=dict)
    failures: list[ProblemResult] = field(default_factory=list)
    passed: bool = False


@dataclass  # Mutable: fields accumulated during validate_regression()
class RegressionResult:
    """Result of cross-version regression testing."""

    versions: dict[str, float] = field(default_factory=dict)
    best_version: str = ""
    regressions: list[str] = field(default_factory=list)
    passed: bool = False


@dataclass  # Mutable: fields set during validate_competition()
class CompetitionResult:
    """Result of competition format simulation."""

    cheatsheet_fits: bool = False
    prompt_size_bytes: int = 0
    estimated_tokens: int = 0
    prompt_preview: str = ""
    passed: bool = False


@dataclass  # Mutable: angles populated incrementally in run_harness()
class HarnessReport:
    """Aggregate report across all validation angles."""

    compliance: ComplianceResult | None = None
    structure: StructureResult | None = None
    accuracy: AccuracyResult | None = None
    regression: RegressionResult | None = None
    competition: CompetitionResult | None = None
    all_passed: bool = False


# ---------------------------------------------------------------------------
# Angle 1: Compliance
# ---------------------------------------------------------------------------


def validate_compliance(cheatsheet_path: Path) -> ComplianceResult:
    """Check size, encoding, and format constraints."""
    result = ComplianceResult(path=str(cheatsheet_path), size_bytes=0)

    if not cheatsheet_path.exists():
        result.errors.append(f"File not found: {cheatsheet_path}")
        return result

    raw = cheatsheet_path.read_bytes()
    result.size_bytes = len(raw)
    result.size_ok = result.size_bytes <= MAX_CHEATSHEET_BYTES

    if not result.size_ok:
        over = result.size_bytes - MAX_CHEATSHEET_BYTES
        result.errors.append(f"Exceeds 10KB limit by {over} bytes")

    # UTF-8 check
    try:
        raw.decode("utf-8")
        result.is_utf8 = True
    except UnicodeDecodeError:
        result.is_utf8 = False
        result.errors.append("Not valid UTF-8")

    # Binary content check (null bytes)
    result.no_binary = b"\x00" not in raw
    if not result.no_binary:
        result.errors.append("Contains null bytes (binary content)")

    result.passed = result.size_ok and result.is_utf8 and result.no_binary
    return result


# ---------------------------------------------------------------------------
# Angle 2: Structure
# ---------------------------------------------------------------------------

# Key technical terms the cheatsheet should contain (with aliases)
_KEY_TERMS = {
    "counterexample": ["counterexample", "counter-example", "counter example"],
    "substitution": ["substitution", "substitute", "specialization"],
    "tautology": ["tautology", "trivially true", "trivial", "reflexive"],
    "variable": ["variable", "vars"],
    "magma": ["magma"],
    "implication": ["implication", "implies", "⇒", "=>"],
    "TRUE": ["true"],
    "FALSE": ["false"],
}

# Canonical magma short names and their descriptive aliases
_MAGMA_NAMES = ["LP", "RP", "C0", "XR", "CM", "N1", "Z3"]
_MAGMA_ALIASES = {
    "LP": ["left projection", "left-projection", "x*y = x", "x*y=x"],
    "RP": ["right projection", "right-projection", "x*y = y", "x*y=y"],
    "C0": ["constant zero", "constant-zero", "x*y = 0", "constant operation"],
    "XR": ["xor", "z2 addition", "addition mod 2"],
    "CM": ["commutative non-associative", "non-associative"],
    "N1": ["non-commutative non-associative", "non-comm"],
    "Z3": ["z/3z", "addition mod 3", "mod 3"],
}


def validate_structure(cheatsheet_path: Path) -> StructureResult:
    """Validate cheatsheet has expected sections and content."""
    result = StructureResult(path=str(cheatsheet_path))

    if not cheatsheet_path.exists():
        result.warnings.append(f"File not found: {cheatsheet_path}")
        return result

    content = cheatsheet_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    result.line_count = len(lines)
    content_upper = content.upper()
    content_lower = content.lower()

    # Check for phase/section markers (two conventions)
    # Convention 1: "PHASE N" (v3 format)
    # Convention 2: "Rule N" / "Strategy N" / "## SECTION" (final/v2 format)
    for i in range(1, 9):
        phase_marker = f"PHASE {i}"
        rule_marker = f"RULE {i}"
        strategy_marker = f"STRATEGY {i}"
        if (
            phase_marker in content_upper
            or rule_marker in content_upper
            or strategy_marker in content_upper
        ):
            result.phases_found.append(phase_marker)

    # Also count markdown heading sections (## HEADING) as structural elements
    section_headings = [
        line.strip()
        for line in lines
        if line.strip().startswith("##") and not line.strip().startswith("###")
    ]
    # If we found few PHASE markers but many ## headings, count headings
    if len(result.phases_found) < 4 and len(section_headings) >= 4:
        for heading in section_headings[:8]:
            marker = heading.lstrip("#").strip().upper()[:30]
            if marker and marker not in [p for p in result.phases_found]:
                result.phases_found.append(f"SECTION: {marker}")

    # Quick reference and worked examples
    result.has_quick_reference = "QUICK REFERENCE" in content_upper
    result.has_worked_examples = (
        "WORKED EXAMPLE" in content_upper
        or "EXAMPLE" in content_upper
        or "PROOF STRATEGY" in content_upper
    )

    # Magma definitions — check both short codes and descriptive aliases
    for name in _MAGMA_NAMES:
        if name in content:
            result.magmas_found.append(name)
            continue
        # Check aliases
        for alias in _MAGMA_ALIASES.get(name, []):
            if alias in content_lower:
                result.magmas_found.append(name)
                break

    # Key terms (check each term against its aliases)
    for term, aliases in _KEY_TERMS.items():
        if any(alias in content_lower for alias in aliases):
            result.key_terms_found.append(term)
        else:
            result.key_terms_missing.append(term)

    # Warnings
    if len(result.phases_found) < result.phases_expected:
        missing = result.phases_expected - len(result.phases_found)
        result.warnings.append(f"Missing {missing} phase/section(s)")

    if not result.has_quick_reference:
        result.warnings.append("No QUICK REFERENCE section found")

    if not result.has_worked_examples:
        result.warnings.append("No worked examples or proof strategy section found")

    if len(result.magmas_found) < 4:
        result.warnings.append(
            f"Only {len(result.magmas_found)} canonical magmas referenced (expected 4+)"
        )

    # Pass if core structure is present
    result.passed = (
        len(result.phases_found) >= 4
        and result.has_worked_examples
        and len(result.magmas_found) >= 3
        and len(result.key_terms_missing) <= 2
    )
    return result


# ---------------------------------------------------------------------------
# Angle 3: Accuracy
# ---------------------------------------------------------------------------


def validate_accuracy(
    problems: list[tuple[str, str, bool, str]] | None = None,
) -> AccuracyResult:
    """Test the decision procedure against known-answer problems."""
    if problems is None:
        problems = KNOWN_PROBLEMS

    result = AccuracyResult(total=len(problems))

    for h_str, t_str, expected, label in problems:
        try:
            h = parse_equation(h_str)
            t = parse_equation(t_str)
            analysis = analyze_implication(h, t)

            predicted = analysis.verdict == ImplicationVerdict.TRUE
            if analysis.verdict == ImplicationVerdict.UNKNOWN:
                predicted = False  # Default FALSE per cheatsheet

            is_correct = predicted == expected
            pr = ProblemResult(
                hypothesis=h_str,
                target=t_str,
                expected=expected,
                predicted=predicted,
                correct=is_correct,
                phase=analysis.phase,
                reason=analysis.reason,
                label=label,
            )

            if is_correct:
                result.correct += 1
            else:
                result.incorrect += 1
                result.failures.append(pr)

            # Track by phase
            phase = analysis.phase
            if phase not in result.by_phase:
                result.by_phase[phase] = {"correct": 0, "incorrect": 0}
            if is_correct:
                result.by_phase[phase]["correct"] += 1
            else:
                result.by_phase[phase]["incorrect"] += 1

        except (ValueError, KeyError) as e:
            result.errors += 1
            result.failures.append(
                ProblemResult(
                    hypothesis=h_str,
                    target=t_str,
                    expected=expected,
                    predicted=False,
                    correct=False,
                    phase="Error",
                    reason=str(e),
                    label=label,
                )
            )

    evaluated = result.total - result.errors
    result.accuracy = result.correct / evaluated if evaluated > 0 else 0.0
    result.passed = result.accuracy >= 0.90 and result.errors == 0
    return result


# ---------------------------------------------------------------------------
# Angle 4: Regression
# ---------------------------------------------------------------------------


def validate_regression(
    cheatsheet_dir: Path | None = None,
) -> RegressionResult:
    """Compare accuracy across all cheatsheet versions.

    This validates that the decision procedure (which the cheatsheets
    teach) produces correct answers, and that structural quality hasn't
    regressed across versions.
    """
    if cheatsheet_dir is None:
        cheatsheet_dir = CHEATSHEET_DIR

    result = RegressionResult()

    # Run accuracy once (procedure is version-independent)
    acc = validate_accuracy()

    # Run structure checks per version
    versions = sorted(cheatsheet_dir.glob("*.txt"))
    for v in versions:
        struct = validate_structure(v)
        # Score: weighted combination of phase coverage + magmas + key terms
        phase_score = len(struct.phases_found) / struct.phases_expected
        magma_score = min(len(struct.magmas_found) / 6, 1.0)
        total_terms = len(struct.key_terms_found) + len(struct.key_terms_missing)
        term_score = len(struct.key_terms_found) / total_terms if total_terms else 0
        combined = phase_score * 0.4 + magma_score * 0.3 + term_score * 0.3
        result.versions[v.stem] = round(combined, 3)

    if result.versions:
        result.best_version = max(result.versions, key=lambda k: result.versions[k])

    # Check for regressions among sequential v-numbered versions only.
    # "final" is a release snapshot — it gets scored but doesn't
    # participate in the sequential regression check.
    v_versions = [
        (name, score)
        for name, score in sorted(result.versions.items())
        if name.startswith("v") and name[1:].isdigit()
    ]
    for i in range(1, len(v_versions)):
        prev_name, prev_score = v_versions[i - 1]
        curr_name, curr_score = v_versions[i]
        if curr_score < prev_score - 0.05:  # allow small tolerance
            result.regressions.append(
                f"{curr_name} ({curr_score:.3f}) regressed vs {prev_name} ({prev_score:.3f})"
            )

    result.passed = len(result.regressions) == 0 and acc.passed
    return result


# ---------------------------------------------------------------------------
# Angle 5: Competition format simulation
# ---------------------------------------------------------------------------

# The evaluation prompt format per the competition playground
_COMPETITION_PROMPT_TEMPLATE = """\
You are given the following reference material (cheatsheet):

<cheatsheet>
{cheatsheet}
</cheatsheet>

Now solve the following problem:

Given that Equation 1: {equation_1}
holds for all elements in a magma (a set with a binary operation *),
does it necessarily follow that Equation 2: {equation_2}
also holds for all elements?

Answer TRUE or FALSE. Provide your reasoning step by step.
"""


def validate_competition(
    cheatsheet_path: Path,
    sample_h: str = "x * (y * z) = (x * y) * z",
    sample_t: str = "x * y = y * x",
) -> CompetitionResult:
    """Simulate the competition evaluation format."""
    result = CompetitionResult()

    if not cheatsheet_path.exists():
        return result

    cheatsheet = cheatsheet_path.read_text(encoding="utf-8")
    prompt = _COMPETITION_PROMPT_TEMPLATE.format(
        cheatsheet=cheatsheet,
        equation_1=sample_h,
        equation_2=sample_t,
    )

    result.prompt_size_bytes = len(prompt.encode("utf-8"))
    # Rough token estimate: ~4 chars per token for English
    result.estimated_tokens = result.prompt_size_bytes // 4
    result.cheatsheet_fits = len(cheatsheet.encode("utf-8")) <= MAX_CHEATSHEET_BYTES
    result.prompt_preview = prompt[:200] + "..."
    result.passed = result.cheatsheet_fits
    return result


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------


def run_harness(
    cheatsheet_path: Path,
    angles: list[str] | None = None,
) -> HarnessReport:
    """Run the full validation harness or selected angles."""
    all_angles = {"compliance", "structure", "accuracy", "regression", "competition"}
    if angles is None:
        angles_set = all_angles
    else:
        angles_set = set(angles) & all_angles

    report = HarnessReport()

    if "compliance" in angles_set:
        report.compliance = validate_compliance(cheatsheet_path)
    if "structure" in angles_set:
        report.structure = validate_structure(cheatsheet_path)
    if "accuracy" in angles_set:
        report.accuracy = validate_accuracy()
    if "regression" in angles_set:
        report.regression = validate_regression()
    if "competition" in angles_set:
        report.competition = validate_competition(cheatsheet_path)

    # All passed = every ran angle passed
    results = [
        r
        for r in [
            report.compliance,
            report.structure,
            report.accuracy,
            report.regression,
            report.competition,
        ]
        if r is not None
    ]
    report.all_passed = all(r.passed for r in results) if results else False
    return report


# ---------------------------------------------------------------------------
# CLI: human-readable output
# ---------------------------------------------------------------------------


def _print_compliance(r: ComplianceResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"COMPLIANCE VALIDATION [{status}]")
    print(f"{'=' * 60}")
    print(f"  File:      {r.path}")
    print(f"  Size:      {r.size_bytes:,} / {r.max_bytes:,} bytes ({r.size_pct:.1f}%)")
    print(f"  Remaining: {r.budget_remaining:,} bytes")
    print(f"  UTF-8:     {'OK' if r.is_utf8 else 'FAIL'}")
    print(f"  No binary: {'OK' if r.no_binary else 'FAIL'}")
    for err in r.errors:
        print(f"  ERROR: {err}")


def _print_structure(r: StructureResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"STRUCTURE VALIDATION [{status}]")
    print(f"{'=' * 60}")
    print(f"  File:           {r.path}")
    print(f"  Lines:          {r.line_count}")
    print(f"  Phases found:   {len(r.phases_found)}/{r.phases_expected}")
    print(f"  Quick ref:      {'Yes' if r.has_quick_reference else 'No'}")
    print(f"  Worked examples:{'Yes' if r.has_worked_examples else 'No'}")
    print(f"  Magmas:         {', '.join(r.magmas_found) or 'None'}")
    total_kw = len(r.key_terms_found) + len(r.key_terms_missing)
    print(f"  Key terms ok:   {len(r.key_terms_found)}/{total_kw}")
    if r.key_terms_missing:
        print(f"  Missing terms:  {', '.join(r.key_terms_missing)}")
    for w in r.warnings:
        print(f"  WARNING: {w}")


def _print_accuracy(r: AccuracyResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"ACCURACY VALIDATION [{status}]")
    print(f"{'=' * 60}")
    print(f"  Total:    {r.total}")
    print(f"  Correct:  {r.correct} ({r.accuracy:.1%})")
    print(f"  Incorrect:{r.incorrect}")
    print(f"  Errors:   {r.errors}")
    if r.by_phase:
        print("  By phase:")
        for phase, counts in sorted(r.by_phase.items()):
            total_p = counts["correct"] + counts["incorrect"]
            acc_p = counts["correct"] / total_p if total_p > 0 else 0
            print(f"    {phase}: {counts['correct']}/{total_p} ({acc_p:.0%})")
    if r.failures:
        print("  Failures:")
        for f in r.failures:
            exp = "TRUE" if f.expected else "FALSE"
            got = "TRUE" if f.predicted else "FALSE"
            print(f"    [{f.label}] Expected {exp}, got {got} ({f.phase}: {f.reason})")


def _print_regression(r: RegressionResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"REGRESSION VALIDATION [{status}]")
    print(f"{'=' * 60}")
    for name, score in sorted(r.versions.items()):
        marker = " <-- best" if name == r.best_version else ""
        print(f"  {name}: {score:.3f}{marker}")
    if r.regressions:
        for reg in r.regressions:
            print(f"  REGRESSION: {reg}")
    else:
        print("  No regressions detected.")


def _print_competition(r: CompetitionResult) -> None:
    status = "PASS" if r.passed else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"COMPETITION FORMAT [{status}]")
    print(f"{'=' * 60}")
    print(f"  Cheatsheet fits: {'Yes' if r.cheatsheet_fits else 'No'}")
    print(f"  Full prompt:     {r.prompt_size_bytes:,} bytes")
    print(f"  Est. tokens:     ~{r.estimated_tokens:,}")


def print_report(report: HarnessReport) -> None:
    """Print a human-readable report."""
    if report.compliance:
        _print_compliance(report.compliance)
    if report.structure:
        _print_structure(report.structure)
    if report.accuracy:
        _print_accuracy(report.accuracy)
    if report.regression:
        _print_regression(report.regression)
    if report.competition:
        _print_competition(report.competition)

    overall = "ALL PASSED" if report.all_passed else "SOME FAILED"
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {overall}")
    print(f"{'=' * 60}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = argv if argv is not None else sys.argv[1:]

    angle = args[0] if args else "all"
    cheatsheet = args[1] if len(args) > 1 else str(CHEATSHEET_DIR / "final.txt")
    path = Path(cheatsheet)

    if angle == "all":
        angles = None
    else:
        angles = [angle]

    report = run_harness(path, angles)
    print_report(report)

    # JSON output to stderr for machine consumption
    if "--json" in args:
        # Serialize with fallback for non-serializable fields
        def _ser(obj):
            if hasattr(obj, "__dict__"):
                return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
            return str(obj)

        json.dump(asdict(report), sys.stdout, indent=2, default=_ser)

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
