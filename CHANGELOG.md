# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-04-21

### Added
- Phase 5 TLA+ bridge tests and expanded equation_analyzer coverage (580+ tests, 100% coverage)
- Feature-review backlog items (#22, #23, #24, #30, #31, #33): structural classification improvements
- Cheatsheet size increased to 10,230 / 10,240 bytes

### Changed
- Tier-3 code refinement across 6 quality dimensions (15 findings resolved)
- Tier-3 codebase cleanup: dead code removal, archive pruning, lazy-refactor fixes
- Refactored decision procedure based on PR #42 and #36 review findings

### Fixed
- Post-merge bugs from decision procedure PR (#44, #45, #46)
- CI: download implications.csv from ETP graph.json
- `Literal` type for `classify_structural` return annotation

## [0.1.1] - 2026-04-01

### Added
- Decision procedure implementation: 9 phases (P0–P6 + structural), 98.01% accuracy
- Issues #11–#21: decision procedure features and fixes
- LLM evaluator and Claude Code commands

### Changed
- README updated with accuracy metrics and competition context
- Rust extension (magma_core) built via maturin for CI compatibility

## [0.1.0] - 2026-03-01

### Added
- Initial MVP: equational theories cheatsheet with formal verification
- Python test suite, evaluation harness, competition cheatsheet
- Lean 4 proofs, TLA+ specs, Rust PyO3 extension (magma_core)
