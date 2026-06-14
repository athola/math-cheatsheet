# Formal Verification Approach Summary

**Project**: Math Cheatsheet - STEP Equational Theories Challenge
**Date**: March 17, 2026
**Version**: 1.0

---

## Scope and Honesty Note (read first)

This document originally described an aspirational dual-tool verification
pipeline. The reality is narrower, and this note states it plainly so no
claim here is mistaken for more than it is:

- **The cheatsheet is validated empirically, not formally.** Its accuracy
  (98.01% on the 22M-pair matrix) comes from comparison against the ETP
  ground-truth oracle, not from machine-checked proofs.
- **Lean 4 — what is actually proven** (`lean/EquationalTheories/`,
  checked by `lake build`): the implication preorder laws (reflexivity,
  transitivity, equivalence is an equivalence relation), term-evaluation
  and well-formedness lemmas, a handful of concrete Bool witnesses
  (XOR/AND commutative/associative/idempotent), and **one** representative
  non-implication countermodel, `idemp_not_implies_comm` (idempotence ⇏
  commutativity, via the left-projection magma on `Fin 2`). The
  `knownTrue/FalseImplications` lists in `Implication.lean` are **data
  records, not theorems** — they carry a `status`/`confidence` string and
  are not proven in Lean. Proving the remaining catalogued implications is
  tracked as backlog.
- **TLA+ — what is actually checked**: only
  `tla/MagmaSpecifications/Size2Check.tla` parses and is verified by TLC.
  It exhaustively enumerates the 16 size-2 magmas and confirms the exact
  associative/commutative/idempotent counts plus the existence of size-2
  witnesses to `assoc ⇏ comm` and `idemp ⇏ comm`. The other `.tla` files
  in this repo are **illustrative pseudo-specifications that do not parse
  under SANY/TLC** (each carries a STATUS banner saying so) and have never
  model-checked anything.
- **The `src/lean_bridge.py` output is a non-verifying scaffold.** It emits
  a faithful Cayley table plus an `example : True := by trivial`
  placeholder; that body is a tautology and does not witness any
  implication. It must not be described as "verified".

The remainder of this document is the original methodology write-up; treat
its tables as the *intended* design, scoped by the note above.

---

## Executive Summary

This document describes the formal verification methodology used to create and validate the math cheatsheet for equation implications. We employed a dual-tool approach combining **Lean 4** (proof assistant) for theorem proving and **TLA+** (model checker) for counterexample discovery.

---

## Tools and Infrastructure

### Lean 4 (v4.28.0)

**Purpose**: Formal proof verification for true implications

**Setup**:
```bash
# Installation via elan
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Lake project configuration
# lean/EquationalTheories/lakefile.lean
```

**Project Structure**:
- `lean/EquationalTheories/Core.lean` - Core equational theory definitions
- `lean/EquationalTheories/Implication.lean` - Implication verification workflows
- `lean/EquationalTheories/Basic.lean` - Basic magma structures
- `lean/.lake/packages/mathlib/` - Mathlib v4.28.0 dependency

**Key Definitions**:
```lean
structure Magma where
  Carrier : Type
  op : Carrier → Carrier → Carrier

structure Equation where
  lhs : Term
  rhs : Term

def satisfies (M : Magma) (e : Equation) : Prop :=
  -- M satisfies equation e
```

### TLA+ (Model Checker)

**Purpose**: Counterexample discovery for false implications

**Setup**:
- TLA+ Toolbox installation
- TLC model checker configuration
- Custom specification modules

**Project Structure**:
- `tla/MagmaSpecifications/Magma.tla` - Core magma definition
- `tla/MagmaSpecifications/EquationChecking.tla` - Equation verification
- `tla/MagmaSpecifications/MagmaModel.tla` - Model definitions
- `tla/Counterexamples/CounterexampleExplorer.tla` - Counterexample search
- `tla/Counterexamples/counterexample_db.py` - Counterexample database

---

## Formal Verification Workflow

### Step 1: Encode Equations in Lean

