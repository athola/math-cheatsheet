# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-03-26

### Fixed

- Rename `data_models.Equation` to `EquationEntry`; remove `CounterexampleMagma`
  in favor of `data_models.Magma` with `(name, Magma)` tuples (#2)
- Add `frozen=True` to dataclasses (`EquationEntry`, `Problem`,
  `AlgebraicEquation`, `Magma`, `Counterexample`, `AnalysisResult`);
  add `Difficulty` enum replacing `Problem.difficulty` string field (#8)
- Remove hardcoded test count from Makefile `test-harness` target (#9)
- Fix Lean `computeStats` Nat division precision loss by casting to Float (#9)
- Implement `evaluate_equation()` and `search_counterexample()` in
  `tla_bridge.py`, reusing `equation_analyzer`'s parser (#10)
- Add `sys.path` fallback to demo scripts for standalone execution (#7)

### Added

- Test coverage for `tla_bridge`, `explore_magmas`, and `counterexample_db`
  (75+ new tests) (#3)
- Shared magma fixtures in `tests/conftest.py` to deduplicate test setup (#4)
- Lean non-implication witnesses with explicit countermodels on Bool (#6)

### Removed

- `research/data/original/*.json` from tracking; data is now generated
  via `make download-etp` or `make generate-data` (#5)

## [0.1.0] - 2026-03-26

### Added

- Initial MVP: 98.01% accuracy on 22M implication matrix
- v4 decision procedure with collapse detection and phase-based evaluation
- Lean 4 formal proofs for implication and non-implication witnesses
- Rust `magma_core` with proptest invariant suite
- TLA+ bridge for counterexample search
- ETP dataset integration (4,694 equations)
- CI pipeline with GitHub Actions
