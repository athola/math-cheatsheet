# Math Cheatsheet - Specification v1.0

**Author**: Egregore Autonomous Research Agent
**Date**: 2026-03-17
**Status**: Draft
**Competition**: SAIR Foundation Equational Theories Challenge

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-03-17 | Egregore | Initial specification from research phase |
| 0.2.0 | 2026-03-17 | Egregore | **ADDED: Formal verification requirements (Lean + TLA+)** |

---

## Overview

**Purpose**: Create a 10KB reference document that enables lower-cost LLMs to accurately determine whether one equational law implies another for magmas (algebraic structures with a single binary operation).

**Scope**:
- **IN**: Reference document covering equational implication concepts, techniques, and patterns; structured for LLM consumption; optimized for 10KB constraint
- **OUT**: All 4694 equations (impossible), interactive elements, external references, visual diagrams

**Stakeholders**:
- **Lower-cost LLMs** (Primary): Target users who will consume the cheatsheet during inference
- **Competition Evaluators** (Secondary): Will assess cheatsheet compliance and effectiveness
- **Research Team** (Tertiary): Will validate and iterate on cheatsheet design

---

## Functional Requirements

### FR-001: Implication Task Support

**Description**: The cheatsheet must provide sufficient information for LLMs to determine whether Equation 1 implies Equation 2 for magmas.

**Acceptance Criteria**:
- [ ] Given an implication question about equational laws, when the LLM accesses the cheatsheet, then it can identify appropriate solution strategies
- [ ] Given a false implication case, when the LLM applies cheatsheet techniques, then it can construct or identify counterexamples
- [ ] Given a true implication case, when the LLM follows cheatsheet proof patterns, then it can derive the implication

**Priority**: Critical
**Dependencies**: None
**Estimated Effort**: L

---

### FR-002: Mathematical Foundation Coverage

**Description**: The cheatsheet must explain core concepts: magmas, equational laws, implication, and proof/counterexample techniques.

**Acceptance Criteria**:
- [ ] Given the cheatsheet, when an LLM reads the foundation section, then it understands what a magma is (set with binary operation)
- [ ] Given the cheatsheet, when an LLM encounters an implication question, then it understands the formal definition (E1 ⇒ E2 iff all E1-models satisfy E2)
- [ ] Given the cheatsheet, when an LLM needs to prove/disprove implication, then it has access to proof and counterexample construction methods

**Priority**: Critical
**Dependencies**: None
**Estimated Effort**: M

---

### FR-003: Counterexample Construction Techniques

**Description**: The cheatsheet must prioritize counterexample construction as the primary disproof method, based on SOTA research findings.

**Acceptance Criteria**:
- [ ] Given an implication question, when the LLM consults the cheatsheet, then it finds structured guidance on counterexample construction
- [ ] Given the counterexample section, when the LLM applies the techniques, then it can systematically test potential counterexamples
- [ ] Given common equation families, when the LLM searches the cheatsheet, then it finds example counterexamples for frequently-tested implications

**Priority**: Critical
**Dependencies**: FR-002
**Estimated Effort**: L

---

### FR-004: Property Taxonomy Reference

**Description**: The cheatsheet must organize equational properties taxonomically (associative, commutative, identity, inverse, distributive).

**Acceptance Criteria**:
- [ ] Given an equation involving a specific property, when the LLM references the cheatsheet, then it can locate the relevant property section
- [ ] Given the property taxonomy, when the LLM studies relationships, then it understands which properties imply others
- [ ] Given multiple properties, when the LLM analyzes an equation, then it can identify which properties are present

**Priority**: High
**Dependencies**: FR-002
**Estimated Effort**: M

---

### FR-005: Worked Examples

**Description**: The cheatsheet must include 5-7 worked examples demonstrating both true and false implications.

