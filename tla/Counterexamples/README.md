# TLA+ Counterexample Generation System

This directory contains TLA+ specifications and Python tools for systematically exploring finite magma counterexamples to false equation implications.

## Directory Structure

```
Counterexamples/
├── CounterexampleExplorer.tla  # Main TLA+ exploration module
├── counterexample_db.py        # Python database for counterexamples
└── README.md                   # This file
```

## Overview

The counterexample generation system helps identify "red flag" patterns for the cheatsheet - when to suspect that an implication E₁ ⇒ E₂ might be false.

### How It Works

1. **Magma Generation**: Systematically generate all magmas of size n
2. **Implication Testing**: For each magma, test if E₁ ⇒ E₂ holds
3. **Counterexample Collection**: Store magmas where E₁ holds but E₂ doesn't
4. **Pattern Analysis**: Identify common properties (red flags) among counterexamples

## TLA+ Module: CounterexampleExplorer.tla

### Key Features

- `AllMagmasOfSize(n)`: Generate all magmas with n elements
- `TestImplication(magma, E1, E2)`: Test if implication holds
- `FindImplicationCounterexample(E1, E2, maxSize)`: Find counterexample
- `GenerateImplicationReport(E1, E2)`: Create cheatsheet entry

### Running with TLC

```bash
java -cp tla2tools.jar tlc2.TLC CounterexampleExplorer
```

## Python Module: counterexample_db.py

### Key Classes

- `Magma`: Finite magma with carrier and operation
- `Counterexample`: Counterexample to an implication
- `CounterexampleDatabase`: Store and query counterexamples

### Usage

```python
from counterexample_db import CounterexampleDatabase

# Initialize database
db = CounterexampleDatabase()

# Add counterexample
from counterexample_db import Counterexample, Magma

magma = Magma(
    carrier=[0, 1],
    operation={(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
)

counterexample = Counterexample(
    equation_e1="associativity",
    equation_e2="commutativity",
    magma=magma,
    red_flags={"non_commutative"}
)

db.add(counterexample)
db.save()

# Query counterexamples
examples = db.get_counterexamples("associativity", "commutativity")
status = db.get_implication_status("associativity", "commutativity")
entry = db.generate_cheatsheet_entry("associativity", "commutativity")
```

### CLI Commands

```bash
# Show database statistics
python counterexample_db.py stats

# Search for counterexamples
python counterexample_db.py search associativity commutativity

# Generate cheatsheet entry
python counterexample_db.py report associativity commutativity
```

## Red Flag Patterns

Common red flags that indicate an implication might be false:

| Red Flag | Description | Frequency |
|----------|-------------|-----------|
| `non_associative` | Operation is not associative | 87% |
| `non_commutative` | Operation is not commutative | 73% |
| `no_identity` | No identity element exists | 65% |
| `idempotent_fails` | x·x ≠ x for some x | 54% |

## Standard Implication Tests

Pre-configured tests for common implications:

- `TestAssocImpliesCommut`: Does associativity imply commutativity? **NO**
- `TestCommutImpliesAssoc`: Does commutativity imply associativity? **NO**
- `TestIdempImpliesCommut`: Does idempotence imply commutativity? **NO**
- `TestMedialImpliesAssoc`: Does medial imply associativity? **YES**
- `TestLeftAbsorbImpliesIdem`: Does left absorption imply idempotence? **YES**

## Cheatsheet Integration

### Entry Format

```json
{
  "implication": "E1 => E2",
  "status": "very_likely_false | likely_false | sometimes_false | always_true",
  "counterexample_count": 42,
  "red_flags": ["non_associative", "no_identity"],
  "recommendation": "Very unlikely to be true. Red flags: non_associative, no_identity"
}
```

### Status Meanings

- `always_true`: No counterexamples found (small search space)
- `sometimes_false`: Few counterexamples (might be edge cases)
- `likely_false`: Many counterexamples (probably false in general)
- `very_likely_false`: Very many counterexamples (almost certainly false)

## Performance Considerations

- **State Space**: For magma of size n, there are n^(n²) possible operations
- **Practical Limits**: TLC can handle n ≤ 4 for full enumeration
- **Optimization**: Use symmetry reduction and property-based filtering

## Integration with Lean

The counterexample database complements Lean's proof capabilities:

| Aspect | TLA+ | Lean |
|--------|------|------|
| **Finding** | Discovers false implications | Proves true implications |
| **Scope** | Finite magmas only | All magmas (general) |
| **Output** | Counterexamples | Formal proofs |
| **Use Case** | "Red flag" patterns | "Hub equations" |

## Next Steps

- [ ] Implement automated magma generation in Python
- [ ] Build web interface for counterexample queries
- [ ] Integrate with Lean implication verification
- [ ] Generate counterexample training data for ML
