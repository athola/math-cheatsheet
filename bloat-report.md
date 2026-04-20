# Bloat Detection Report

**Scan Level**: 3 (Tier 1 heuristics + git + Vulture static analysis + Radon complexity + cross-file reference tracing)
**Date**: 2026-04-20
**Repository**: /Users/alex.thola/math-cheatsheet (branch: mvp-0.1.0)
**Files Scanned**: ~170 tracked files across src/, tests/, scripts/, docs/, research/, tla/, lean/, experiments/, cheatsheet/

---

## SUMMARY

| Risk Level | Findings | Estimated Token Savings |
|------------|----------|------------------------|
| LOW        | 11       | ~27,500                |
| MEDIUM     | 8        | ~15,200                |
| HIGH       | 5        | ~7,800                 |
| **TOTAL**  | **24**   | **~50,500**            |

Token estimates use ~3.5 chars/token for Python and ~4 chars/token for Markdown/text (rough estimates; actual savings depend on LLM tokenizer).

---

## LOW RISK FINDINGS

### [L1] Duplicate cheatsheet file: cheatsheet/v3.txt
**File**: `/Users/alex.thola/math-cheatsheet/cheatsheet/v3.txt`
**Action**: DELETE
**Confidence**: 99%
**Risk**: LOW
**Token Impact**: ~2,500

**Evidence** [EN]:
- `md5sum` of v3.txt and final.txt both return `6d4437246aa90155b3d2cba0c577dc12` — byte-for-byte identical.
- `cheatsheet/final.txt` is the canonical output; v3.txt is a superseded intermediate that was never renamed before final.txt was produced.
- No callers reference `cheatsheet/v3.txt` in any `.py`, `.sh`, `.yml`, or Makefile (grep found zero hits).
- `cheatsheet/v1.txt` and `cheatsheet/v2.txt` are retained as historical baselines (referenced in `docs/formal-verification-summary.md` lines 203-204) — v3 is the only true duplicate.

---

### [L2] Nested Lean project scaffolding (lean/EquationalTheories/ sub-project)
**Files**:
- `/Users/alex.thola/math-cheatsheet/lean/EquationalTheories/lake-manifest.json`
- `/Users/alex.thola/math-cheatsheet/lean/EquationalTheories/lakefile.toml`
- `/Users/alex.thola/math-cheatsheet/lean/EquationalTheories/lean-toolchain`
- `/Users/alex.thola/math-cheatsheet/lean/EquationalTheories/Main.lean`
- `/Users/alex.thola/math-cheatsheet/lean/EquationalTheories/README.md`
- `/Users/alex.thola/math-cheatsheet/lean/EquationalTheories/.github/workflows/lean_action_ci.yml`
**Action**: DELETE (the above files only; keep the .lean source files in the directory)
**Confidence**: 88%
**Risk**: LOW
**Token Impact**: ~250 (small files, mainly CI/manifest overhead)

**Evidence** [EN]:
- `make lean-check` runs `cd lean && lake build` — it targets the parent `lean/` Lake project, not the nested one.
- The parent `lean/lakefile.toml` has the mathlib dependency and the up-to-date version (`0.1.1`); the nested `lean/EquationalTheories/lakefile.toml` shows version `0.1.0` with an empty packages list — older snapshot.
- `lean/EquationalTheories/lake-manifest.json` has `"packages": []` (no mathlib), while `lean/lake-manifest.json` has 9 packages including mathlib v4.28.0.
- The nested `Main.lean` diverges slightly from the parent `lean/Main.lean` (missing `import EquationalTheories.Invariants`).
- Both `lean/.github/` and `lean/EquationalTheories/.github/` contain identical `lean_action_ci.yml` — 200 bytes duplicated.
- The `.lean` source files (`Basic.lean`, `Core.lean`, `Implication.lean`, `Invariants.lean`, `EquationalTheories.lean`) are the actual content and must be kept.

---

### [L3] Stale baseline evaluation results (experiments/results/baseline/)
**Files**:
- `/Users/alex.thola/math-cheatsheet/experiments/results/baseline/evaluation_results.json`
- `/Users/alex.thola/math-cheatsheet/experiments/results/baseline/evaluation_summary.json`
**Action**: ARCHIVE
**Confidence**: 85%
**Risk**: LOW
**Token Impact**: ~800

