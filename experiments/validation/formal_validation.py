#!/usr/bin/env python3
"""
Formal Validation Experiments

Integrates Lean proofs and TLA+ model checking to validate
the cheatsheet's formal verification claims.
"""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Machine-checked artifacts, keyed by (claim_type, e1_property, e2_property).
# Source of truth: the status tables in docs/formal-verification-summary.md.
# Do NOT add entries here without an actual theorem/TLC run backing them.
#
# Lean entries map to (theorem_name, proof_file); check_lean_proofs verifies
# the theorem is really declared in that file before trusting the entry.
_LEAN_PROVEN: dict[tuple[str, str | None, str | None], tuple[str, str]] = {
    ("false_implication", "idempotence", "commutativity"): (
        "idemp_not_implies_comm",
        "lean/EquationalTheories/Invariants.lean",
    ),
}

# Pairs exhaustively witnessed at size 2 by TLC via Size2Check.tla.
_TLC_WITNESSED: dict[tuple[str, str | None, str | None], str] = {
    ("false_implication", "idempotence", "commutativity"): (
        "tla/MagmaSpecifications/Size2Check.tla"
    ),
    ("false_implication", "associativity", "commutativity"): (
        "tla/MagmaSpecifications/Size2Check.tla"
    ),
}


@dataclass
class FormalClaim:
    """A claim from the cheatsheet with formal verification status."""

    claim_type: str  # "true_implication", "false_implication", "property"
    equation_e1: str
    equation_e2: str | None
    confidence: float
    lean_verified: bool = False
    tla_verified: bool = False
    proof_path: str | None = None
    counterexample_path: str | None = None


@dataclass
class FormalValidationReport:
    """Report on formal verification status."""

    total_claims: int
    lean_verified: int
    tla_verified: int
    both_verified: int
    not_verified: int
    claims: list[FormalClaim]


