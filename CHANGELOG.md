# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.2] - 2026-05-06

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
- `lean_bridge.counterexample_to_lean_theorem`: emits real Lean 4
  theorems `¬ (H_prop → T_prop) := by decide` over the synthesised
  `op_<name>` on `Fin n`. The negation-of-implication form makes the
  proposition decidable on the finite carrier; ten sample counter-
  examples are verified end-to-end against `lean` in CI via the
  `cross_language` pytest marker (#64)
- Phase 6 rewrite observability: `_rewrite_to_normal_form` now returns
  `(Term, RewriteStatus)` where status is `'normal_form'`, `'cycle'`,
  or `'budget'`. Budget exhaustion is logged at DEBUG so practitioners
  can identify implications discoverable by raising the step limit (#60)
- `_match_pattern` snapshot/restore on failure so partial bindings
  cannot leak into sibling sub-matches; protects any future
  AC-matching extension or pattern-cache reuse from silently-wrong
  matches (#60)
- ETPEquations loader aggregates every parse failure into a single
  `ExceptionGroup` instead of aborting on the first error; users with
  five typos see five errors in one shot rather than re-running five
  times (#61)
- `lean_coverage.scan_lean_declarations` log+skips on
  `UnicodeDecodeError`/`PermissionError`/`OSError` so a single bad
  file no longer crashes the whole dashboard (#61)
- Hypothesis-driven soundness test: every TRUE verdict from
  `analyze_implication` is exhaustively verified against all
  size-≤3 magmas where H holds — a regression that introduces a
  false-TRUE structural shortcut surfaces as a Hypothesis
  counterexample rather than as an opaque accuracy delta (#59)
- Term parser-error coverage: unbalanced parens, bare leading
  operator, trailing operator, and manual-construction OP/VAR
  invariant violations (#59)
- Phase 6 × Phase 7c interaction test pinning that the rewrite TRUE
  proof beats the op-count FALSE heuristic when both apply (#59)
- Mock-patched `Equation.holds_in` call counter for
  `_size_2_satisfactions` cache so a cache bypass or hashability
  regression fails an assertion rather than just slowing the corpus (#59)

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
- `Magma`, `AnalysisResult`, and `CounterexampleMagma` are now
  `frozen=True`; Cayley tables and properties are stored as nested
  tuples. `m.operation[0][0] = 99` (the silent-corruption case) raises
  `TypeError` instead of producing an invalid magma. `__post_init__`
  accepts list-of-list inputs for back-compat (#55, #58)
- `Term.__post_init__` validates the OP/VAR invariant at construction.
  `Term(NodeType.OP)` (no children) and `Term(NodeType.VAR)` (empty
  name) now raise `ValueError` immediately rather than passing
  construction and surfacing only inside `_lr()` at every traversal (#58)
- `_size_2_satisfactions` switched from `functools.cache` to
  `functools.lru_cache(maxsize=8192)` to bound memory in long-running
  consumers (notebooks, batch jobs, server processes); 8192 is plenty
  for the 4694-equation corpus (#58)
- `PredictionResult.phase` typed via `Literal[...]` and validated
  against `_VALID_PHASE_PREFIXES` in `__post_init__`. A typo like
  `"P6-defualt"` fails fast at construction time rather than slipping
  through string-literal comparisons (#53)
- `ImplicationOracle._VALID_VALUES` annotated `Final` and derived from
  a single `_ENCODING` source-of-truth shared with `decode_truth` (#53)
- `_equiv_data` returns `_EquivData(eq_to_class, classes_by_id)`
  NamedTuple instead of a positional `tuple[dict, dict]` whose `[0]`
  vs `[1]` indexing was bug-prone (#53)
- `Magma.from_dict_operation` accepts `carrier=None` and infers size
  from the dict keys; the parameter was previously redundant because
  `range(size)` was the only legal value (#55)

### Fixed
- `tokenize_equation` surfaces unrecognised characters via `UserWarning`
  instead of silently dropping them; new `strict=True` parameter raises
  `ValueError`. Previous behaviour produced `["x","*","y"]` for both
  `"x * y"` and `"x1 * y"` (#54)
- `wilson_ci` validates `0 <= successes <= total` and rejects `total=0`
  with non-zero successes; previously clamp-masked into a meaningless
  interval, hiding caller bugs like accuracy passed as a float instead
  of a count (#54)
- Phase 6 `_phase6_rewrite` continues past unsound orientations (RHS
  introduces fresh variables) — the existing `_rule_is_sound` guard is
  now exercised by an integration test that constructs `H = x*x = x*y`
  where one orientation is unsound (#60)
- Phase 8 reason changed from `"Inconclusive - default FALSE"` (which
  contradicted the `UNKNOWN` verdict) to `"Inconclusive — no rule
  fired"`. The default-FALSE policy belongs to `DecisionProcedure`,
  not the analyzer (#62)

### Refactored
- `_detect_determined_operation` collapses four absorption branches via
  a canonical `(var_side, op_side)` ordering, which drops ~30 lines of
  duplicated AST-shape checks down to one shared shape match.
  `is_collapse_structural` uses the same canonicalisation for its two
  var-vs-op mirror branches (#63)
- `_rewrite_once` uses `term._lr()` for OP-children access instead of
  manual `term.left`/`term.right` + `is not None` guards; consistent
  with the rest of the module (#63)
- `compute_coverage` uses `collections.Counter` directly for the kind
  tally; `lean_bridge` joins arms via a generator expression instead
  of building a temporary list; `_iter_vars` uses a structural `match`
  statement (project targets py3.10+) (#63)

### Test
- Tightened phase assertions in `test_decision_procedure.py`: three
  tests using OR-over-multiple-phase patterns (e.g. `"P5c" in
  result.phase or "P6" in result.phase`) replaced with exact phase
  string assertions. A revert of the P5bc-structural dispatch would
  have silently passed under the previous loose form (#56)
- Renamed `test_side_swap_of_associativity` to acknowledge that
  Phase 6 closes the associativity flip via rewriting before
  Phase 7a's side-swap shortcut fires; Phase 7a coverage is now
  anchored by `test_side_swap_of_commutativity_fires_phase7a`
  (commutativity's bidirectional rewrite cycles, so Phase 7a
  genuinely is the proof path there) (#59)
- Coverage gap fills across branch-touched files: 697 tests pass,
  total coverage 88%; every executable line in modified files is
  covered except CLI `__main__` blocks and one defensive branch
  (`equation_analyzer.py:348` Phase 7c FALSE) that
  `TestPhase7cFalseDeadByDesign` proves unreachable
  (`_h_vars_unique` strictness forces `Phase 5` to fire first)

### Documentation
- `_match_pattern` docstring rewritten to call out non-linearity in the
  pattern as the property that enables `x*x → x` rules; the previous
  wording inverted "linear-match" terminology (#62)
- `test_phase6_rewrite` docstring is now unambiguous about which
  orientation closes the proof (RHS→LHS yields `x*x → x`) (#62)
- `_size_2_satisfactions` docstring notes the cache is per-process
  only. Cold-start runs pay the full per-equation cost (#62)

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