**Evidence** [EN]:
- `evaluation_summary.json` shows `"model": "simulated"`, `"accuracy": 0.8`, `"timestamp": "2026-03-17T21:33:57"` — 34 days old relative to today, from a simulated run at MVP 0.1.0 inception.
- Current accuracy target is 98%+ (CI accuracy gate: `scripts/check_accuracy_gate.py --threshold 98.0`); this 80% baseline data predates the real decision procedure.
- No code in `src/` or `scripts/` reads these JSON files at runtime. No CI step reads from `experiments/results/`.
- Value is purely historical record-keeping; safe to archive.

---

### [L4] Stale experiment validation markdown reports
**Files**:
- `/Users/alex.thola/math-cheatsheet/experiments/validation/validation_summary.md`
- `/Users/alex.thola/math-cheatsheet/experiments/validation/final_validation_report.md`
**Action**: ARCHIVE
**Confidence**: 82%
**Risk**: LOW
**Token Impact**: ~2,200

**Evidence** [EN]:
- `final_validation_report.md` references `cheatsheet/final.txt` as "9570 bytes" but actual file is 9911 bytes — report is outdated.
- Both documents are handwritten narratives from 2026-03-18 (MVP 0.1.0 submission day) describing v1/v2 cheatsheet iterations that have since been superseded.
- No runtime code reads these files; `make` has no target that references them.
- The executable validation scripts (`validate_cheatsheet.py`, `validate_v2.py`, `formal_validation.py`) are active Makefile targets and should be kept.

---

### [L5] Dead variable `sample_size` in DecisionProcedure.evaluate()
**File**: `/Users/alex.thola/math-cheatsheet/src/decision_procedure.py` line 160
**Action**: REFACTOR
**Confidence**: 100% (Vulture high-confidence)
**Risk**: LOW
**Token Impact**: ~30

**Evidence** [EN]:
- Vulture 100% confidence: `decision_procedure.py:160: unused variable 'sample_size'`.
- The parameter `sample_size: int | None = None` is accepted but the function body calls `self.oracle.accuracy_of(self.predict_bool)` unconditionally, ignoring `sample_size`. The docstring says "If sample_size is set, evaluate on a random sample" but the sampling logic was never implemented.
- No callers pass `sample_size` (grep confirms zero call sites with the kwarg).

---

### [L6] Stale planning document: docs/implementation-plan.md
**File**: `/Users/alex.thola/math-cheatsheet/docs/implementation-plan.md`
**Action**: ARCHIVE
**Confidence**: 80%
**Risk**: LOW
**Token Impact**: ~440

**Evidence** [EN]:
- Document is a task checklist dated 2026-03-19 describing Tasks 1.1 through 4.x ("Phase 1: Data Foundation", "Phase 2: Decision Procedure", etc.) — all tasks are now complete.
- References `experiments/evaluate.py` and `experiments/analyze.py` (lines 288, 291, 294 of `docs/research-mission-plan.md` mirrors the same scripts) — neither file exists in the repository.
- Not referenced by any code, CI, or Makefile target.

---

### [L7] Stale planning document: docs/research-mission-plan.md
**File**: `/Users/alex.thola/math-cheatsheet/docs/research-mission-plan.md`
**Action**: ARCHIVE
**Confidence**: 78%
**Risk**: LOW
**Token Impact**: ~3,360

**Evidence** [EN]:
- Header: "Autonomous Research Mission Plan — SAIR Math Cheatsheet Competition — Egregore + Attune Integration". This is a pre-execution research briefing, not living documentation.
- References `experiments/evaluate.py`, `experiments/analyze.py` (lines 288-294) — scripts that do not exist.
- References `cheatsheet/v1.txt` evaluation as a future goal that has been completed.
- Not referenced by any code, CI, or Makefile target.

---

### [L8] Stale early-phase doc: docs/formal-verification-considerations.md
**File**: `/Users/alex.thola/math-cheatsheet/docs/formal-verification-considerations.md`
**Action**: ARCHIVE
**Confidence**: 78%
**Risk**: LOW
**Token Impact**: ~440