**Acceptance Criteria**:
- [ ] Given the worked examples section, when the LLM studies the cases, then it sees step-by-step reasoning for each
- [ ] Given true implication examples, when the LLM analyzes them, then it understands the proof structure
- [ ] Given false implication examples, when the LLM analyzes them, then it sees the counterexample construction

**Priority**: High
**Dependencies**: FR-002, FR-003
**Estimated Effort**: M

---

### FR-006: Proof Templates

**Description**: The cheatsheet must provide structured proof templates for common implication types.

**Acceptance Criteria**:
- [ ] Given an implication question, when the LLM identifies its type, then it finds a corresponding proof template
- [ ] Given the proof templates, when the LLM applies them, then it can structure its reasoning systematically
- [ ] Given template-based reasoning, when the LLM follows the steps, then it produces coherent derivations

**Priority**: Medium
**Dependencies**: FR-002
**Estimated Effort**: M

---

### FR-007: Notation and Conventions

**Description**: The cheatsheet must establish clear mathematical notation conventions to reduce confusion.

**Acceptance Criteria**:
- [ ] Given the notation guide, when the LLM reads an equation, then it can interpret all symbols correctly
- [ ] Given variable conventions (x, y, z for elements; * for operation), when the LLM encounters them, then it understands their meaning
- [ ] Given quantifier notation (∀, ∃), when the LLM sees them, then it interprets them correctly

**Priority**: Medium
**Dependencies**: None
**Estimated Effort**: S

---

### FR-008: Size Compliance

**Description**: The cheatsheet must not exceed 10KB (10,240 bytes) in size.

**Acceptance Criteria**:
- [ ] Given the completed cheatsheet, when measured by byte count, then it is ≤ 10,240 bytes
- [ ] Given size pressure during development, when content is added, then lower-priority content is removed before exceeding limit
- [ ] Given the final version, when validated, then it includes margin (≤ 9,500 bytes target) for safety

**Priority**: Critical
**Dependencies**: All (enforces constraint)
**Estimated Effort**: M

---

### FR-009: LLM Readability

**Description**: The cheatsheet must be structured and formatted for optimal LLM consumption.

**Acceptance Criteria**:
- [ ] Given the cheatsheet structure, when an LLM processes it, then it can identify sections via clear headings
- [ ] Given section ordering, when the LLM reads sequentially, then it encounters concepts from simple to complex
- [ ] Given cross-references, when the LLM needs related information, then it can find explicit links ("see Section 3.2")

**Priority**: High
**Dependencies**: None
**Estimated Effort**: S

---

### FR-010: Self-Contained Content

**Description**: The cheatsheet must be entirely self-contained with no external dependencies.

**Acceptance Criteria**:
- [ ] Given any term or concept in the cheatsheet, when an LLM encounters it, then it is defined within the document
- [ ] Given any notation or symbol, when the LLM sees it, then it is explained in the notation guide
- [ ] Given the complete document, when audited for external references, then none are found

**Priority**: Critical
**Dependencies**: None
**Estimated Effort**: M

---

### FR-011: Lean Formal Verification (CRITICAL - NEW)

**Description**: All implication claims in the cheatsheet must be formally verified using Lean 4 proof assistant.

**Acceptance Criteria**:
- [ ] Given any implication claim in the cheatsheet, when checked in Lean, then there exists a formal proof or counterexample
- [ ] Given counterexamples provided, when encoded in Lean, then they are verified as valid countermodels
- [ ] Given proof patterns, when implemented as Lean tactics, then they produce correct results
- [ ] Lean proof artifacts included in submission package

**Priority**: Critical (Competition Requirement)
**Dependencies**: None
**Estimated Effort**: XL (40-60 hours including Lean learning curve)

**Rationale**: Competition requires formal verification. Lean provides mathematical rigor for all claims.

---

### FR-012: TLA+ Specification and Verification (CRITICAL - NEW)

**Description**: Algebraic structures and properties must be specified and verified using TLA+ model checker.

