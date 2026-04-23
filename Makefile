# Math Cheatsheet - Equational Theories
# Formal verification grounded approach for STEP competition

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON := venv/bin/python
PYTEST := venv/bin/python -m pytest
RUFF := venv/bin/ruff
MYPY := venv/bin/mypy
PYTHONPATH := PYTHONPATH=src:tla/python

# ── Core ────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Set up venv and install dependencies
	python3 -m venv venv
	$(PYTHON) -m pip install --quiet -e ".[dev]"
	$(PYTHON) -m pip install --quiet pre-commit
	$(PYTHON) -m pre_commit install

.PHONY: build-rust
build-rust: ## Build Rust PyO3 extension (magma_core)
	cd rust && cargo build --release

.PHONY: install-rust
install-rust: ## Build and install Rust extension into venv
	cd rust && $(PYTHON) -m pip install --quiet maturin && maturin develop --release

.PHONY: lean-check
lean-check: ## Check Lean 4 formal proofs
	cd lean && lake build

# ── Quality ─────────────────────────────────────────────────────

.PHONY: test
test: ## Run all tests
	$(PYTHONPATH) $(PYTEST) -v

.PHONY: test-quick
test-quick: ## Run tests (no verbose, fail-fast)
	$(PYTHONPATH) $(PYTEST) -x -q

.PHONY: test-property
test-property: ## Run property-based invariant tests (Hypothesis)
	$(PYTHONPATH) $(PYTEST) -v -m property

.PHONY: test-cross-language
test-cross-language: ## Run cross-language consistency tests (Python ↔ Rust)
	$(PYTHONPATH) $(PYTEST) -v -m cross_language

.PHONY: test-rust
test-rust: ## Run Rust proptest invariant tests
	cd rust && cargo test --release -- --nocapture

.PHONY: test-invariants
test-invariants: test-property test-cross-language test-rust ## Run all invariant tests

.PHONY: lint
lint: ## Lint Python source with ruff
	$(RUFF) check src/ tests/ experiments/ tla/python/

.PHONY: format
format: ## Auto-format Python source with ruff
	$(RUFF) format src/ tests/ experiments/ tla/python/
	$(RUFF) check --fix src/ tests/ experiments/ tla/python/

.PHONY: typecheck
typecheck: ## Run mypy type checking
	$(PYTHONPATH) $(MYPY) src/ --ignore-missing-imports

.PHONY: check
check: lint typecheck test test-rust ## Run all quality gates (lint + typecheck + test + rust)

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files
	$(PYTHON) -m pre_commit run --all-files

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit git hooks
	$(PYTHON) -m pre_commit install

# ── Data ────────────────────────────────────────────────────────

.PHONY: generate-data
generate-data: ## Generate synthetic equations and problems
	$(PYTHON) scripts/generate_synthetic_data.py

.PHONY: parse-data
parse-data: ## Parse and validate equation/problem data (LIVE)
	$(PYTHONPATH) $(PYTHON) src/parsers.py

# ── Cheatsheet Test Harness ────────────────────────────────────
# Five validation angles, all dogfoodable independently.

HARNESS := $(PYTHONPATH) $(PYTHON) -m src.cheatsheet_harness
CHEATSHEET ?= cheatsheet/final.txt

.PHONY: harness
harness: ## Run full cheatsheet validation harness (all 5 angles)
	$(HARNESS) all $(CHEATSHEET)

.PHONY: harness-compliance
harness-compliance: ## Check cheatsheet size, encoding, format (LIVE)
	$(HARNESS) compliance $(CHEATSHEET)

.PHONY: harness-structure
harness-structure: ## Validate cheatsheet content structure (LIVE)
	$(HARNESS) structure $(CHEATSHEET)

.PHONY: harness-accuracy
harness-accuracy: ## Test decision procedure on known problems (LIVE)
	$(HARNESS) accuracy $(CHEATSHEET)

.PHONY: harness-regression
harness-regression: ## Cross-version quality comparison (LIVE)
	$(HARNESS) regression $(CHEATSHEET)

.PHONY: harness-competition
harness-competition: ## Simulate competition evaluation format (LIVE)
	$(HARNESS) competition $(CHEATSHEET)

.PHONY: competition-sim
competition-sim: ## Run end-to-end competition simulation (#24)
	PYTHONPATH=src:tla/python $(PYTHON) scripts/competition_sim.py --n $${N:-50} --seed $${SEED:-0}

