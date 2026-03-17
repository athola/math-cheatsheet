# SAIR Math Cheatsheet Competition - Autonomous Research Mission

> **Mission**: Use autonomous AI agents (egregore + attune) to conduct deep research and build a winning cheatsheet for the SAIR Foundation mathematical reasoning competition.

## Quick Start

```bash
# 1. Initialize the repository
git init
git add .
git commit -m "Initial commit: research mission setup"

# 2. Summon the egregore (autonomous research orchestrator)
/egregore:summon --bounded --window 14d

# 3. Monitor progress (optional, runs automatically)
/loop 10m /egregore:status

# 4. Stop the egregore when complete
/egregore:dismiss
```

## What This Does

The egregore will autonomously:

1. **Research**: Deep dive into equational theories, magmas, and mathematical implication
2. **Specify**: Define cheatsheet requirements based on competition rules
3. **Plan**: Design experimentation strategy and validation framework
4. **Execute**: Build, test, and iterate on the cheatsheet

Each phase uses specialized skills and "ultrathink" methodology for comprehensive analysis.

## Architecture

```
/egregore:summon
  └─> /attune:mission (runs through phases)
       ├─> Brainstorm: Comprehensive domain research
       ├─> Specify: Requirements and constraints
       ├─> Plan: Experimentation strategy
       └─> Execute: Build and validate cheatsheet
```

## Key Files

- `docs/research-mission-plan.md` - Detailed mission architecture
- `.egregore/manifest.json` - Work items for the egregore
- `docs/project-brief.md` - Generated after brainstorm phase
- `docs/specification.md` - Generated after specify phase
- `docs/implementation-plan.md` - Generated after plan phase
- `cheatsheet/final.txt` - Final output after execution

## Competition Context

**Task**: Determine if Equation 1 implies Equation 2 for magmas (algebraic structures with a binary operation).

**Constraints**:
- Cheatsheet size: 10KB maximum
- Evaluation: No-tools setting (no internet, calculators)
- Training: 1200 problems (1000 regular + 200 hard)
- Stage 1 deadline: April 20, 2026

## Project Structure

```
math-cheatsheet/
├── .attune/              # Attune mission state
├── .egregore/            # Egregore manifest and state
├── docs/                 # Generated documentation
├── research/
│   ├── data/            # Competition data
│   ├── notebooks/       # Jupyter research notebooks
│   └── experiments/     # Experiment code
├── experiments/          # Stand experiment scripts
├── cheatsheet/          # Cheatsheet versions
└── README.md            # This file
```

## Monitoring Progress

While the egregore runs, you can check status at any time:

```bash
/egregore:status
```

This shows:
- Current work item being processed
- Completed items
- Failed items (if any)
- Overall progress

## Self-Recovery

The egregore includes automatic recovery for:
- Session crashes
- Rate limit errors
- Context exhaustion
- Network interruptions

For enhanced recovery, install the watchdog:

```bash
/egregore:install-watchdog
```

## Documentation

See `docs/research-mission-plan.md` for:
- Detailed phase descriptions
- Skills invoked at each stage
- Success criteria
- Risk mitigations
- Timeline estimates

## Competition Links

- [SAIR Foundation](https://sair.foundation/)
- [Zulip Community](https://zulip.sair.foundation/)
- [Equational Theories Project](https://www.equational-theories.org/)

---

*This is an autonomous research mission. Once summoned, the egregore will work independently through all phases. Check progress periodically with `/egregore:status`.*
