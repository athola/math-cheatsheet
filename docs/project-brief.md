# Math Cheatsheet Competition - Project Brief

**Date**: 2026-03-17
**Status**: Draft
**Mission**: Create a 10KB cheatsheet to help lower-cost LLMs solve equational implication problems

---

## Problem Statement

**Who**: Lower-cost LLMs (Llama, Gemini Flash, OpenAI OSS) evaluating mathematical implication questions

**What**: Inability to reliably determine whether Equation 1 implies Equation 2 for magmas (binary algebraic structures with a single binary operation)

**Where**: SAIR Foundation competition no-tools evaluation environment

**When**: Stage 1 deadline April 20, 2026; 1200 training problems available now

**Why**: Current models lack deep equational logic reasoning; 10KB reference must compensate for this gap

**Current State**:
- 4694 equational laws available but unstructured
- No proven methodology for cheatsheet optimization
- Limited understanding of how LLMs utilize mathematical reference material

---

## Goals

1. **Primary**: Create a ≤10KB cheatsheet that measurably improves LLM performance on equational implication tasks
2. **Secondary**: Develop reusable methodology for mathematical knowledge distillation
3. **Tertiary**: Contribute insights to mathematical reasoning research community

---

## Constraints

### Technical
- **10KB hard limit** (~1500-2000 words compressed)
- **Text-only format**: No diagrams, images, or structured data
- **Self-contained**: Must work in no-tools evaluation setting

### Resources
- **Timeline**: ~34 days until deadline (March 17 → April 20)
- **Data**: 1200 training problems, 4694 equations
- **Compute**: Local resources only

### Integration
- Must work with multiple model types (Llama, Gemini Flash, OpenAI OSS)
- Must parse standard equation format from competition
- Must validate against training problems

### Success Criteria
- [ ] Cheatsheet ≤ 10KB
- [ ] Measurable improvement over baseline on training set
- [ ] Validated on at least 2 model types
- [ ] Documented methodology
- [ ] Submitted before April 20, 2026

---

## Approach Comparison

| Approach | Description | Pros | Cons | Risk |
|----------|-------------|------|------|------|
| **Taxonomic** | Organize by mathematical property | Pedagogical, easy to navigate | May miss implications | Low |
| **Graph Hubs** | Focus on high out-degree equations | Data-driven, dense info | Needs computation | High |
| **Proof Strategies** | Teach reasoning techniques | Generalizable | Abstract for LLMs | Medium |
| **Frequency** | Optimize by occurrence | Test-set aligned | Overfitting risk | Medium |
| **Hybrid** | Combine elements | Robust, multi-angle | Complex | Medium |

Scoring: 🟢 = Good, 🟡 = Acceptable, 🔴 = Concern

---

## War Room Decision

**Session**: war-room-20260317-cheatsheet-strategy
**RS**: 0.44 (Type 1B) | **Mode**: Lightweight with Full Analysis

### Selected Approach: Adaptive Hybrid Strategy (Phased)

Rather than committing to a single structure, we use a **two-phase approach**:

**Phase 1: Data-Agnostic Foundation** (Immediate)
- Core definitions: magma, equational logic, implication
- Basic properties: associativity, commutativity, identity, inverse
- Simple proof patterns: direct proof, counterexample basics

**Phase 2: Data-Driven Optimization** (After data acquisition)
- Frequency analysis: Which equations appear most?
- Graph analysis: Are there hub equations?
- Allocate remaining space to proven high-impact content

This is **staged commitment, not avoidance** — we start with safe foundation, then optimize based on evidence.

### Reversal Plan

- If graph shows no hubs → Fall back to frequency optimization
- If frequency is uniform → Fall back to taxonomic approach
- If LLM shows no improvement → Pivot to proof strategy focus

### Intelligence Gaps

1. equations.txt format: How are 4694 equations structured?
2. train_problems.json format: How are implication problems posed?
3. Evaluation model: Which specific lower-cost LLMs?
4. Implication data: Pre-computed or must we compute?

---

## Next Steps

1. **RESEARCH-001** (Current): Draft taxonomic foundation
   - Write core definitions and concepts
   - Document basic property taxonomy
   - Describe foundational proof techniques

2. **RESEARCH-002**: Acquire and analyze competition data
   - Download equations.txt and train_problems.json
   - Analyze equation formats and structures
   - Perform frequency analysis

3. **RESEARCH-003**: Research state-of-the-art in mathematical reasoning
   - Study Honda, Murakami, Zhang (2025) findings
   - Investigate few-shot learning for math
   - Review prompt engineering techniques

4. **SPEC-001**: Create cheatsheet specification
   - Define detailed structure based on research
   - Establish size budgets per section
   - Set validation criteria

5. **PLAN-001**: Design experimentation strategy
   - Plan data pipeline and analysis
   - Design evaluation methodology
   - Establish iteration framework

---

*This project brief will evolve as research progresses and data is acquired.*
