# TLA+ Magma Specifications

This directory contains TLA+ specifications for exploring finite magmas and verifying equational implications.

## Files

### Magma.tla
Core magma specification defining:
- Magma structure (set with binary operation)
- Algebraic properties (associativity, commutativity, identity)
- Cayley table generation
- Model checking helpers

### EquationChecking.tla
Equation verification module:
- Term representation and evaluation
- Equation satisfaction checking
- Counterexample finding
- Common equation templates (associativity, commutativity, etc.)

### MagmaModel.tla
Concrete magma models for testing:
- Small magmas (size 1-4)
- Counterexample magmas (non-associative, non-commutative)
- Common algebraic structures (groups, Klein four-group)

### MagmaProperties.cfg
Model checker configuration for verifying properties.

## Usage

### Manual Model Checking with TLA+ Toolbox:

1. Install TLA+ Toolbox from https://lamport.azurewebsites.net/tla/toolbox.html
2. Open Magma.tla in the Toolbox
3. Create a new model
4. Configure constants (S, op)
5. Run TLC model checker

### Programmatic Usage (via PlusCal or Python integration):

For automated counterexample generation, use the Python integration in `../python/`.

## Key Concepts

### Magma
A magma is the most basic algebraic structure: a set with a binary operation. No axioms required.

### Equation Encoding
Equations are encoded as pairs of terms. Terms are sequences:
- `["x"]` represents variable x
- `["*", t1, t2]` represents (t1 * t2)

### Counterexample Finding
To find a counterexample to an implication E1 => E2:
1. Find a magma where E1 holds
2. Check if E2 also holds
3. If E2 doesn't hold, we have a counterexample

## Integration with Lean

- TLA+ provides finite model exploration
- Lean provides proof verification
- Together they give a complete verification pipeline:
  - Lean proves implications (soundness)
  - TLA+ finds counterexamples (completeness for finite models)

## References

- TLA+ Specification Language: https://lamport.azurewebsites.net/tla/tla.html
- Equational Logic: "A Tarski-Frege proof system for equational logic"
- Universal Algebra: Burris & Sankappanavar