**Evidence** [EN]:
- Header: `**Status**: Future Enhancement` — written as a speculative "pros/cons" document before Lean and TLA+ were actually integrated.
- The work described ("encode equations in Lean", "create library of verified proofs") was subsequently carried out and documented in `docs/formal-verification-summary.md` (278 lines, fully supersedes this).
- Not referenced from any code or Makefile.

---

### [L9] Orphaned .attune mission config
**File**: `/Users/alex.thola/math-cheatsheet/.attune/mission-type.json`
**Action**: ARCHIVE
**Confidence**: 72%
**Risk**: LOW
**Token Impact**: ~65

**Evidence** [EN]:
- Config for the Attune autonomous agent system (`"mission_type": "full"`, `"phases": ["brainstorm", "specify", "plan", "execute"]`). This was the research orchestration configuration used at project inception.
- No code in `src/`, `scripts/`, or CI reads or references `.attune/`.
- The mission is complete (branch `mvp-0.1.0` is merged to main equivalent).

---

### [L10] Unused Jupyter notebook
**File**: `/Users/alex.thola/math-cheatsheet/research/notebooks/01_exploration.ipynb`
**Action**: ARCHIVE
**Confidence**: 72%
**Risk**: LOW
**Token Impact**: ~1,600

**Evidence** [EN]:
- File exists at 6,295 bytes. The `notebook` extras in `pyproject.toml` (`jupyter`, `jupyterlab`, `matplotlib`, `seaborn`) are present but not installed by default (`pip install -e ".[dev]"` does not include `notebook`).
- No Makefile target runs or references this notebook.
- The research index (`research/INDEX.md` line 230) lists it as part of planned structure but there is no indication it contains live analysis results used by any other artifact.

---

### [L11] Duplicate lean CI workflow files
**File**: `/Users/alex.thola/math-cheatsheet/lean/.github/workflows/lean_action_ci.yml` (outer)
**Action**: DELETE
**Confidence**: 85%
**Risk**: LOW
**Token Impact**: ~50

**Evidence** [EN]:
- `lean/.github/workflows/lean_action_ci.yml` and `lean/EquationalTheories/.github/workflows/lean_action_ci.yml` are byte-for-byte identical (200 bytes each; both verified with file read).
- The outer `lean/.github/` workflow fires on push/PR for `lean/` itself — but this project uses `.github/workflows/ci.yml` at the repository root for all CI. An additional GitHub Actions workflow inside `lean/` would only run if `lean/` were a standalone repository pushed to GitHub separately.
- Risk of unexpected double-triggering or confusion if the repository is ever restructured.

---

## MEDIUM RISK FINDINGS

### [M1] tla/tla_wrapper.py — unreferenced TLC orchestration module
**File**: `/Users/alex.thola/math-cheatsheet/tla/tla_wrapper.py`
**Action**: ARCHIVE (or CONSOLIDATE into scripts/run_tla_checks.py)
**Confidence**: 88%
**Risk**: MEDIUM
**Token Impact**: ~2,300

**Evidence** [EN]:
- Zero import references anywhere in the codebase (grep across all `.py`, `.yml`, Makefile confirmed).
- `scripts/run_tla_checks.py` covers the same purpose: finding `tla2tools.jar`, running TLC, parsing output, printing summary. Both have a `TLCRunner`/`TLCResult` concept and a `main()`.
- `tla_wrapper.py` adds `EquationChecker` (234 lines total) which is never instantiated outside the file.
- `tla_wrapper.py` is not in `PYTHONPATH` configuration (`pyproject.toml` lists `src`, `tests`, `tla/python`; `tla/` root is excluded).
- `make tla-check` calls `scripts/run_tla_checks.py`, not `tla_wrapper.py`.
- Risk MEDIUM: the `EquationChecker` class has more TLA+ integration logic than `run_tla_checks.py`; useful as reference if TLA+ checks are expanded.

---

### [M2] tla/python/tla_bridge.py — mostly NotImplementedError stubs
**File**: `/Users/alex.thola/math-cheatsheet/tla/python/tla_bridge.py`
**Action**: REFACTOR (remove stub-only functions; keep generate_all_magmas and to_python_magma)
**Confidence**: 90%
**Risk**: MEDIUM
**Token Impact**: ~1,200

