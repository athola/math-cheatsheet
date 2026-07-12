"""Regression tests for experiments/validation/formal_validation.py.

Full-review 2026-07-12 blocker B4: ``check_lean_proofs`` decided
"Lean verified" via substring matching over raw ``.lean`` text, so the
catalog data records in ``Implication.lean`` (plain String fields, not
theorems) produced ``lean_verified: true`` for implications the project's
own honesty table (docs/formal-verification-summary.md) says are NOT
proven. The checker must instead consult an explicit allow-list of
actually-proven theorems and verify the theorem exists in the cited file.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "experiments" / "validation" / "formal_validation.py"


@pytest.fixture(scope="module")
def fv():
    spec = importlib.util.spec_from_file_location("formal_validation", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _claim(fv, e1: str, e2: str, claim_type: str = "false_implication"):
    return fv.FormalClaim(
        claim_type=claim_type,
        equation_e1=e1,
        equation_e2=e2,
        confidence=0.9,
    )


class TestLeanAllowList:
    """Only implications the honesty table marks Lean-proven may be flagged."""

    def test_assoc_implies_comm_is_not_lean_verified(self, fv) -> None:
        # docs/formal-verification-summary.md: "TLC size-2 witness; not Lean-proven"
        claims = fv.FormalValidator(_ROOT).check_lean_proofs(
            [_claim(fv, "### Associativity", "Commutativity")]
        )
        assert claims[0].lean_verified is False
        assert claims[0].proof_path is None

    def test_comm_implies_assoc_is_not_lean_verified(self, fv) -> None:
        # docs: "catalog (needs size >= 3 model); not proven"
        claims = fv.FormalValidator(_ROOT).check_lean_proofs(
            [_claim(fv, "### Commutativity", "Associativity")]
        )
        assert claims[0].lean_verified is False

    def test_idemp_implies_comm_is_lean_verified_via_invariants(self, fv) -> None:
        # The one machine-checked non-implication: idemp_not_implies_comm.
        claims = fv.FormalValidator(_ROOT).check_lean_proofs(
            [_claim(fv, "### Idempotence", "Commutativity")]
        )
        assert claims[0].lean_verified is True
        assert claims[0].proof_path == "lean/EquationalTheories/Invariants.lean"

    def test_catalog_true_implication_is_not_lean_verified(self, fv) -> None:
        # docs: "Identity + commutative => two-sided identity: catalog / not Lean-proven"
        claims = fv.FormalValidator(_ROOT).check_lean_proofs(
            [
                _claim(
                    fv,
                    "### Left Identity + Right Identity",
                    "Identity",
                    claim_type="true_implication",
                )
            ]
        )
        assert claims[0].lean_verified is False


class TestTlaAllowList:
    """Only Size2Check-witnessed pairs may be flagged TLA-verified."""

    def test_comm_implies_assoc_is_not_tla_verified(self, fv) -> None:
        claims = fv.FormalValidator(_ROOT).check_tla_specs(
            [_claim(fv, "### Commutativity", "Associativity")]
        )
        assert claims[0].tla_verified is False

    def test_assoc_implies_comm_has_size2_witness(self, fv) -> None:
        claims = fv.FormalValidator(_ROOT).check_tla_specs(
            [_claim(fv, "### Associativity", "Commutativity")]
        )
        assert claims[0].tla_verified is True
        assert claims[0].counterexample_path == "tla/MagmaSpecifications/Size2Check.tla"