Each equation from the STEP dataset is encoded as a Lean structure:

```lean
def associativity : Equation :=
  ⟨Term.app (Term.app (Term.var "x") (Term.var "y")) (Term.var "z"),
   Term.app (Term.var "x") (Term.app (Term.var "y") (Term.var "z"))⟩
```

### Step 2: Prove True Implications

For implications believed to be true, construct formal Lean proofs:

```lean
theorem twoSidedIdentityImpliesLeftIdentity :
  ∀ (M : Magma) (∃ e, ∀ x, M.op e x = x ∧ M.op x e = x) →
  ∃ e, ∀ x, M.op e x = x := by
  -- Proof construction
```

### Step 3: Search for Counterexamples in TLA+

For implications believed to be false, use TLA+ to find countermodels:

```tla
---- MODULE CounterexampleExplorer ----
EXTENDS Magma, EquationChecking

FindCounterexample(e1, e2) ==
  CHOOSE m \in MagmasOfSize(2) :
    Satisfies(m, e1) /\ ~Satisfies(m, e2)
====
```

### Step 4: Extract Patterns

Analyze proofs and counterexamples to extract reusable patterns:

**From Proofs**:
- Identity element rules
- Structural implication rules
- Reflexive equivalence

**From Counterexamples**:
- Red flag patterns (non-commutative, non-associative)
- Small magma search strategies
- Property independence results

---

## Verified Implications

### True Implications (catalog — mostly NOT Lean-proven)

These are entries the decision procedure relies on. Only reflexivity is an
actual Lean theorem (`implication_reflexivity`); the rest are catalog
records / empirically validated, not machine-checked. "Confidence" is a
heuristic label, not a proof status.

| Implication | Confidence | Status |
|-------------|------------|--------|
| Reflexive (identical equations) | 100% | Lean theorem (`implication_reflexivity`) |
| Two-sided identity ⇒ unilateral identity | 100% | catalog / not Lean-proven |
| Identity + commutative ⇒ two-sided identity | 100% | catalog / not Lean-proven |
| Standard ⇒ extended associativity | 75% | heuristic / derivable |

### False Implications (catalog — one Lean-proven, none TLA+-verified)

The only machine-checked non-implication is `idemp ⇒ comm`, proven in Lean
(`idemp_not_implies_comm`) and independently witnessed at size 2 by TLC
(`Size2Check.tla`). The others are catalog entries from empirical search,
not formal proofs. "Confidence" is a heuristic label.

| Implication | Confidence | Status |
|-------------|------------|--------|
| Idempotence ⇒ commutativity | 90% | **Lean-proven** + TLC size-2 witness |
| Associativity ⇒ commutativity | 95% | TLC size-2 witness (`Size2Check`); not Lean-proven |
| Commutativity ⇒ associativity | 95% | catalog (needs size ≥ 3 model); not proven |
| Left identity ⇒ right identity | 85% | catalog / empirical |
| Left identity ⇒ two-sided identity | 85% | catalog / empirical |

---

## Cheatsheet Integration

### From Formal Proofs to Cheatsheet Rules

**Lean Proof → Cheatsheet Rule**:
```
Lean: ∀ M, (∃e, ∀x, e·x = x ∧ x·e = x) → (∃e, ∀x, e·x = x)
↓
Cheatsheet: "IF E₁ has 'e·x = x AND x·e = x' AND E₂ is about identity THEN TRUE"
```

**TLA+ Counterexample → Red Flag**:
```
TLA+: Counterexample found: Matrix multiplication (assoc, not comm)
↓
Cheatsheet: "Red flag: Non-commutative operation ⇒ E₁ ⇒ commutativity FALSE (95%)"
```

### Confidence Levels

