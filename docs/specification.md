# SAIR Math Distillation Challenge - Specification v2

**Date**: 2026-03-19
**Status**: Active
**Deadline**: April 20, 2026

## Overview

Build a system that generates an optimal <=10KB cheatsheet for the SAIR
Math Distillation Challenge. The cheatsheet guides an LLM to correctly
answer "Does Equation 1 imply Equation 2?" for equational laws of magmas.

**Input**: 4694 equations from the Equational Theories Project, 22M implication pairs
**Output**: cheatsheet/v4.txt (<=10,240 bytes) maximizing TRUE/FALSE accuracy

## Functional Requirements

### FR-001: ETP Data Integration

**Description**: Parse and index the full 4694-equation dataset and 22M implication matrix.

**Acceptance Criteria**:
- [ ] Parse all 4694 equations from ETP format (◇ operator, variables x,y,z,w,u,v)
- [ ] Load the 4693x4694 CSV implication matrix into queryable format
- [ ] Decode values: 3=proven TRUE, -3=proven FALSE, 4=conj TRUE, -4=conj FALSE
- [ ] Query any (eq_i, eq_j) pair in <1ms
- [ ] Classify each equation: collapse/tautology/weak/mid/strong

**Priority**: High | **Effort**: M

### FR-002: Equation Structural Analyzer

**Description**: Extract structural features from any equation for rule-based classification.

**Acceptance Criteria**:
- [ ] Parse equation string into AST (Term tree with Var/Op nodes)
- [ ] Extract: variable set, variable count, depth, operation count, tree shape
- [ ] Detect collapse equations (force |M|=1)
- [ ] Detect tautology (LHS == RHS structurally)
- [ ] Detect absorption patterns (x = x◇y, x = y◇x, etc.)
- [ ] Detect substitution relationships between equation pairs
- [ ] Handle all 4694 equations without errors

**Priority**: High | **Effort**: L

### FR-003: Implication Decision Procedure

**Description**: Multi-phase decision procedure that determines TRUE/FALSE for equation pairs.

**Acceptance Criteria**:
- [ ] Phase 0: Parse both equations into ASTs
- [ ] Phase 1: Instant decisions (identity, tautology target, collapse hypothesis)
- [ ] Phase 2: Variable analysis (new vars in target → FALSE)
- [ ] Phase 3: Substitution detection (target is specialization → TRUE)
- [ ] Phase 4: Counterexample testing against canonical magmas
- [ ] Phase 5: Equivalence class lookup
- [ ] Default: FALSE
- [ ] Accuracy >= 90% on the full 22M implication matrix
- [ ] Accuracy >= 93% on the 1200 competition problems

**Priority**: High | **Effort**: XL

### FR-004: Cheatsheet Generator

**Description**: Generate a <=10KB plain text cheatsheet encoding the decision procedure.

**Acceptance Criteria**:
- [ ] Output fits in 10,240 bytes
- [ ] Contains: structural rules, decision tree, counterexample table
- [ ] Follows the competition Jinja2 prompt format
- [ ] Human-readable (an LLM must follow the instructions)
- [ ] Includes required output format (VERDICT, REASONING, PROOF, COUNTEREXAMPLE)
- [ ] Optimized against real competition data

**Priority**: High | **Effort**: L

### FR-005: Competition Evaluator

**Description**: Score a cheatsheet's decision procedure against real competition problems.

**Acceptance Criteria**:
- [ ] Evaluate against the full 22M implication matrix (batch mode)
- [ ] Evaluate against competition problem sets (normal.jsonl, hard.jsonl)
- [ ] Report: accuracy, precision, recall, confusion matrix
- [ ] Breakdown by equation category (collapse, variable, substitution, etc.)
- [ ] Compare multiple cheatsheet versions
- [ ] Run in <5 minutes for full 22M evaluation

**Priority**: High | **Effort**: M

### FR-006: Counterexample Magma Discovery

**Description**: Find the minimal set of finite magmas that witness the most FALSE implications.

**Acceptance Criteria**:
- [ ] For each FALSE implication, find a magma where hypothesis holds but conclusion fails
- [ ] Rank magmas by coverage (how many FALSE pairs they witness)
- [ ] Select top-N magmas that maximize FALSE coverage
- [ ] Encode selected magmas compactly for the cheatsheet
- [ ] Cover >= 80% of non-trivial FALSE implications with <= 10 magmas

**Priority**: Medium | **Effort**: L

## Non-Functional Requirements

### NFR-001: Performance
- Implication oracle: <1ms per query
- Full 22M evaluation: <5 minutes
- Cheatsheet generation: <1 minute

### NFR-002: Data Integrity
- All 4694 equations parseable without error
- Implication matrix matches ETP source exactly

## Key Data Facts

| Metric | Value |
|--------|-------|
| Total equations | 4,694 |
| Proven TRUE | 8,178,279 (37.1%) |
| Proven FALSE | 13,855,357 (62.9%) |
| Collapse equations | 1,496 (31.9%) |
| TRUE from collapse | 85.9% of all TRUE |
| Non-collapse TRUE rate | 7.7% |
| Equivalence classes | 4,015 unique patterns |
| Always-FALSE baseline | 62.9% accuracy |
| Collapse+default baseline | ~90% accuracy |

## Out of Scope (Stage 1)

- LLM-in-the-loop evaluation (no API calls to test cheatsheet with real LLM)
- Lean proof generation
- Stage 2 counterexample format
- Confidence calibration

## Success Criteria

- [ ] cheatsheet/v4.txt <= 10,240 bytes
- [ ] Decision procedure accuracy >= 93% on competition problems
- [ ] All 4694 equations handled correctly
- [ ] Evaluation harness runs against real implication matrix
