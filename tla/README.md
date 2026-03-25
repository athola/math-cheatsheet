# TLA+ Formal Verification for Magma Theory

This directory contains TLA+ specifications for exploring finite magma state spaces and verifying equational implications through model checking.

## Directory Structure

```
tla/
├── MagmaSpecifications/
│   ├── Magma.tla              # Basic magma definitions and properties
│   ├── EquationChecking.tla   # Term evaluation and equation satisfaction
│   ├── MagmaModel.tla         # Concrete magma models for testing
│   ├── TEST_MODEL.tla         # Test theorems and property checking
│   ├── MagmaModel.cfg         # TLC configuration for MagmaModel
│   └── EquationChecking.cfg   # TLC configuration for equation checking
└── Counterexamples/           # (TODO) Automated counterexample generation
```

## Prerequisites

1. **TLA+ Toolbox**: Download from https://lamport.azurewebsites.net/tla/toolbox.html
2. **TLC Model Checker**: Included with Toolbox
3. **Python 3.8+**: For wrapper scripts

## Key Modules

### Magma.tla
Defines the fundamental magma structure:
- `Magma`: Set with binary operation (no axioms required)
- `Associative`: Property for semigroups
- `Commutative`: Property for commutative operations
- `HasIdentity`: Property for monoids
- `CayleyTable`: Generate operation table

### EquationChecking.tla
Term evaluation and equation verification:
- `Eval(term)`: Evaluate a term under variable assignment
- `EquationSatisfied(eqn)`: Check if equation holds for all assignments
- `FindCounterexample(eqn)`: Find assignment where equation fails
- `ImplicationHolds(E1, E2)`: Check if E1 ⇒ E2 in current magma

### MagmaModel.tla
Concrete magma examples:
- `M2_XOR`: 2-element XOR group (Z/2Z)
- `M2_AND`: 2-element AND semilattice
- `M2_OR`: 2-element OR semilattice
- `M3_Z3`: 3-element cyclic group
- `M4_Klein`: Klein four-group
- `NonAssociativeMagma`: Counterexample to associativity
- `NonCommutativeMagma`: Counterexample to commutativity

## Running Model Checker

### Via Toolbox (GUI)
1. Open TLA+ Toolbox
2. Create new spec → Add `Magma.tla`, `EquationChecking.tla`, `MagmaModel.tla`
3. Create model → Use `.cfg` files or configure manually
4. Run model checker

### Via Command Line
```bash
# Navigate to TLA+ Tools directory
cd /path/to/tla/tools

# Run TLC on test model
java -cp tla2tools.jar tlc2.TLC \
  -depth 10 \
  -deadlock \
  /home/alext/math-cheatsheet/tla/MagmaSpecifications/TEST_MODEL
```

### Via Python Wrapper
```python
from tla_wrapper import run_tlc, parse_tlc_output

# Run model checker
result = run_tlc("TEST_MODEL", specs=["Magma", "EquationChecking", "MagmaModel"])

# Parse results
if result["status"] == "success":
    print("All properties verified!")
else:
    print(f"Counterexample found: {result['counterexample']}")
```

## Equation Encoding

Equations are encoded as pairs of term representations:

```
Term := Variable | ["*", Term, Term]
Variable := ["x"] | ["y"] | ["z"] | ...
Equation := [Term, Term]
```

Examples:
- **Associativity**: `(x*y)*z = x*(y*z)`
  ```tla
  [["*", ["*", ["x"], ["y"]], ["z"]],
   ["*", ["x"], ["*", ["y"], ["z"]]]
  ```

- **Commutativity**: `x*y = y*x`
  ```tla
  [["*", ["x"], ["y"]],
   ["*", ["y"], ["x"]]]
  ```

- **Idempotence**: `x*x = x`
  ```tla
  [["*", ["x"], ["x"]],
   ["x"]]
  ```

## Implication Verification

To check if equation E1 implies E2:

```tla
\* Direct implication check
ImplicationHolds(E1, E2) ==
    EquationSatisfied(E1) => EquationSatisfied(E2)

\* Find counterexample to implication
\* (i.e., state where E1 holds but E2 doesn't)
FindImplicationCounterexample(E1, E2) ==
    CHOOSE assign \in AllAssignments(...) :
        /\ Eval(E1[1]) = Eval(E1[2])
        /\ Eval(E2[1]) # Eval(E2[2])
```

## Integration with Lean

The TLA+ and Lean 4 components work together:

| Aspect | TLA+ | Lean 4 |
|--------|------|--------|
| **Strength** | Finite model enumeration | General constructive proofs |
| **Output** | Counterexamples to false implications | Proof witnesses for true implications |
| **Scope** | Small finite magmas (|S| ≤ 4) | All magmas (general) |
| **Use Case** | "Red flag" patterns | "Hub equation" identification |

## Usage Patterns for Cheatsheet Development

1. **Find counterexamples**: Use TLA+ to explore small magmas and find where implications fail
2. **Identify red flags**: Patterns that frequently produce counterexamples become "red flags" in cheatsheet
3. **Verify with Lean**: Promising implications from Lean analysis get verified with TLA+ counterexample search
4. **Generate training data**: Counterexamples train ML models to predict implication validity

## Performance Considerations

- **State space explosion**: For magma of size n, there are n^(n²) possible operations
- **Practical limits**: TLC can handle magmas up to ~4 elements for full enumeration
- **Optimization strategies**:
  - Use symmetry reduction
  - Exploit equation constraints to prune search space
  - Parallel model checking with TLC's distributed mode

## References

- Lamport, L. (2002). "Specifying Systems: The TLA+ Language and Tools for Hardware and Software Engineers"
- STEP dataset: 4694 equational laws for magmas
- Equational Theories project (MIT): Formalizing implications in Lean 4

## Next Steps

- [ ] Complete TLAP-001: Test all modules with TLC
- [ ] Implement FORMAL-003: Automated counterexample generation
- [ ] Build counterexample database for ML training
- [ ] Integrate with Lean implication verification results