**Acceptance Criteria**:
- [ ] Given magma definitions, when specified in TLA+, then they are syntactically correct
- [ ] Given key properties (associativity, commutativity), when model-checked, then they are verified for invariants
- [ ] Given state space models, when analyzed by TLC, then they produce verification results
- [ ] TLA+ specifications included in submission package

**Priority**: Critical (Competition Requirement)
**Dependencies**: None
**Estimated Effort**: XL (30-50 hours including TLA+ learning curve)

**Rationale**: Competition requires formal verification. TLA+ provides model checking for algebraic properties.

---

## Non-Functional Requirements

### NFR-001: Performance - Size Constraint

**Requirement**: Cheatsheet must be ≤ 10,240 bytes

**Measurement**:
- Metric: Byte count using `wc -c cheatsheet.txt`
- Target: ≤ 9,500 bytes (10,240 hard limit)
- Tool: Unix `wc` command or equivalent

**Priority**: Critical

---

### NFR-002: Performance - Information Density

**Requirement**: Achieve high information density through notation and compression

**Measurement**:
- Metric: Concepts per 1KB (target: ≥ 5 distinct concepts/techniques per KB)
- Target: ≥ 47 unique concepts in 10KB
- Tool: Manual content audit

**Priority**: High

---

### NFR-003: Usability - LLM Comprehension

**Requirement**: Content must be structured for lower-cost LLM processing

**Measurement**:
- Metric: Reading grade level (target: ≤ 15 for technical content)
- Target: Clear hierarchical structure, explicit examples
- Tool: Flesch-Kincaid or similar readability analysis

**Priority**: High

---

### NFR-004: Reliability - Accuracy

**Requirement**: All mathematical statements must be formally correct

**Measurement**:
- Metric: Error rate (target: 0 mathematical errors)
- Target: 100% accuracy on all claims
- Tool: Expert mathematical review

**Priority**: Critical

---

### NFR-005: Maintainability - Iterative Improvement

**Requirement**: Cheatsheet structure must support iterative refinement

**Measurement**:
- Metric: Time to create modified version (target: ≤ 1 hour)
- Target: Modular section design enables A/B testing
- Tool: Version control and section isolation

**Priority**: Medium

---

### NFR-006: Performance - Cross-Model Consistency

**Requirement**: Cheatsheet must work effectively across different LLM families

**Measurement**:
- Metric: Accuracy variance across models (target: ≤ 15% variance)
- Target: Consistent improvement for Llama, Gemini Flash, OpenAI OSS
- Tool: Multi-model evaluation

**Priority**: High

---

## Technical Constraints

### Size Constraints

| Constraint | Value | Notes |
|------------|-------|-------|
| **Maximum Size** | 10,240 bytes | Hard limit; submissions exceeding are disqualified |
| **Target Size** | ≤ 9,500 bytes | Safety margin for encoding differences |
| **Minimum Size** | ≥ 5,000 bytes | Too small lacks sufficient content |
| **Word Count** | ~1,500-2,000 words | Approximate; byte count is authoritative |

### Format Constraints

| Constraint | Value | Notes |
|------------|-------|-------|
| **File Type** | Plain text (.txt) | No markdown, HTML, or formatting |
| **Encoding** | UTF-8 or ASCII | Must be universally readable |
| **Line Endings** | Unix (LF) | Consistent with competition systems |
| **Max Line Length** | No specified limit | But keep reasonable for readability |

### Content Constraints

| Constraint | Value | Notes |
|------------|-------|-------|
| **External References** | Prohibited | Must be self-contained |
| **Diagrams/Images** | Prohibited | Text-only format |
| **Hyperlinks** | Not allowed | No external URLs |
| **Executable Code** | Not relevant | Reference document only |

---

## Cheatsheet Structure Specification

### Byte Budget Allocation

