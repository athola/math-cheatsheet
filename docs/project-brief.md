# SAIR Math Distillation Challenge - Project Brief v2

**Date**: 2026-03-19
**Status**: Active
**Deadline**: April 20, 2026 (Stage 1)

## Problem Statement

The SAIR Foundation Math Distillation Challenge asks participants to create a
<=10KB plain text cheatsheet that maximizes an LLM's accuracy on equational
implication problems. Given two equations over magmas (sets with a binary
operation), the model must determine: does Equation 1 imply Equation 2?

The problem space is the Equational Theories Project (ETP) by Terence Tao et al:
4694 equational laws yielding 22,028,942 ordered implication pairs.

## Data Analysis (Key Findings)

### Implication Matrix (export_raw_implications_3_19_2026.csv)
- 4694 equations, 22M pairs
- Encoding: 3=proven TRUE, -3=proven FALSE, 4=conj TRUE, -4=conj FALSE
- Overall: 37.1% TRUE, 60.2% FALSE, 2.7% unresolved

### Structural Decomposition
| Category | Equations | % | Implies N others |
|----------|-----------|---|-----------------|
| Collapse (force \|M\|=1) | 1,496 | 31.9% | All 4694 |
| Weak (almost nothing) | 614 | 13.1% | <=5 |
| Mid-range | 898 | 19.1% | 100-1000 |
| Strong non-collapse | ~1,086 | 23.1% | 1000-4600 |
| Tautology (x=x) | 1 | 0.02% | 1 (itself) |

### The 86% Rule
85.9% of all TRUE implications originate from the 1,496 collapse equations.
Among non-collapse pairs, only 7.7% are TRUE (92.3% FALSE).

### Accuracy Projections
| Strategy | Expected Accuracy |
|----------|------------------|
| Always FALSE | 62.9% |
| Collapse detection + default FALSE | ~90% |
| + variable analysis | ~93% |
| + substitution + counterexamples | ~96%+ |

## Goals

1. **Primary**: Maximize Stage 1 accuracy (TRUE/FALSE correctness)
2. **Secondary**: Build evaluation harness to measure accuracy on real data
3. **Tertiary**: Prepare for Stage 2 (counterexamples, proofs, confidence)

## Success Criteria

- [ ] Cheatsheet <= 10,240 bytes
- [ ] Accuracy > 90% on competition problems (1200 selected from 22M)
- [ ] Evaluation harness tests against real implication matrix
- [ ] Decision procedure handles all 4694 equations

## Constraints

- **Size**: 10KB plain text (no code, no binary)
- **Format**: Injected into Jinja2 prompt as `{{ cheatsheet }}`
- **Evaluation**: LLM reads cheatsheet + equation pair, outputs TRUE/FALSE
- **Time**: ~30 days to deadline
- **Data**: Full 22M implication matrix available for training/validation

## Approach Comparison

### Approach 1: Rule-Based Decision Tree (SELECTED)
Encode a decision tree the LLM can follow step-by-step:
1. Classify equation structure (collapse, tautology, variable count, depth)
2. Apply structural rules (variable analysis, substitution)
3. Consult a compact counterexample table for common FALSE cases
4. Default to FALSE for unresolved cases

**Pros**: Interpretable, fits 10KB, LLM can follow, leverages data analysis
**Cons**: Can't encode all 22M implications, misses edge cases
**Risk**: Medium — depends on LLM's ability to execute algebraic reasoning

### Approach 2: Compressed Lookup Table
Encode key implication facts directly (e.g., equivalence classes, key pairs).
Use the 10KB to store the most frequently tested implications.

**Pros**: Direct answers for known problems, no reasoning required
**Cons**: Can only store ~500-1000 facts in 10KB, fragile to new problems
**Risk**: High — if competition problems aren't in the table, accuracy drops

### Approach 3: Hybrid (Rules + Selective Lookup)
Combine structural rules (5KB) with a compact lookup table of the hardest
non-collapse TRUE implications (5KB). Rules handle the easy 90%, lookup
handles the hard 10%.

**Pros**: Best of both, data-driven optimization of lookup portion
**Cons**: More complex cheatsheet, harder to debug
**Risk**: Low-medium — two layers of defense

### Selection: Approach 3 (Hybrid)

**Rationale**: The data shows a clear structural decomposition:
- Collapse detection + variable analysis handles ~93% (rules portion)
- The remaining 7% of TRUE cases in non-collapse pairs need specific
  algebraic knowledge (lookup portion)
- 10KB splits naturally: ~5KB rules + ~5KB curated facts

## Architecture

```
Input: (Equation 1, Equation 2)
  │
  ├─ Phase 0: Parse equations (structural features)
  ├─ Phase 1: Instant decisions
  │   ├─ Self-implication (identical) → TRUE
  │   ├─ Tautology target (x=x) → TRUE
  │   ├─ Collapse hypothesis → TRUE
  │   └─ Tautology hypothesis + non-tautology target → FALSE
  ├─ Phase 2: Variable analysis
  │   └─ New variable in target → FALSE
  ├─ Phase 3: Substitution detection
  │   └─ Target is specialization of hypothesis → TRUE
  ├─ Phase 4: Structural pattern matching
  │   ├─ Absorption/projection detection → determined operation
  │   └─ Counterexample magma table → FALSE
  ├─ Phase 5: Equivalence class lookup
  │   └─ Known equivalence classes → same answer
  └─ Default: FALSE
```

## Out of Scope (for Stage 1)

- Lean proof generation
- Confidence calibration
- Full 22M implication encoding
- Stage 2 counterexample format

## Implementation Plan

### Phase 1: Data Integration (Days 1-3)
- Import full 4694-equation list with ETP numbering
- Parse and index the 22M implication matrix
- Build accuracy evaluation against real data

### Phase 2: Cheatsheet Optimization (Days 4-10)
- Implement rule-based decision tree
- Identify optimal counterexample magmas (data-driven)
- Optimize lookup table for hardest TRUE cases
- Iterative: generate cheatsheet → evaluate → refine

### Phase 3: Evaluation & Hardening (Days 11-15)
- Test against normal.jsonl (1000 problems) and hard.jsonl (200 problems)
- A/B test cheatsheet variants
- Size optimization (fit within 10KB)

### Phase 4: Competition Submission (Days 16-30)
- Final cheatsheet polishing
- Stage 2 preparation (counterexample format)
- Documentation

## Key Files

- `research/data/etp/` — Full ETP equation list and implication matrix
- `src/etp_parser.py` — Parse ETP equations into structured format
- `src/implication_oracle.py` — Query the 22M implication matrix
- `src/cheatsheet_optimizer.py` — Generate and evaluate cheatsheets
- `src/evaluator.py` — Score cheatsheet against competition problems
- `cheatsheet/v4.txt` — Competition cheatsheet (<=10KB)
