# Math Cheatsheet — Equational Theories

A formally verified 10KB reference for determining equational implication
in magmas. Built for the
[SAIR Mathematics Distillation Challenge][sair-challenge],
using Lean 4, TLA+, Rust, and Python.

**98.01% accuracy** on the full 22M implication matrix
(4,694 equations, 22,028,942 pairs) | 10,230 bytes of 10,240 limit

## Competition Context

The [SAIR Foundation][sair] (Tao & Davis, 2026) asks: given two
equational laws over magmas, does Equation 1 imply Equation 2?
Contestants produce a compact cheatsheet that a weak LLM reads at
inference time — no internet, no calculator. Top 1,000 entries
advance to Stage 2, which requires formal proofs or valid
counterexamples.

| Constraint       | Value                           |
|------------------|---------------------------------|
| Cheatsheet limit | 10,240 bytes                    |
| Training set     | 1,200 problems (1,000 + 200 hard) |
| Stage 1 deadline | April 20, 2026                  |
| Dataset origin   | [Equational Theories Project][etp] (22M+ implications) |

## Status

| Metric                  | Value         |
|-------------------------|---------------|
| Decision procedure accuracy | 98.01% (22M pairs) |
| Competition problem accuracy | 94.25% (1,200 problems) |
| Cheatsheet size         | 10,230 / 10,240 bytes |
| Competition submission  | 9,851 bytes (`competition-v1.txt`) |
| Equations covered       | 4,694         |
| Decision procedure phases | 9 (P0-P6 + structural) |
| Test suite              | 580+ tests (100% equation_analyzer.py) |

## Quick Start

```bash
make setup            # create venv, install Python deps
make test             # run Python test suite (580+ tests)
make test-rust        # run Rust proptest suite
make lean-check       # check Lean 4 proofs
make harness          # 5-angle cheatsheet validation
make tla-check        # run TLC model checker on all TLA+ modules
make check            # all quality gates (lint + typecheck + test + rust)
```

Run `make help` for the full target list.

## Architecture

Four languages cover complementary verification angles:

| Layer          | Language    | Role                                              |
|----------------|-------------|---------------------------------------------------|
| Core pipeline  | Python 3.12 | Equation parsing, analysis, evaluation, harness   |
| Fast search    | Rust (PyO3) | Exhaustive magma enumeration, counterexample search |
| Formal proofs  | Lean 4      | Machine-checked implication proofs via mathlib     |
| Model checking | TLA+        | State-space exploration of magma specifications    |

## Verification Pipeline

The cheatsheet harness validates from five independent angles
(`make harness` or individual targets):

| Angle          | Target                  | What it checks                          |
|----------------|-------------------------|-----------------------------------------|
| Compliance     | `make harness-compliance`  | Size (<=10,240 B), encoding, format  |
| Structure      | `make harness-structure`   | Content sections and decision procedure |
| Accuracy       | `make harness-accuracy`    | Decision procedure vs. known problems   |
| Regression     | `make harness-regression`  | Cross-version quality comparison        |
| Competition    | `make harness-competition` | Simulated evaluation format             |

Current cheatsheet: `cheatsheet/final.txt` (10,230 bytes of 10,240 limit).
Competition submission: `cheatsheet/competition.txt` → `competition-v1.txt` (9,851 bytes).

## Decision Procedure

The multi-phase implication predictor runs 9 phases in sequence:

| Phase | Name | Decision |
|-------|------|----------|
| P0 | Self-implication | H = T → TRUE |
| P1 | Tautology target | T is x=x → TRUE |
| P2 | Collapse hypothesis | H forces \|M\|=1 → TRUE |
| P3 | Tautology hypothesis | H is x=x, T is not → FALSE |
| P4 | Variable analysis | New vars in T → FALSE |
| P5 | Substitution | T is H with merged vars → TRUE |
| P5a | Equivalence class | Same implication profile → TRUE |
| P5b/c | Structural analysis | Counterexample magmas / determined ops → TRUE/FALSE |
| P6 | Default | → FALSE |

Evaluate against the full matrix: `python src/decision_procedure.py`
Analyze errors: `python src/error_analyzer.py`
Batch competition scoring: `python src/competition_evaluator.py`

## Project Structure

```
math-cheatsheet/
├── src/                  # Python core
│   ├── decision_procedure.py  # 9-phase implication predictor
│   ├── equation_analyzer.py   # Structural analysis + counterexamples
│   ├── etp_equations.py       # ETP dataset parser (4,694 equations)
│   ├── implication_oracle.py  # 22M ground-truth matrix
│   ├── competition_evaluator.py # Batch scoring + category breakdown
│   ├── error_analyzer.py      # Failure pattern analysis
│   ├── counterexample_generator.py # Exhaustive magma search
│   ├── llm_evaluator.py       # Claude API evaluation (with caching)
│   └── cheatsheet_harness.py  # 5-angle validation
├── rust/                 # Rust PyO3 extension (magma_core)
├── lean/                 # Lean 4 formal proofs
├── tla/                  # TLA+ specs and Python bridge
├── tests/                # pytest suite (580+ tests)
├── cheatsheet/           # Cheatsheet versions (v1 → final, competition)
├── scripts/              # CLI utilities, TLA+ automation, Lean scaffolding
├── docs/                 # Specification, plans, analysis, bibliography
├── research/             # Domain research notes + ETP dataset
└── Makefile              # Build, test, and validate targets
```

## Development

### Testing

```bash
make test                 # full Python suite
make test-property        # property-based tests (Hypothesis)
make test-cross-language  # Python/Rust consistency checks
make test-rust            # Rust proptest invariants
make test-invariants      # all invariant tests combined
```

### Quality gates

```bash
make lint                 # ruff linting
make typecheck            # mypy type checking
make format               # auto-format with ruff
make check                # lint + typecheck + test + rust
```

### Analysis Tools

```bash
python src/error_analyzer.py          # break down 22M matrix errors by pattern
python src/competition_evaluator.py   # batch scoring with category breakdown
python src/counterexample_generator.py # exhaustive magma counterexample search
make tla-check                        # run TLC model checker on TLA+ specs
make etp-status                       # show ETP dataset summary
```

### Demos

```bash
make demo                 # run all demos
make demo-magmas          # generate and inspect size-2 magmas
make demo-properties      # magma property census (size 2-3)
make demo-counterexamples # find counterexamples to non-implications
make demo-cheatsheet      # show cheatsheet stats and byte count
```

## Documentation

- [Specification](docs/specification.md) — cheatsheet requirements
  and acceptance criteria
- [Implementation plan](docs/implementation-plan.md) — build strategy
  and phases
- [Competition rules analysis](docs/competition-rules-analysis.md) —
  constraint deep-dive
- [Formal verification summary](docs/formal-verification-summary.md) —
  Lean/TLA+ results
- [State-of-the-art research](docs/sota-research.md) — prior work
  and techniques survey
- [Research index](research/INDEX.md) — domain research notes

## Links

- [SAIR Foundation][sair]
- [SAIR Competition Portal][sair-challenge]
- [Equational Theories Project][etp]
  (Tao et al. — the upstream Lean 4 dataset)
- [Zulip Community][zulip]

[sair]: https://sair.foundation/
[sair-challenge]: https://competition.sair.foundation/competitions/mathematics-distillation-challenge-equational-theories-stage1/overview
[etp]: https://github.com/teorth/equational_theories
[zulip]: https://zulip.sair.foundation/
