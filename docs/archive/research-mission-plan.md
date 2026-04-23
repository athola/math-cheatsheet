# Autonomous Research Mission Plan
## SAIR Math Cheatsheet Competition - Egregore + Attune Integration

**Mission**: Conduct massive deep research on equational implication over magmas to create a competition-winning cheatsheet.

**Approach**: Use `/egregore:summon` to run `/attune:mission` consecutively, with each phase handled by specialized research agents using ultrathink methodology.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EGREGORE ORCHESTRATOR                       │
│  (Autonomous, self-recovering, runs indefinitely or --bounded)      │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  │ Invokes /attune:mission
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                         ATTUNE MISSION                              │
│  Phase-based execution: brainstorm → specify → plan → execute      │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
    [PHASE 1]              [PHASE 2]              [PHASE 3-4]
   Brainstorm             Specify              Plan + Execute
                          │                      │
                          │                      │
                      ┌───▼──────────────────────▼───┐
                      │     RESEARCH AGENTS           │
                      │  (Deep ultrathink research)   │
                      └───────────────────────────────┘
```

---

## Phase 0: Repository Setup

### Initial Structure
```bash
# Create project structure
mkdir -p docs research data experiments
mkdir -p .attune .egregore

# Initialize repository
git init
```

### Required Files

**1. `.egregore/manifest.json`** - Work items for the egregore
```json
{
  "version": "1.0",
  "mode": "bounded",
  "items": [
    {
      "id": "RESEARCH-001",
      "title": "Deep Research: Equational Theories Project",
      "description": "Conduct comprehensive research on the Equational Theories Project, understanding the 4694 laws, implication relationships, and mathematical structure of magmas.",
      "priority": "critical",
      "status": "pending",
      "phase": "brainstorm",
      "estimated_duration": "4h"
    },
    {
      "id": "RESEARCH-002",
      "title": "Analysis: Competition Rules and Evaluation",
      "description": "Analyze all competition rules, evaluation criteria, model constraints (10KB limit, no-tools setting), and success metrics.",
      "priority": "critical",
      "status": "pending",
      "phase": "brainstorm",
      "estimated_duration": "2h"
    },
    {
      "id": "RESEARCH-003",
      "title": "Research: State-of-the-Art in Mathematical Reasoning",
      "description": "Research current SOTA approaches for LLM mathematical reasoning, few-shot learning, and cheatsheet/prompt engineering techniques.",
      "priority": "high",
      "status": "pending",
      "phase": "brainstorm",
      "estimated_duration": "3h"
    },
    {
      "id": "SPEC-001",
      "title": "Specify: Cheatsheet Requirements",
      "description": "Create detailed specification for the cheatsheet: structure, content areas, size constraints, and validation criteria.",
      "priority": "critical",
      "status": "pending",
      "phase": "specify",
      "estimated_duration": "2h"
    },
    {
      "id": "PLAN-001",
      "title": "Plan: Research and Experimentation Strategy",
      "description": "Create implementation plan for conducting experiments, testing different cheatsheet approaches, and measuring effectiveness.",
      "priority": "critical",
      "status": "pending",
      "phase": "plan",
      "estimated_duration": "2h"
    },
    {
      "id": "EXEC-001",
      "title": "Execute: Build and Validate Cheatsheet v1",
      "description": "Build initial cheatsheet version, validate against training problems, iterate based on results.",
      "priority": "high",
      "status": "pending",
      "phase": "execute",
      "estimated_duration": "6h"
    }
  ]
}
```

**2. `.attune/mission-type.json`** - Mission configuration
```json
{
  "mission_type": "full",
  "phases": ["brainstorm", "specify", "plan", "execute"],
  "auto_continue": true,
  "research_mode": true
}
```

---

## Phase 1: Brainstorm (Research Discovery)

**Goal**: Comprehensive understanding of the competition domain, rules, and landscape.

**Skills to Invoke**:
- `Skill(attune:project-brainstorming)` - Main brainstorm framework
- `Skill(attune:war-room)` - For multi-perspective deliberation on strategy

**Research Questions**:
1. **Mathematical Foundation**:
   - What is a magma? (A set with a binary operation, no other axioms)
   - What are equational theories? (Equations that hold for all elements)
   - How does implication work? (E1 implies E2 if E2 holds in all models where E1 holds)
   - What is the structure of the 4694 laws in equations.txt?

2. **Competition Structure**:
   - Stage 1: true/false on implication questions
   - 10KB cheatsheet size limit
   - No-tools evaluation (no internet, no calculators)
   - 1200 training problems (1000 regular + 200 hard)
   - Evaluation model: lower-cost (Llama, Gemini Flash, OpenAI OSS)

3. **Prior Art**:
   - Honda, Murakami, Zhang (2025) on distilling few-shot learning
   - Equational Theories Project findings
   - Related work on mathematical reasoning prompts

**Output Artifact**: `docs/project-brief.md`

---

## Phase 2: Specify (Requirements Definition)

**Goal**: Define what the cheatsheet must contain and how success will be measured.

**Skills to Invoke**:
- `Skill(attune:project-specification)` - Main specification framework

**Specification Contents**:
1. **Cheatsheet Structure**:
   ```
   Section 1: Problem Understanding (1-2KB)
   - How to read equations
   - What implication means
   - Common pitfalls

   Section 2: Mathematical Framework (2-3KB)
   - Key magma properties
   - Useful theorems/laws
   - Implication patterns

   Section 3: Solution Strategies (3-4KB)
   - Step-by-step reasoning approach
   - Counterexample construction
   - Proof sketching
   - Verification methods

   Section 4: Reference (1-2KB)
   - Common equation forms
   - Quick reference tables
   ```

2. **Functional Requirements**:
   - Must fit within 10KB (~1500-2000 words compressed)
   - Must be human-readable
   - Must improve model performance on implication tasks
   - Must work in no-tools setting

3. **Non-Functional Requirements**:
   - Clear and concise language
   - Mathematical rigor where needed
   - Practical examples
   - No external dependencies

**Output Artifact**: `docs/specification.md`

---

## Phase 3: Plan (Research Strategy)

**Goal**: Create detailed plan for experimentation and cheatsheet development.

**Skills to Invoke**:
- `Skill(attune:project-planning)` - Main planning framework
- `Skill(parseltongue:python-testing)` - For testing infrastructure

**Plan Contents**:
1. **Data Acquisition**:
   - Download equations.txt (4694 laws)
   - Download training problems (1200 items)
   - Download implication graph if available

2. **Research Infrastructure**:
   ```
   research/
   ├── data/
   │   ├── equations.txt
   │   ├── train_problems.json
   │   └── implication_graph.json
   ├── notebooks/
   │   ├── 01_exploration.ipynb
   │   ├── 02_pattern_analysis.ipynb
   │   └── 03_cheatsheet_iteration.ipynb
   └── experiments/
       ├── baseline.py
       ├── evaluate.py
       └── iterate.py
   ```

3. **Experimentation Plan**:
   - Week 1: Data analysis, pattern discovery
   - Week 2: Baseline experiments (no cheatsheet)
   - Week 3: Cheatsheet v1, initial testing
   - Week 4: Iteration and refinement

4. **Validation Approach**:
   - Use open-source models for testing
   - Cross-validation on training set
   - Ablation studies (which sections help most?)
   - Error analysis on failed cases

**Output Artifact**: `docs/implementation-plan.md`

---

## Phase 4: Execute (Research & Build)

**Goal**: Execute the research plan and build the winning cheatsheet.

**Skills to Invoke**:
- `Skill(attune:project-execution)` - Main execution framework
- `Skill(parseltongue:python-pro)` - For Python research code
- `Skill(imbue:proof-of-work)` - For validation of each iteration

**Execution Steps**:

1. **Setup Data Pipeline**:
   ```python
   # Load and parse equations
   # Build implication lookup structure
   # Create problem-evaluation harness
   ```

2. **Exploratory Analysis**:
   - Analyze equation frequencies
   - Find common implication patterns
   - Identify "key" equations that imply many others
   - Discover equation families/clusters

3. **Cheatsheet Construction**:
   - Draft based on mathematical insights
   - Optimize for information density
   - Test with sample problems
   - Iterate based on performance

4. **Validation**:
   ```bash
   # Run evaluation on training set
   python experiments/evaluate.py --cheatsheet cheatsheet/v1.txt --split train

   # Cross-validation
   python experiments/evaluate.py --cheatsheet cheatsheet/v1.txt --split cv --folds 5

   # Error analysis
   python experiments/analyze.py --cheatsheet cheatsheet/v1.txt --errors
   ```

**Output Artifact**: `cheatsheet/final.txt`, `experiments/results/`

---

## Egregore Configuration

### Summon Command

```bash
# Start the autonomous research mission
/egregore:summon --bounded --window 7d
```

### Manifest Updates

As research progresses, the egregore can dynamically add new work items:
- New research questions discovered
- Additional experiments to run
- Iterations on the cheatsheet
- Bug fixes in evaluation code

### Watchdog Installation

```bash
# Install watchdog for self-recovery
/egregore:install-watchdog
```

This ensures the mission continues even if:
- Session crashes due to errors
- Rate limits are hit
- Context window fills up
- Network interruptions occur

---

## Ultrathink Integration

Each research agent should use "ultrathink" methodology:

1. **Deep First-Principles Analysis**:
   - Don't just surface-level research
   - Question fundamental assumptions
   - Build from mathematical foundations

2. **Multiple Perspectives**:
   - Use `Skill(attune:war-room)` for deliberation
   - Consider different approaches
   - Evaluate trade-offs systematically

3. **Iterative Refinement**:
   - Generate hypotheses
   - Test against data
   - Refine based on evidence
   - Document learning

4. **Knowledge Synthesis**:
   - Connect insights across domains
   - Build coherent mental models
   - Document for future reference

---

## Success Criteria

### Stage 1 Goals
- [ ] Cheatsheet under 10KB
- [ ] Improved accuracy over baseline (measured on training set)
- [ ] Validated on multiple model types
- [ ] Documented methodology

### Stretch Goals
- [ ] Top 100 leaderboard position
- [ ] Novel insights on equational implications
- [ ] Publishable findings
- [ ] Preparation for Stage 2

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Setup | 0.5 day | None |
| Brainstorm | 2-3 days | Setup |
| Specify | 1-2 days | Brainstorm |
| Plan | 1-2 days | Specify |
| Execute | 7-14 days | Plan |

**Total**: 12-22 days of autonomous research

---

## Next Steps

1. **Initialize Repository**:
   ```bash
   cd /home/alext/math-cheatsheet
   mkdir -p docs research data experiments cheatsheet .attune .egregore
   ```

2. **Create Manifest**: Copy the manifest JSON above to `.egregore/manifest.json`

3. **Summon Egregore**:
   ```bash
   /egregore:summon --bounded --window 14d
   ```

4. **Monitor Progress**:
   ```bash
   /loop 10m /egregore:status
   ```

5. **Review Artifacts**: Check `docs/` for generated brief, spec, and plan

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context exhaustion | High | Egregore spawns continuation agents |
| Rate limiting | Medium | Watchdog auto-recovery |
| Dead-end research | Medium | War-room for perspective diversity |
| 10KB too restrictive | Medium | Iterative compression experiments |
| Evaluation model unknown | Low | Test on multiple model types |

---

*This plan will evolve as the egregore conducts research and discovers new insights.*
