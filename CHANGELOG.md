# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- Corrected formal-verification claims to match what is actually proven.
  The cheatsheet is validated empirically, not formally verified. Lean
  proves the implication preorder laws, term/well-formedness lemmas,
  Bool/XOR/AND witnesses, and one representative countermodel; TLA+ checks
  only `Size2Check.tla`. README, `docs/formal-verification-summary.md`, and
  the `lean_bridge.py` docstrings were updated accordingly.

### Added
- `tla/MagmaSpecifications/Size2Check.tla` (+`.cfg`): the one executable,
  TLC-verified spec. Exhaustively enumerates the 16 size-2 magmas and
  confirms associative/commutative/idempotent counts plus size-2 witnesses
  for `assoc ⇏ comm` and `idemp ⇏ comm`.
- `idemp_not_implies_comm` in `lean/EquationalTheories/Invariants.lean`: a
  fully-proven non-implication via a `Fin 2` left-projection countermodel
  (no `sorry`/`axiom`/`admit`).

### Fixed
- Marked the non-parsing TLA+ modules (Magma fixes aside) as illustrative
  pseudo-specs with STATUS banners; removed the unsound
  `count = 0 => "always_true"` label in `CounterexampleExplorer.tla`.
- Fixed `Magma.tla` to parse (undefined `Infinity`; vacuous
  `EquationHolds == TRUE` placeholder removed).
- Tightened `isCommutativityPattern` so it no longer matches the tautology
  `x*x = x*x`.

## [0.2.1] - 2026-04-23

### Added
- Phase 6 rewrite analysis: orient H as a rewrite rule and reduce T (#28)
- Phase 7 structural heuristics: side-swap identity, depth divergence,
  operator-count bounds (#35)
- Python → Lean 4 counterexample bridge: emit `example` scaffolds carrying
  a finite magma's Cayley table for a FALSE implication (`src/lean_bridge.py`,
  #32). Note: the emitted body is a non-verifying `by trivial` placeholder,
  not a proof (backlog O1).
- Lean 4 proof coverage dashboard: scan `.lean` declarations and report
  `sorry`/`admit` placeholder rate (`src/lean_coverage.py`, #25)
- Canonical `Term` AST in `src/term.py` — single source of truth for the
  parser that previously lived in `equation_analyzer.py` and
  `etp_equations.py` (#27)
- Phase-ordering invariant tests and coverage-fill tests for `term.py`

### Changed
- `equation_analyzer.py` and `etp_equations.py` now re-export
  `Term`/`NodeType`/`var`/`op` from `src/term.py` rather than defining
  their own (#27)

### Performance
- Phase 4b caches size-2 satisfaction per equation (#34), avoiding
  repeated enumeration of the same magma set across equation pairs

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