| Section | Bytes | Percentage | Priority |
|---------|-------|------------|----------|
| **1. Core Concepts** | 1,500 | 15% | Critical |
| **2. Counterexamples** | 3,000 | 30% | Critical |
| **3. Property Taxonomy** | 2,000 | 20% | High |
| **4. Proof Patterns** | 2,000 | 20% | High |
| **5. Worked Examples** | 1,500 | 15% | High |
| **Total Target** | **10,000** | **100%** | - |
| **Safety Margin** | **-500** | - | - |
| **Final Target** | **≤ 9,500** | - | - |

---

### Section 1: Core Concepts (1,500 bytes)

**Purpose**: Foundational definitions and problem understanding

**Content Requirements**:
```
1.1 What is a Magma? (200B)
   - Definition: Set + binary operation
   - No other axioms assumed
   - Notation: (M, *)

1.2 What is Implication? (300B)
   - Definition: E1 ⇒ E2 iff all E1-models satisfy E2
   - Formal notation
   - Intuitive explanation

1.3 Task Format (200B)
   - Question structure: "Does E1 imply E2?"
   - Expected answer: YES or NO with reasoning
   - Binary classification

1.4 Basic Proof Concepts (400B)
   - Direct proof: Assume E1, derive E2
   - Counterexample: Find E1-model that violates E2
   - Why counterexamples are powerful (single disproof)

1.5 Notation Guide (400B)
   - Variables: x, y, z for elements
   - Operation: * (or ·, +)
   - Quantifiers: ∀ (for all), ∃ (exists)
   - Set notation: ∈ (in), ⊆ (subset)
```

**Validation**:
- All terms defined before use
- Clear hierarchical structure
- Mathematical notation explained

---

### Section 2: Counterexamples (3,000 bytes)

**Purpose**: Systematic counterexample construction (highest ROI per SOTA research)

**Content Requirements**:
```
2.1 Counterexample Framework (800B)
   Step 1: Understand E1's requirements
   Step 2: Identify a structure satisfying E1
   Step 3: Test if structure violates E2
   Step 4: If yes → E1 does NOT imply E2

2.2 Common Counterexample Families (1,200B)
   Family A: Numeric structures (ℤ, ℚ, ℝ)
     - Addition: associative, commutative
     - Multiplication: associative, commutative
     - Subtraction: neither

   Family B: Function composition
     - Associative but not commutative
     - Rich counterexample source

   Family C: String concatenation
     - Associative, commutative only for trivial cases
     - Useful for specific implications

   Family D: Matrix operations
     - Matrix multiplication: associative, not commutative
     - Specific counterexamples

2.3 Counterexample Construction Templates (600B)
   Template 1: Start with known property, test target
   Template 2: Modify known structure to remove property
   Template 3: Combine structures to isolate behavior

2.4 Worked Counterexamples (400B)
   Example 1: Associativity does NOT imply commutativity
   Example 2: Identity does NOT imply inverse
   Example 3: Left-identity does NOT imply right-identity
```

**Validation**:
- At least 3 distinct counterexample families
- Step-by-step construction framework
- Concrete examples before abstract patterns

---

### Section 3: Property Taxonomy (2,000 bytes)

**Purpose**: Organize equational properties by mathematical structure

**Content Requirements**:
```
3.1 Associative Properties (500B)
   - Definition: (x*y)*z = x*(y*z)
   - Implications: What associativity enables
   - Does NOT imply: commutativity, identity

3.2 Commutative Properties (400B)
   - Definition: x*y = y*x
   - Implications: Symmetry properties
   - Does NOT imply: associativity

3.3 Identity Elements (400B)
   - Definition: ∃e ∀x: e*x = x*e = x
   - Left-identity vs. right-identity
   - Bidirectional identity implications

3.4 Inverse Properties (350B)
   - Definition: For each x, ∃x⁻¹: x*x⁻¹ = e
   - Requires identity first
   - Group properties

3.5 Distributive Properties (350B)
   - Definition: Operations interacting
   - Two-operation structures
   - Ring-like properties
```