| Source | Confidence | Basis |
|--------|------------|-------|
| Lean formal proof | 100% | Mechanically verified (only the lemmas listed in the Scope note above) |
| TLC size-2 model check | high (size 2 only) | Exhaustive over the 16 size-2 magmas (`Size2Check.tla`); says nothing about larger carriers |
| Empirical search / catalog | 85-95% | Compared against the ETP oracle; not a proof |
| Algebraic derivation | 75% | Manual reasoning |
| Heuristic pattern | 50-70% | Inductive inference |

---

## Validation Results

### V1 Validation (Initial)
- Sample accuracy: 66.67%
- Lean coverage: 100%
- TLA+ coverage: 31%
- Issues: Identity compound handling, extended associativity

### V2 Validation (Improved)
- Sample accuracy: 100% (on v2 test cases)
- All critical improvements verified:
  - ✓ Identity compound (AND) handling
  - ✓ Extended associativity support
  - ✓ Reflexive implication detection

---

## File Artifacts

### Lean Proofs
- `lean/EquationalTheories/Core.lean` (225 lines)
- `lean/EquationalTheories/Implication.lean` (145 lines)
- `lean/EquationalTheories/Basic.lean` (structural definitions)

### TLA+ Specifications
- `tla/MagmaSpecifications/*.tla` (core specs)
- `tla/Counterexamples/CounterexampleExplorer.tla` (236 lines)
- `tla/Counterexamples/counterexample_db.py` (244 lines)

### Python ↔ Lean Tooling (v0.2.1)
- `src/lean_bridge.py` — emit a Lean 4 `example` block witnessing a
  FALSE implication, given a finite counterexample magma (#32)
- `src/lean_coverage.py` — scan `.lean` declarations for remaining
  `sorry`/`admit` placeholders and report completion rate (#25)

### Cheatsheet Versions
- `cheatsheet/v1.txt` (6680 bytes, 238 lines) - Initial version
- `cheatsheet/v2.txt` (9570 bytes, 318 lines) - Improved version

### Validation
- `experiments/validation/validate_cheatsheet.py` - Pattern validator
- `experiments/validation/formal_validation.py` - Formal coverage checker
- `experiments/validation/validate_v2.py` - V2 improvement validator
- `experiments/validation/validation_summary.md` - Results summary

---

## Theoretical Foundation

### Magma Definition
A **magma** is a set M with a binary operation * : M × M → M.
No other axioms are assumed.

### Implication Definition
E₁ ⇒ E₂ iff every magma satisfying E₁ also satisfies E₂.
Formally: Mod(E₁) ⊆ Mod(E₂)

### Proof Techniques
1. **Direct Proof**: Assume E₁, derive E2 algebraically
2. **Counterexample**: Find M ∈ Mod(E₁) \ Mod(E₂)
3. **Reflexivity**: E₁ ⇒ E₁ (trivially true)
4. **Symmetry**: For commutativity, x*y = y*x ⇔ y*x = x*y

---

## Reproducibility

### Running Lean Proofs
```bash
cd lean/EquationalTheories
lake build
lake exe build
```

### Running TLA+ Model Checker
Only `Size2Check.tla` is executable under TLC (the other modules are
illustrative pseudo-specs and will not parse):
```bash
cd tla/MagmaSpecifications
java -cp ../tools/tla2tools.jar tlc2.TLC \
  -config Size2Check.cfg Size2Check.tla
```

### Running Validation
```bash
python3 experiments/validation/validate_v2.py
python3 experiments/validation/formal_validation.py
```

---

## Future Work

### Short Term
1. Expand TLA+ coverage for remaining false implications
2. Add more Lean proofs for edge cases
3. Improve confidence calibration

### Long Term
1. Automate Lean proof generation
2. Integrate with formal SAT solvers
3. Build comprehensive implication database

---

## References

1. **Lean Documentation**: https://leanprover.github.io/
2. **TLA+ Specification Language**: https://lamport.azurewebsites.net/tla/tla.html
3. **Mathlib**: https://github.com/leanprover-community/mathlib4
4. **STEP Challenge Rules**: Competition specification document

---

*This summary documents the formal verification approach used to create a rigorously-grounded cheatsheet for the STEP Equational Theories Challenge.*