class FormalValidator:
    """Validates formal verification claims in the cheatsheet."""

    def __init__(self, project_root: Path):
        """Initialize validator with project paths."""
        self.project_root = project_root
        self.cheatsheet_path = project_root / "cheatsheet" / "v1.txt"

    def scan_cheatsheet_claims(self) -> list[FormalClaim]:
        """Scan the cheatsheet for formal verification claims."""
        claims = []
        content = self.cheatsheet_path.read_text()

        # Parse KNOWN FALSE IMPLICATIONS section
        in_false_section = False
        for line in content.split("\n"):
            if "KNOWN FALSE IMPLICATIONS" in line:
                in_false_section = True
                continue
            if "KNOWN TRUE IMPLICATIONS" in line:
                in_false_section = False
                continue

            # Extract implication claims
            if "⇒" in line or "=>" in line:
                parts = line.split("⇒") if "⇒" in line else line.split("=>")
                if len(parts) == 2:
                    e1 = parts[0].strip().split(":")[0].strip()
                    e2 = parts[1].strip().split(":")[0].strip()

                    # Extract confidence if present
                    confidence = 0.9  # default
                    for token in line.split():
                        if "%" in token:
                            try:
                                confidence = float(token.rstrip("%")) / 100
                            except ValueError:
                                pass

                    claim_type = "false_implication" if in_false_section else "true_implication"
                    claims.append(
                        FormalClaim(
                            claim_type=claim_type,
                            equation_e1=e1,
                            equation_e2=e2,
                            confidence=confidence,
                        )
                    )

        return claims

    def check_lean_proofs(self, claims: list[FormalClaim]) -> list[FormalClaim]:
        """Check which claims are covered by an actually-proven Lean theorem.

        Earlier versions matched keywords against raw ``.lean`` text, which
        misread the catalog data records in ``Implication.lean`` (plain
        String fields, not theorems) as proofs and contradicted the status
        tables in ``docs/formal-verification-summary.md``. Verification now
        requires the claim's property pair to be in the explicit allow-list
        AND the named theorem to be declared in the cited file.
        """
        for claim in claims:
            key = self._claim_key(claim)
            entry = _LEAN_PROVEN.get(key)
            if entry is None:
                continue
            theorem_name, rel_path = entry
            proof_file = self.project_root / rel_path
            if proof_file.exists() and f"theorem {theorem_name}" in proof_file.read_text():
                claim.lean_verified = True
                claim.proof_path = rel_path

        return claims

    def check_tla_specs(self, claims: list[FormalClaim]) -> list[FormalClaim]:
        """Check which claims have a machine-checked TLC witness.

        Only ``Size2Check.tla`` is TLC-verified (see the honesty note in
        ``docs/formal-verification-summary.md``); the other ``.tla`` files
        are illustrative pseudo-specs. A claim is TLA-verified only if its
        property pair is in the Size2Check witness allow-list.
        """
        for claim in claims:
            rel_path = _TLC_WITNESSED.get(self._claim_key(claim))
            if rel_path is not None and (self.project_root / rel_path).exists():
                claim.tla_verified = True
                claim.counterexample_path = rel_path

        return claims

    def _claim_key(self, claim: FormalClaim) -> tuple[str, str | None, str | None]:
        """Normalize a claim to (claim_type, e1_property, e2_property)."""
        return (
            claim.claim_type,
            self._property_of(claim.equation_e1),
            self._property_of(claim.equation_e2 or ""),
        )

    @staticmethod
    def _property_of(text: str) -> str | None:
        """Map free-form cheatsheet claim text to a canonical property name."""
        text = text.lower()
        if "assoc" in text:
            return "associativity"
        if "commut" in text:
            return "commutativity"
        if "idempot" in text:
            return "idempotence"
        if "left identity" in text:
            return "left_identity"
        if "right identity" in text:
            return "right_identity"
        if "identity" in text or "e*x" in text:
            return "identity"
        return None

    def generate_report(self, claims: list[FormalClaim]) -> FormalValidationReport:
        """Generate formal validation report."""
        lean_verified = sum(1 for c in claims if c.lean_verified)
        tla_verified = sum(1 for c in claims if c.tla_verified)
        both_verified = sum(1 for c in claims if c.lean_verified and c.tla_verified)

        return FormalValidationReport(
            total_claims=len(claims),
            lean_verified=lean_verified,
            tla_verified=tla_verified,
            both_verified=both_verified,
            not_verified=sum(1 for c in claims if not c.lean_verified and not c.tla_verified),
            claims=claims,
        )

    def save_report(self, report: FormalValidationReport, output_path: Path) -> None:
        """Save validation report to JSON."""
        data = {
            "summary": {
                "total_claims": report.total_claims,
                "lean_verified": report.lean_verified,
                "tla_verified": report.tla_verified,
                "both_verified": report.both_verified,
                "not_verified": report.not_verified,
                "lean_coverage": report.lean_verified / report.total_claims
                if report.total_claims > 0
                else 0,
                "tla_coverage": report.tla_verified / report.total_claims
                if report.total_claims > 0
                else 0,
            },
            "claims": [asdict(c) for c in report.claims],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")  # keep the committed report end-of-file-fixer clean


def main():
    """Run formal validation experiments."""
    print("=" * 60)
    print("FORMAL VALIDATION EXPERIMENTS")
    print("=" * 60)

    project_root = Path(__file__).parent.parent.parent
    validator = FormalValidator(project_root)

    # Scan cheatsheet for claims
    print("\n1. Scanning cheatsheet for formal claims...")
    claims = validator.scan_cheatsheet_claims()
    print(f"   Found {len(claims)} formal claims")

    # Check Lean proofs
    print("\n2. Checking Lean formal proofs...")
    claims = validator.check_lean_proofs(claims)
    lean_verified = sum(1 for c in claims if c.lean_verified)
    print(f"   {lean_verified}/{len(claims)} claims have Lean proofs")

    # Check TLA+ specs
    print("\n3. Checking TLA+ specifications...")
    claims = validator.check_tla_specs(claims)
    tla_verified = sum(1 for c in claims if c.tla_verified)
    print(f"   {tla_verified}/{len(claims)} claims have TLA+ specs")

    # Generate report
    report = validator.generate_report(claims)

    # Print summary
    print("\n" + "=" * 60)
    print("FORMAL VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total claims: {report.total_claims}")
    lean_pct = report.lean_verified / report.total_claims * 100
    tla_pct = report.tla_verified / report.total_claims * 100
    print(f"Lean verified: {report.lean_verified} ({lean_pct:.1f}%)")
    print(f"TLA+ verified: {report.tla_verified} ({tla_pct:.1f}%)")
    print(f"Both verified: {report.both_verified}")
    print(f"Not verified: {report.not_verified}")

    # Save report
    output_path = project_root / "experiments" / "validation" / "formal_validation_report.json"
    validator.save_report(report, output_path)
    print(f"\nReport saved to: {output_path}")

    # Print detailed claims
    print("\n" + "=" * 60)
    print("DETAILED CLAIMS")
    print("=" * 60)
    for i, claim in enumerate(claims, 1):
        lean_status = "✓" if claim.lean_verified else "✗"
        tla_status = "✓" if claim.tla_verified else "✗"
        print(f"\n{i}. [{claim.claim_type}] {claim.equation_e1} ⇒ {claim.equation_e2}")
        print(f"   Confidence: {claim.confidence:.0%}")
        print(f"   Lean: {lean_status} | TLA+: {tla_status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