**Validation**:
- Each property clearly defined
- Implication relationships stated
- Cross-references to counterexamples

---

### Section 4: Proof Patterns (2,000 bytes)

**Purpose**: Structured reasoning templates for implication proofs

**Content Requirements**:
```
4.1 Direct Proof Template (500B)
   Given: E1 as assumption
   Step 1: Express E1 in algebraic form
   Step 2: Apply valid transformations
   Step 3: Derive E2 from transformations
   Step 4: Verify each step is valid
   Conclusion: E1 implies E2

4.2 Deduction Chains (400B)
   Pattern: E1 → intermediate → E2
   Example: Associative + identity → other properties
   Chain construction guidelines

4.3 Property Inference Rules (600B)
   Rule 1: If E has identity and inverses → group properties
   Rule 2: If E is commutative and associative → abelian properties
   Rule 3: Left and right versions → bidirectional implications
   Rule 4: Combination properties → derived behaviors

4.4 Proof by Contradiction (300B)
   Assume E1 true AND E2 false
   Derive logical inconsistency
   Conclude: E1 must imply E2

4.5 Verification Steps (200B)
   Check: Are all steps valid?
   Check: Are assumptions justified?
   Check: Does conclusion follow?
```

**Validation**:
- Templates are generalizable
- Step-by-step structure maintained
- Applicable across property types

---

### Section 5: Worked Examples (1,500 bytes)

**Purpose**: Demonstrate application of techniques

**Content Requirements**:
```
Example 1: True Implication (400B)
  E1: (x*y)*z = x*(y*z) [Associativity]
  E2: (x*y)*(z*w) = ((x*y)*z)*w [Extended associativity]
  Reasoning: [Step-by-step proof]
  Answer: YES

Example 2: False Implication (400B)
  E1: x*y = y*x [Commutativity]
  E2: (x*y)*z = x*(y*z) [Associativity]
  Counterexample: [Function composition]
  Answer: NO

Example 3: Property Interaction (350B)
  E1: Identity + commutative
  E2: x⁻¹*x = e (inverse property)
  Analysis: [Reasoning about implications]
  Answer: NO (inverse not guaranteed)

Example 4: Bidirectional Implication (350B)
  E1: Left-identity + right-identity
  E2: Bidirectional identity
  Analysis: [Proof that they are equivalent]
  Answer: YES (both directions)
```

**Validation**:
- Mix of true and false implications
- Step-by-step reasoning shown
- Techniques from earlier sections applied

---

## Content Guidelines

### Notation Conventions

| Concept | Notation | Example |
|---------|----------|---------|
| Elements | x, y, z, a, b | x * y = y * x |
| Operation | *, ·, + | (x * y) * z |
| Identity | e | e * x = x |
| Inverse | x⁻¹ | x * x⁻¹ = e |
| For all | ∀ | ∀x,y: x*y = y*x |
| Exists | ∃ | ∃e: ∀x: e*x = x |
| In set | ∈ | x ∈ M |
| Subset | ⊆ | Mod(E1) ⊆ Mod(E2) |

### Style Guidelines

1. **Be Concise**: Remove filler words; use symbolic notation
2. **Be Explicit**: Define all terms before use
3. **Be Structured**: Use clear hierarchy with numbered sections
4. **Be Concrete**: Give examples before generalizations
5. **Be Precise**: Mathematical language must be exact

### Compression Techniques

1. **Symbolic Notation**: Use ∀ instead of "for all"
2. **Template Statements**: "For all x,y: property" instead of enumerating
3. **Cross-References**: "See Section 2.3" instead of repeating
4. **Pattern Grouping**: Describe families, not individual instances

---

## Out of Scope

### Explicitly Excluded (v1.0)

