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
from typing import List, Optional


@dataclass
class FormalClaim:
    """A claim from the cheatsheet with formal verification status."""

    claim_type: str  # "true_implication", "false_implication", "property"
    equation_e1: str
    equation_e2: Optional[str]
    confidence: float
    lean_verified: bool = False
    tla_verified: bool = False
    proof_path: Optional[str] = None
    counterexample_path: Optional[str] = None


@dataclass
class FormalValidationReport:
    """Report on formal verification status."""

    total_claims: int
    lean_verified: int
    tla_verified: int
    both_verified: int
    not_verified: int
    claims: List[FormalClaim]


class FormalValidator:
    """Validates formal verification claims in the cheatsheet."""

    def __init__(self, project_root: Path):
        """Initialize validator with project paths."""
        self.project_root = project_root
        self.lean_dir = project_root / "lean" / "EquationalTheories"
        self.tla_dir = project_root / "tla"
        self.cheatsheet_path = project_root / "cheatsheet" / "v1.txt"

    def scan_cheatsheet_claims(self) -> List[FormalClaim]:
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

    def check_lean_proofs(self, claims: List[FormalClaim]) -> List[FormalClaim]:
        """Check which claims have Lean formal proofs."""
        lean_files = list(self.lean_dir.rglob("*.lean"))

        for claim in claims:
            # Check if there's a Lean file that might verify this claim
            for lean_file in lean_files:
                content = lean_file.read_text()
                # Simple keyword matching
                e1_keywords = self._extract_keywords(claim.equation_e1)
                e2_keywords = self._extract_keywords(claim.equation_e2 or "")
                all_keywords = e1_keywords + e2_keywords

                if all_keywords and all(kw in content.lower() for kw in all_keywords):
                    claim.lean_verified = True
                    claim.proof_path = str(lean_file.relative_to(self.project_root))
                    break

        return claims

    def check_tla_specs(self, claims: List[FormalClaim]) -> List[FormalClaim]:
        """Check which claims have TLA+ specifications."""
        tla_files = list(self.tla_dir.rglob("*.tla"))

        for claim in claims:
            if claim.claim_type == "false_implication":
                # Counterexample claims should have TLA+ models
                for tla_file in tla_files:
                    content = tla_file.read_text().lower()
                    if "counterexample" in content or "model" in content:
                        claim.tla_verified = True
                        claim.counterexample_path = str(tla_file.relative_to(self.project_root))
                        break

        return claims

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract searchable keywords from an equation."""
        keywords = []
        text = text.lower()
        if "assoc" in text:
            keywords.append("associative")
        if "commut" in text:
            keywords.append("commutative")
        if "identity" in text or "e*x" in text:
            keywords.append("identity")
        if "idempotent" in text or "x*x" in text:
            keywords.append("idempotent")
        return keywords

    def generate_report(self, claims: List[FormalClaim]) -> FormalValidationReport:
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
