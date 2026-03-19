# Competition Rules and Evaluation Framework Analysis

**Research Item**: RESEARCH-002
**Date**: 2026-03-17
**Status**: Complete

---

## Executive Summary

The SAIR Foundation Math Cheatsheet Competition requires creating a 10KB reference document that helps lower-cost LLMs determine equational implication over magmas. Key constraint is the hard 10KB limit against 4694 equations, necessitating aggressive content prioritization.

---

## Competition Constraints

### Technical Constraints

| Constraint | Value | Implications |
|------------|-------|--------------|
| **Cheatsheet Size** | 10KB maximum | ~1500-2000 words; requires aggressive compression |
| **Evaluation Setting** | No-tools | No internet, calculators, or external references |
| **Training Data** | 1200 problems | 1000 regular + 200 hard; indicates difficulty distribution |
| **Task Type** | Binary classification | True/false: "Does E1 imply E2?" |
| **Domain** | Magmas | Binary operation; no other axioms assumed |
| **Equation Count** | 4694 laws | Large search space; cannot memorize all |

### Timeline Constraints

| Milestone | Date | Days from Start |
|-----------|------|-----------------|
| Project Start | March 17, 2026 | 0 |
| Data Acquisition Complete | March 21, 2026 | 4 |
| Cheatsheet v1 Ready | March 28, 2026 | 11 |
| Iteration Complete | April 10, 2026 | 24 |
| **Stage 1 Deadline** | **April 20, 2026** | **34** |

---

## Task Analysis

### Core Question

**"Does Equation 1 imply Equation 2?"**

### Mathematical Definition

E1 implies E2 if every model (magma) that satisfies E1 also satisfies E2.

Formally: E1 ⇒ E2 iff Mod(E1) ⊆ Mod(E2)

Where Mod(E) = set of all magmas satisfying equation E

### Example

```
E1: (x * y) * z = x * (y * z)  [Associativity]
E2: x * x = x                  [Idempotence]

Question: Does E1 imply E2?
Answer: NO
Reason: Counterexample exists (integers under addition)
```

### Implication Types

1. **True Implication**: E2 is provable from E1
2. **False Implication**: Counterexample exists
3. **Equivalence**: Bidirectional implication

---

## Evaluation Framework

### Target Models

**Lower-Cost LLMs**:
- Llama family (Meta)
- Gemini Flash (Google)
- OpenAI OSS models

**Characteristics**:
- Lower parameter count (1B-8B range)
- Faster inference
- Reduced reasoning capability
- Limited context window

### Evaluation Setting

**No-Tools Constraints**:
- No internet access
- No calculators or computational tools
- No external file lookup
- All knowledge must be in-context

**Implication**: Cheatsheet must be:
- Self-contained
- Immediately readable
- Optimized for in-context learning

---

## Success Metrics (Inferred)

| Metric | Measurement | Target |
|--------|-------------|--------|
| **Accuracy** | % correct on test set | Maximize |
| **Size Compliance** | Byte count | ≤ 10,240 bytes |
| **Robustness** | Cross-model performance | Consistent improvement |
| **Efficiency** | Accuracy per byte | High density |

---

## Intelligence Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **Exact evaluation model** | Can't test on target | Test on multiple models |
| **Test distribution** | May overfit | Cross-validation |
| **Scoring formula** | Unknown weighting | Optimize accuracy; size is constraint |
| **Equation format** | Don't know representation | Acquire equations.txt |
| **Methodology** | Proof vs. pattern? | Assume binary answer |

---

## Key Optimization Opportunities

### 1. Information Density Over Coverage

10KB cannot cover 4694 equations (~2 bytes per equation).
**Strategy**: Prioritize high-impact equations and patterns.

### 2. Pattern Over Enumeration

Teaching *how* to reason > listing specific implications.
**Strategy**: Include proof templates and common patterns.

### 3. Counterexamples Over Proofs

Single counterexample disproves; proofs require exhaustive reasoning.
**Strategy**: Include counterexample construction techniques.

### 4. Hub Equation Focus

If implication graph follows power-law, few equations cover most implications.
**Strategy**: Analyze graph; identify hubs; allocate space accordingly.

### 5. Template-Based Reasoning

Structured approaches for common implication types.
**Strategy**: Include step-by-step frameworks.

---

## Constraints for Cheatsheet Design

### Must Haves (Non-Negotiable)

- ✓ Size ≤ 10KB (hard limit)
- ✓ Self-contained (no external references)
- ✓ Text-only (no diagrams)
- ✓ Addresses implication task specifically
- ✓ Readable by lower-cost LLMs

### Should Haves (Important)

- Clear section structure
- Mathematical notation conventions
- Common equation forms
- Proof/counterexample techniques
- Reference tables

### Could Haves (Nice to Have)

- Worked examples
- Visual representations (using text)
- Historical context
- Advanced topics

### Won't Haves (Explicit Exclusions)

- All 4694 equations (impossible in 10KB)
- Comprehensive proof catalog (too verbose)
- External references (not allowed)
- Interactive elements (not possible)

---

## Next Steps

1. **Immediate**: Acquire competition data files
   - equations.txt (4694 laws)
   - train_problems.json (1200 problems)
   - Any implication data if available

2. **Analysis Phase**:
   - Frequency analysis of training problems
   - Equation format parsing
   - Implication graph analysis (if feasible)

3. **Specification Phase**:
   - Define cheatsheet structure based on findings
   - Allocate byte budget per section
   - Establish validation criteria

---

*This analysis will inform the cheatsheet specification (SPEC-001).*