**Evidence** [EN]:
- `search_counterexample()` (line 82): body is `raise NotImplementedError(...)`. Zero callers.
- `evaluate_equation()` (line 95): body is `raise NotImplementedError(...)`. Zero callers.
- `TLAModelChecker.check_property()` (line 112): body raises `NotImplementedError`. `TLAModelChecker` class flagged by Vulture (60% confidence).
- `COUNTEREXAMPLES` dict (line 155): `{}` — empty, never populated, never read.
- `get_counterexample()` (line 158): reads from empty dict, always returns `None`. Zero external callers.
- `generate_all_magmas()` and `to_python_magma()` are actively used by `tla/python/explore_magmas.py` and tests — keep those.
- Removing the 5 stub items would reduce the file by ~80 lines.

---

### [M3] src/evaluation.py — lightly-used legacy evaluation harness
**File**: `/Users/alex.thola/math-cheatsheet/src/evaluation.py`
**Action**: ARCHIVE or CONSOLIDATE into src/competition_evaluator.py
**Confidence**: 80%
**Risk**: MEDIUM
**Token Impact**: ~2,240

**Evidence** [EN]:
- Only one external import: `tests/test_invariants_evaluation.py` (imports `EvaluationResult`, `Evaluator`).
- `evaluate_with_cheatsheet()` method (line 95) flagged by Vulture — no caller exists.
- `compare_evaluations()` function (line 181) flagged by Vulture — no caller.
- The module predates `src/competition_evaluator.py` and `src/llm_evaluator.py`; its `Evaluator` class uses "simulated" responses (the baseline results in `experiments/results/baseline/` have `"model": "simulated"`).
- `src/competition_evaluator.py` and `src/llm_evaluator.py` are the production evaluation paths.
- The `EvaluationResult` and `EvaluationSummary` dataclasses duplicate fields already present in `competition_evaluator.py` (both define correct/incorrect/accuracy/timestamp).
- Risk MEDIUM: `test_invariants_evaluation.py` directly imports from this module; removing it requires updating 230 lines of tests.

---

### [M4] src/error_analyzer.py — no runtime callers outside its own __main__
**File**: `/Users/alex.thola/math-cheatsheet/src/error_analyzer.py`
**Action**: INVESTIGATE (confirm no production use before archiving)
**Confidence**: 78%
**Risk**: MEDIUM
**Token Impact**: ~4,350

**Evidence** [EN]:
- Zero `import error_analyzer` or `from error_analyzer import` references in `src/`, `scripts/`, CI, or Makefile (other than its own test file `tests/test_error_analyzer.py`).
- The module has its own `if __name__ == "__main__"` CLI (line 410 starts a `main()` function), suggesting it was designed as a standalone analysis tool.
- Contains `ErrorAnalyzer` (line 157) which is a 280-line class analyzing decision procedure failures — genuinely useful for debugging but not wired into any automated pipeline.
- Vulture flags two dead variables at lines 47-48 (`h_is_collapse`, `t_is_collapse`).
- Risk MEDIUM: error analysis is valuable for regression diagnosis. INVESTIGATE first to confirm it is truly unused in any ad-hoc workflow before archiving.

---

### [M5] src/generate_synthetic_data.py — only referenced by its own test
**File**: `/Users/alex.thola/math-cheatsheet/src/generate_synthetic_data.py`
**Action**: ARCHIVE or move to scripts/
**Confidence**: 80%
**Risk**: MEDIUM
**Token Impact**: ~1,820

**Evidence** [EN]:
- Sole import reference: `tests/test_generate_synthetic_data.py` (line 5).
- No Makefile targets run it directly (the `generate-data` target exists but runs `src/generate_synthetic_data.py` as a script, not as an imported module).
- Produces `research/data/original/` files (equations.json, train_problems.json, implications.json). Those files exist in the repo already; the generator is not run in CI.
- The ETP dataset (`research/data/etp/equations.txt`, downloaded by `scripts/download_etp_data.py`) has superseded the synthetic data for all production use; decision procedure tests and evaluations use ETP data exclusively.
- Risk MEDIUM: `make generate-data` is a documented target. Removing or moving it would require Makefile update.

---

