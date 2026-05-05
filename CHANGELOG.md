# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- SHA-256 checksum verification test coverage for ImplicationOracle:
  matching/uppercase digest, mismatched-with-remediation, sidecar
  auto-detection, kwarg-overrides-sidecar, and no-digest paths (#48)
- Magma validation error-path tests: zero/negative size, wrong row count,
  short/long row, negative/out-of-range cells, non-contiguous carrier,
  missing operation entries (#49)
- caplog-backed assertions for debug logging in `DecisionProcedure.predict`
  and warning emission for `EvalCache` version-mismatch, corrupt-file,
  and missing-entries paths (#50)
- `competition_sim.main()` integration test verifying JSON schema and
  seeded reproducibility, plus `check_accuracy_gate.run_harness`
  subprocess and `SystemExit`-on-nonzero coverage (#51)

### Changed
- `evaluate_with_llm` raises `OSError`/`EnvironmentError` instead of
  calling `sys.exit` when the SDK or `ANTHROPIC_API_KEY` is missing;
  the CLI `main()` translates the exception to a process exit so
  the script behaviour is unchanged (#51)
- `ImplicationOracle.equivalence_classes` returns a `MappingProxyType`
  view over `frozenset` values; the cached row-profile mapping can no
  longer be corrupted by callers via `.discard`/`.add` (#52/M4)
- `parse_verdict` emits `logger.warning` when a `VERDICT:` line is
  present but unparseable, distinguishing LLM-compliance failures from
  the legitimate "no verdict line at all" case (#52/M5)

## [0.2.1] - 2026-04-23

### Added
- Phase 6 rewrite analysis: orient H as a rewrite rule and reduce T (#28)
- Phase 7 structural heuristics: side-swap identity, depth divergence,
  operator-count bounds (#35)
- Python → Lean 4 counterexample bridge: emit `example` blocks witnessing
  FALSE implications via finite magmas (`src/lean_bridge.py`, #32)
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
