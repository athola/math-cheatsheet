# Implementation Plan v2 - SAIR Math Distillation Challenge

**Date**: 2026-03-19
**Branch**: mvp-0.1.0

## Phase 1: Data Foundation

### Task 1.1: Import implication matrix
- Copy CSV to research/data/etp/implications.csv
- Write src/implication_oracle.py: load matrix, query (i,j) → TRUE/FALSE/UNKNOWN
- Validate: 4694 equations, correct value distribution

### Task 1.2: Parse all 4694 equations
- Write src/etp_equations.py: parse full equation list into ASTs
- Store: id, string, AST, variable_set, depth, op_count, is_collapse, is_tautology
- Generate JSON index

### Task 1.3: Classify equations by strength
- Tag each: collapse (implies all), tautology (implied by all), weak, mid, strong
- Based on matrix row/column sums

## Phase 2: Decision Procedure

### Task 2.1: Collapse detection (structural)
- Identify which equations force |M|=1 from structure alone
- Validate against 1496 known collapse equations

### Task 2.2: Variable analysis
- New vars in target → FALSE
- Measure coverage on real matrix

### Task 2.3: Substitution detection
- Target obtainable from hypothesis by variable merging → TRUE

### Task 2.4: Optimal counterexample magmas
- Find minimal magma set that witnesses most FALSE implications
- Use exhaustive size-2 and size-3 search

### Task 2.5: Full evaluation
- Score decision procedure against 22M matrix
- Per-phase accuracy breakdown

## Phase 3: Cheatsheet v4

### Task 3.1: Generate cheatsheet
- Decision tree as LLM instructions (5KB)
- Counterexample table + equivalence hints (5KB)
- <=10,240 bytes total

### Task 3.2: Iterate
- Score → identify failures → refine → re-score
- Target: >=93% accuracy

## Phase 4: Submission Prep
- Competition output format compliance
- Final size check and polish