### [M6] scripts/demo_properties.py and scripts/demo_counterexamples.py — thin demo wrappers
**Files**:
- `/Users/alex.thola/math-cheatsheet/scripts/demo_properties.py` (14 lines)
- `/Users/alex.thola/math-cheatsheet/scripts/demo_counterexamples.py` (27 lines)
**Action**: CONSOLIDATE into Makefile inline commands or README examples
**Confidence**: 72%
**Risk**: MEDIUM
**Token Impact**: ~230

**Evidence** [EN]:
- `demo_properties.py` is 14 lines that calls `generate_all_magmas(2)` and `generate_all_magmas(3)` then prints counts — trivially reproducible as a Makefile one-liner.
- `demo_counterexamples.py` is 27 lines with hardcoded equation pairs; these cases are already covered more rigorously in `tests/test_counterexample_generator.py`.
- Both are called by `make demo-properties` / `make demo-counterexamples` — they have Makefile presence but no CI presence and no test coverage of their own output.
- Risk MEDIUM: removing them requires updating Makefile `demo-*` targets and `demo` composite target.

---

### [M7] Equation analysis dead functions in src/equation_analyzer.py
**File**: `/Users/alex.thola/math-cheatsheet/src/equation_analyzer.py`, lines 476–504
**Action**: DELETE (two functions)
**Confidence**: 80%
**Risk**: MEDIUM
**Token Impact**: ~370

**Evidence** [EN]:
- `batch_analyze()` (line 476, 11 lines): Vulture flagged (60% confidence). Zero callers in src/, scripts/, or tests/ (grep confirms). Thin wrapper over `analyze_implication`.
- `analyze_equation_structure()` (line 489, 15 lines): Vulture flagged (60% confidence). Zero callers in src/, scripts/, or tests/ (grep confirms). Returns a dict of structural properties but is not consumed anywhere.
- The high-complexity `_detect_determined_operation()` (Radon grade E, complexity 39) and `analyze_implication()` (complexity 19) are actively used — those are not candidates for removal.
- Risk MEDIUM: function signatures are public; external callers outside this repo cannot be ruled out, though this is an internal research tool.

---

### [M8] Obsolete docs/sota-research.md (limitations caveat throughout)
**File**: `/Users/alex.thola/math-cheatsheet/docs/sota-research.md`
**Action**: ARCHIVE
**Confidence**: 72%
**Risk**: MEDIUM
**Token Impact**: ~3,150

**Evidence** [EN]:
- File header notes `**Status**: Complete (with noted limitations)` and explicitly states "External web search was unavailable during this research phase" — results are explicitly unverified.
- Covers the same domain as `research/llm-math-reasoning.md` (45,931 bytes) and `research/comprehensive-research-report.md` (45,029 bytes), both of which are more detailed.
- Not referenced by any code, CI, or Makefile target.
- The content is a reasoning-from-first-principles document that acknowledges missing citations for key claims.

---

## HIGH RISK FINDINGS

### [H1] DecisionProcedure.evaluate_by_phase() — untested dead method (high complexity)
**File**: `/Users/alex.thola/math-cheatsheet/src/decision_procedure.py`, line 171
**Action**: DELETE or REFACTOR into evaluate()
**Confidence**: 92%
**Risk**: HIGH
**Token Impact**: ~500

**Evidence** [EN]:
- Vulture (60% confidence) and manual grep both confirm: zero callers in src/, tests/, scripts/, Makefile, or CI. The method is defined but never called.
- Radon rates the method grade C, complexity 14 — significant complexity for code that is never executed.
- The public `evaluate()` method on the same class (line 160) is the production path, called by `scripts/check_accuracy_gate.py` and `scripts/competition_sim.py`.
- Risk HIGH: the method name (`evaluate_by_phase`) aligns with a documented feature goal from `docs/implementation-plan.md` ("Phase 2.5: Full evaluation — per-phase accuracy breakdown"). Removing it loses the scaffolding for that feature. Recommend `REFACTOR` to either implement the per-phase breakdown in `evaluate()` or formally delete and close the issue.

---

### [H2] ImplicationOracle.equivalence_classes property and query_raw() — zero callers
**File**: `/Users/alex.thola/math-cheatsheet/src/implication_oracle.py`, lines 186–240
**Action**: REFACTOR (mark internal or remove)
**Confidence**: 85%
**Risk**: HIGH
**Token Impact**: ~650