.PHONY: accuracy-gate
accuracy-gate: ## Enforce accuracy threshold (regression #23)
	PYTHONPATH=src:tla/python $(PYTHON) scripts/check_accuracy_gate.py --threshold $${MIN_ACCURACY:-98.0}

.PHONY: test-harness
test-harness: ## Run harness pytest suite (31 tests)
	$(PYTHONPATH) $(PYTEST) tests/test_cheatsheet_harness.py -v

# ── Legacy Validation (LIVE) ──────────────────────────────────

.PHONY: validate-cheatsheet
validate-cheatsheet: ## Validate cheatsheet v1 against known implications (LIVE)
	$(PYTHONPATH) $(PYTHON) experiments/validation/validate_cheatsheet.py

.PHONY: validate-v2
validate-v2: ## Validate cheatsheet v2 rules (LIVE)
	$(PYTHONPATH) $(PYTHON) experiments/validation/validate_v2.py

.PHONY: validate-formal
validate-formal: ## Run formal verification checks (LIVE)
	$(PYTHONPATH) $(PYTHON) experiments/validation/formal_validation.py

.PHONY: validate-all
validate-all: harness validate-cheatsheet validate-v2 validate-formal ## Run all validation (harness + legacy)

# ── Evaluation (LIVE) ───────────────────────────────────────────

.PHONY: evaluate-baseline
evaluate-baseline: ## Run baseline LLM evaluation (LIVE, simulated)
	$(PYTHONPATH) $(PYTHON) src/evaluation.py

.PHONY: download-etp
download-etp: ## Download ETP equation data from GitHub
	$(PYTHONPATH) $(PYTHON) scripts/download_etp_data.py

.PHONY: etp-status
etp-status: ## Print ETP dataset stats (equations, matrix, classifications)
	@$(PYTHONPATH) $(PYTHON) -c "\
	from etp_equations import ETPDataset; \
	ds = ETPDataset(); \
	s = ds.summary(); \
	print('=== ETP Dataset Status ==='); \
	print(f'Equations:  {s[\"total_equations\"]}'); \
	print(f'Matrix:     {s[\"matrix_shape\"][0]}x{s[\"matrix_shape\"][1]}'); \
	print(); \
	print('Oracle classification:'); \
	[print(f'  {k}: {v}') for k, v in sorted(s['classification_counts'].items())]; \
	print(); \
	print('Structural classification:'); \
	[print(f'  {k}: {v}') for k, v in sorted(s['structural_counts'].items())]; \
	"

# ── Demo (LIVE - dogfooding) ────────────────────────────────────

.PHONY: demo-magmas
demo-magmas: ## Generate and inspect all size-2 magmas (LIVE)
	@echo "=== Magma Generation Demo (LIVE) ==="
	$(PYTHONPATH) $(PYTHON) tla/python/tla_bridge.py

.PHONY: demo-properties
demo-properties: ## Count magma properties across size-2 and size-3 (LIVE)
	@echo "=== Magma Property Census (LIVE) ==="
	$(PYTHONPATH) $(PYTHON) scripts/demo.py --mode properties

.PHONY: demo-counterexamples
demo-counterexamples: ## Find counterexamples to classic non-implications (LIVE)
	@echo "=== Counterexample Search Demo (LIVE) ==="
	$(PYTHONPATH) $(PYTHON) scripts/demo.py --mode counterexamples

.PHONY: demo-cheatsheet
demo-cheatsheet: ## Show cheatsheet stats and byte count (LIVE)
	@echo "=== Cheatsheet Analysis (LIVE) ==="
	@for f in cheatsheet/*.txt; do \
		bytes=$$(wc -c < "$$f"); \
		lines=$$(wc -l < "$$f"); \
		echo "  $$f: $$bytes bytes, $$lines lines (limit: 10240 bytes)"; \
	done

.PHONY: demo
demo: demo-magmas demo-properties demo-counterexamples demo-cheatsheet ## Run all demos (LIVE)

# ── TLA+ Model Checking ───────────────────────────────────────────

.PHONY: tla-setup
tla-setup: ## Download TLA+ tools (tla2tools.jar)
	bash scripts/setup_tla_tools.sh

.PHONY: tla-check
tla-check: ## Run TLC model checker on all TLA+ modules
	$(PYTHON) scripts/run_tla_checks.py

.PHONY: tla-check-verbose
tla-check-verbose: ## Run TLC with verbose output
	$(PYTHON) scripts/run_tla_checks.py --verbose

# ── Clean ───────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -not -path './venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/