- **All 4694 Equations**: Impossible in 10KB; must prioritize
- **Visual Diagrams**: Text-only format required
- **Interactive Elements**: Not supported in evaluation setting
- **Historical Context**: Not relevant for task performance
- **Advanced Topics**: Category theory, universal algebra beyond basics
- **External References**: Must be self-contained

**Rationale**: The 10KB constraint forces aggressive prioritization. Every byte must directly contribute to the implication task. Educational content, however interesting, is excluded if it doesn't improve task performance.

---

## Dependencies

### External Dependencies

- **None**: Cheatsheet must be self-contained

### Data Dependencies

- **equations.txt**: 4694 equational laws (to be acquired)
- **train_problems.json**: 1200 training problems (to be acquired)
- **implication_graph**: If available (to be computed or acquired)

### Tool Dependencies

- **Byte counter**: `wc -c` or equivalent for size validation
- **LLM evaluation**: Access to lower-cost LLMs for testing
- **Version control**: Git for iteration tracking

---

## Acceptance Testing Strategy

### Phase 1: Content Validation

**Test**: Review all mathematical statements for accuracy
**Method**: Expert mathematical review
**Criteria**: Zero errors

### Phase 2: Size Validation

**Test**: Measure byte count
**Method**: `wc -c cheatsheet.txt`
**Criteria**: ≤ 9,500 bytes (target), ≤ 10,240 bytes (hard limit)

### Phase 3: LLM Evaluation

**Test**: Measure accuracy improvement on training problems
**Method**:
1. Baseline: LLM without cheatsheet
2. Test: LLM with cheatsheet
3. Compare: % improvement
**Criteria**: ≥ 10% improvement over baseline

### Phase 4: Cross-Model Validation

**Test**: Verify cheatsheet works across different LLM families
**Method**: Test on Llama, Gemini Flash, OpenAI OSS
**Criteria**: ≤ 15% variance in improvement across models

### Phase 5: Ablation Study

**Test**: Measure each section's contribution
**Method**: Remove each section, measure performance delta
**Criteria**: Identify high/low-value sections for optimization

---

## Success Criteria

- [ ] Cheatsheet size ≤ 10,240 bytes (hard limit)
- [ ] Cheatsheet size ≤ 9,500 bytes (target)
- [ ] Zero mathematical errors (verified by review)
- [ ] ≥ 10% accuracy improvement over baseline on training set
- [ ] Consistent improvement across ≥ 2 LLM families
- [ ] All terms defined before use (self-contained)
- [ ] Clear hierarchical structure (LLM-readable)
- [ ] At least 5 worked examples included
- [ ] Counterexample construction emphasized (per SOTA)

---

## Glossary

| Term | Definition |
|------|------------|
| **Magma** | A set M with a binary operation * : M × M → M |
| **Equation** | A statement that must hold for all elements of a magma |
| **Implication** | E1 ⇒ E2 means every magma satisfying E1 also satisfies E2 |
| **Model** | A specific magma that satisfies a given equation |
| **Counterexample** | A model satisfying E1 but not E2, disproving implication |
| **Associative** | (x*y)*z = x*(y*z) for all x, y, z |
| **Commutative** | x*y = y*x for all x, y |
| **Identity** | Element e such that e*x = x*e = x for all x |
| **Inverse** | For each x, element x⁻¹ such that x*x⁻¹ = e |

---

## References

### Research Documents

1. **docs/project-brief.md** - Project overview and approach selection
2. **docs/competition-rules-analysis.md** - Competition constraints and evaluation
3. **docs/sota-research.md** - State-of-the-art techniques
4. **docs/plans/2026-03-17-war-room-cheatsheet-strategy.md** - Strategic decisions

### External Sources (To Be Added)

- [ ] Competition official rules and specifications
- [ ] Equational Theories Project documentation
- [ ] Honda, Murakami, Zhang (2025) paper (when accessible)
- [ ] Mathematical logic and universal algebra references

---

*This specification serves as the blueprint for cheatsheet development. All implementation should trace back to these requirements.*