**Evidence** [EN]:
- `equivalence_classes` property (line 186): Vulture (60%). Zero callers outside `implication_oracle.py` itself (the `_build_equivalence_classes()` private method populates it, `equivalence_classes` property exposes it). No tests or production code reads this property.
- `query_raw()` (line 229): Vulture (60%). Zero callers outside `implication_oracle.py`. The production method is `query(h_id, t_id)` — `query_raw` returns the raw integer matrix value rather than bool.
- `_build_equivalence_classes()` (line 158) runs at `__init__` time on every oracle instantiation — an O(n^2) matrix scan building sets of equivalent equations. This work is wasted if `equivalence_classes` is never consumed.
- Risk HIGH: if the oracle is ever extended for equivalence-based optimization (see research docs), these are useful primitives. Recommend marking `_equivalence_classes` truly private (`__`) and making `_build_equivalence_classes` lazy.

---

### [H3] BatchCounterexampleSearch — production dead code (tests-only usage)
**File**: `/Users/alex.thola/math-cheatsheet/src/counterexample_generator.py`, lines 112–183
**Action**: REFACTOR (move to tests/ or mark experimental)
**Confidence**: 85%
**Risk**: HIGH
**Token Impact**: ~2,000

**Evidence** [EN]:
- Vulture (60% confidence) on the class itself. Verified: only `tests/test_counterexample_generator.py` imports `BatchCounterexampleSearch` (lines 13, 228, 253–312). No production path in src/, scripts/, or CI uses it.
- Radon grades the class and its `search_batch` method both C (complexity 13 and 12 respectively) — non-trivial complexity for code not on a production path.
- `OptimalMagmaDiscovery` class (line 179, Radon C, complexity 11) has the same profile: no import outside the file and its tests, zero callers verified by grep.
- Risk HIGH: test_counterexample_generator.py depends on these classes. Removing them requires migrating or deleting those test cases (TestBatchCounterexampleSearch, 4 test methods).

---

### [H4] ETPDataset class in src/etp_equations.py — tests-only, low-confidence dead
**File**: `/Users/alex.thola/math-cheatsheet/src/etp_equations.py`, lines 296–340
**Action**: INVESTIGATE
**Confidence**: 75%
**Risk**: HIGH
**Token Impact**: ~850

**Evidence** [EN]:
- Vulture (60%) flags `ETPDataset`, `implies()`, `get_equation()`, and `equation_info()` as unused.
- Production code in `src/decision_procedure.py`, `src/llm_evaluator.py`, and `scripts/` imports `ETPEquations` (not `ETPDataset`). The `ETPDataset` class wraps both `ETPEquations` and `ImplicationOracle` as a convenience facade.
- `tests/unit/test_etp_equations.py` does not import `ETPDataset` directly, though some test fixtures use `ETPEquations` standalone.
- Risk HIGH: `ETPDataset` sits at the boundary of two actively-used classes. False removal risk is elevated. Recommend INVESTIGATE: grep for any `ETPDataset` instantiation across all scripts and notebooks before acting.

---

### [H5] Large research documentation corpus — low information density relative to size
**Files** (ARCHIVE candidates, grouped):
- `/Users/alex.thola/math-cheatsheet/research/knowledge-distillation.md` (70,256 bytes)
- `/Users/alex.thola/math-cheatsheet/research/cheatsheet-optimization.md` (74,832 bytes)
- `/Users/alex.thola/math-cheatsheet/research/formal-verification-methods.md` (59,697 bytes)
- `/Users/alex.thola/math-cheatsheet/research/llm-math-reasoning.md` (45,931 bytes)
- `/Users/alex.thola/math-cheatsheet/research/equational-implication-theory.md` (54,380 bytes)
- `/Users/alex.thola/math-cheatsheet/research/competition-strategies.md` (43,016 bytes)
- `/Users/alex.thola/math-cheatsheet/research/counterexample-strategies.md` (31,441 bytes)
- `/Users/alex.thola/math-cheatsheet/research/comprehensive-research-report.md` (45,029 bytes)
- `/Users/alex.thola/math-cheatsheet/research/applied-implementation.md` (47,611 bytes)
- `/Users/alex.thola/math-cheatsheet/research/property-taxonomy.md` (46,921 bytes)
- `/Users/alex.thola/math-cheatsheet/research/universal-algebra.md` (32,634 bytes)
- `/Users/alex.thola/math-cheatsheet/research/implication-graphs.md` (47,613 bytes)
**Action**: ARCHIVE (move to a `research/archive/` subdirectory or a separate branch)
**Confidence**: 70%
**Risk**: HIGH
**Token Impact**: ~150,000 (entire corpus ~599K bytes)

**Evidence** [EN]:
- None of these 12 files are imported, read at runtime, or referenced from any `.py`, Makefile, or CI file (grep across all code confirmed zero hits for file paths).
- The `research/INDEX.md` itself states the corpus is "60,500+ words" written by the "Egregore Autonomous Research System" — an AI research phase from 2026-03-17 to 2026-03-18, now complete.
- The final cheatsheet (`cheatsheet/final.txt`) and decision procedure (`src/decision_procedure.py`) represent the distilled output; the research corpus served its purpose during the research phase.
- Risk HIGH because these are the most contextually valuable documents for understanding why decisions were made (mathematical rationale, counterexample strategies). Archiving is strongly preferred over deletion. The files represent roughly 100K+ tokens of AI-generated research, making them the single largest context contributor after the data files.
- `research/math-review-findings.md` (8,861 bytes) and `research/tao-research-connections.md` (8,001 bytes) contain cross-references to specific lines in `cheatsheet/final.txt` (lines 120, 144) — slightly higher value than the bulk corpus, though still archivable.

---

## NOTES ON NON-FINDINGS

The following were examined and are **not** bloat:

- `cheatsheet/competition.txt` — this is already a symlink to `competition-v1.txt`, not a duplicate file.
- `cheatsheet/v1.txt`, `cheatsheet/v2.txt` — explicitly cited as historical baselines in `docs/formal-verification-summary.md`.
- `src/competition_evaluator.py`, `src/llm_evaluator.py` — standalone CLI entry points; not expected to be imported by other src modules.
- `experiments/validation/validate_cheatsheet.py`, `validate_v2.py`, `formal_validation.py` — all are active `make validate-*` targets.
- `tla/python/explore_magmas.py` — `find_property_correlations()` flagged by Vulture but file is imported by test suite and used at module level.
- Vulture's 60%-confidence dataclass field warnings (`AlgebraicEquation`, `EvaluationResult` fields, `Counterexample`) — these are false positives common to `dataclass`/`asdict` usage patterns where fields are serialized dynamically.

---

## RECOMMENDED NEXT STEPS

1. **Immediate (safe, no test changes)**:
   - Delete `cheatsheet/v3.txt` [L1]
   - Remove nested `lean/EquationalTheories/` Lake scaffolding files [L2]
   - Delete `lean/.github/` duplicate CI workflow [L11]
   - Archive `experiments/results/baseline/` [L3]
   - Archive stale planning docs (`docs/implementation-plan.md`, `docs/research-mission-plan.md`, `docs/formal-verification-considerations.md`) [L6, L7, L8]

2. **Low-effort code cleanup**:
   - Remove `batch_analyze()` and `analyze_equation_structure()` from `equation_analyzer.py` [M7]
   - Remove `sample_size` parameter or implement the sampling in `DecisionProcedure.evaluate()` [L5]
   - Delete `search_counterexample`, `evaluate_equation`, `TLAModelChecker`, `COUNTEREXAMPLES`, `get_counterexample` stubs from `tla/python/tla_bridge.py` [M2]

3. **Requires test coordination**:
   - Investigate `evaluate_by_phase()` and decide: implement or delete [H1]
   - Confirm `BatchCounterexampleSearch` and `OptimalMagmaDiscovery` are not intended for production use [H3]
   - Confirm `ETPDataset` has no callers before acting [H4]

4. **Archive bulk research corpus**:
   - Move `research/*.md` (12 large files) to `research/archive/` [H5] — largest single token savings (~150K tokens)

```
git checkout -b cleanup/bloat-report
# then address findings in priority order
```
