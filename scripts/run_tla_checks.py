#!/usr/bin/env python3
"""Run TLC model checker on all TLA+ modules and report results.

Usage:
    python scripts/run_tla_checks.py [--timeout SECONDS] [--verbose]

Requires: Java 11+ and tla2tools.jar (run scripts/setup_tla_tools.sh first).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

TLCStatus = Literal["pass", "fail", "error", "skip", "unknown"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TLA_DIR = PROJECT_ROOT / "tla" / "MagmaSpecifications"
TOOLS_JAR = PROJECT_ROOT / "tla" / "tools" / "tla2tools.jar"


@dataclass(frozen=True)
class TLCResult:
    """One TLC run outcome.

    Frozen so aggregated result lists are effectively read-only (#43/I4).
    The ``warnings`` list remains mutable by Python semantics — the freeze
    is on the record's identity, not the contents of its list fields.
    """

    module: str
    status: TLCStatus
    elapsed_seconds: float = 0.0
    message: str = ""
    states_found: int = 0
    distinct_states: int = 0
    warnings: list[str] = field(default_factory=list)


def find_tla_tools() -> Path | None:
    """Locate tla2tools.jar."""
    candidates = [
        TOOLS_JAR,
        Path("/usr/share/tla/tla2tools.jar"),
        Path.home() / "tla" / "tools" / "tla2tools.jar",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def run_tlc(
    module: str,
    config: str | None = None,
    timeout: int = 120,
    verbose: bool = False,
) -> TLCResult:
    """Run TLC on a single module."""
    jar = find_tla_tools()
    if not jar:
        return TLCResult(
            module=module,
            status="skip",
            message="tla2tools.jar not found. Run: scripts/setup_tla_tools.sh",
        )

    cmd = [
        "java",
        "-XX:+UseParallelGC",
        "-cp",
        str(jar),
        "tlc2.TLC",
        "-deadlock",
        "-cleanup",
    ]

    tla_file = TLA_DIR / f"{module}.tla"
    if not tla_file.exists():
        return TLCResult(module=module, status="error", message=f"File not found: {tla_file}")

    if config:
        cfg_file = TLA_DIR / config
        if cfg_file.exists():
            cmd.extend(["-config", str(cfg_file)])

    cmd.append(str(tla_file))

    if verbose:
        print(f"  Running: {' '.join(cmd)}")

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TLA_DIR),
        )
        elapsed = time.time() - t0
        return parse_tlc_output(module, proc.stdout + proc.stderr, proc.returncode, elapsed)

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return TLCResult(
            module=module,
            status="error",
            elapsed_seconds=elapsed,
            message=f"Timeout after {timeout}s",
        )
    except FileNotFoundError:
        return TLCResult(module=module, status="error", message="Java not found in PATH")


def parse_tlc_output(module: str, output: str, returncode: int, elapsed: float) -> TLCResult:
    """Parse TLC stdout+stderr into a structured result."""
    # Decide status + human message.
    status: TLCStatus
    message: str
    if "Model checking completed. No error has been found." in output:
        status = "pass"
        message = "All properties verified"
    elif "Finished computing initial states" in output and returncode == 0:
        status = "pass"
        message = "Model checking completed"
    elif "Error:" in output or returncode != 0:
        status = "fail"
        error_lines = [
            line for line in output.split("\n") if "Error" in line or "error" in line.lower()
        ]
        message = "; ".join(error_lines[:3]) if error_lines else f"Exit code {returncode}"
    else:
        status = "pass"
        message = "Completed"

    # Extract state counts.
    states_found = 0
    distinct_states = 0
    states_match = re.search(r"(\d+) states generated.*?(\d+) distinct states", output)
    if states_match:
        states_found = int(states_match.group(1))
        distinct_states = int(states_match.group(2))

    warnings = [line.strip() for line in output.split("\n") if "Warning:" in line]

    return TLCResult(
        module=module,
        status=status,
        elapsed_seconds=elapsed,
        message=message,
        states_found=states_found,
        distinct_states=distinct_states,
        warnings=warnings,
    )


# Modules to check with their corresponding .cfg files (if any)
MODULES_TO_CHECK = [
    ("Magma", None),
    ("MagmaModel", "MagmaModel.cfg"),
    ("EquationChecking", "EquationChecking.cfg"),
    ("InvariantCheck", None),
    ("TEST_MODEL", None),
]


def run_all_checks(timeout: int = 120, verbose: bool = False) -> list[TLCResult]:
    """Run TLC on all registered modules."""
    results = []
    for module, config in MODULES_TO_CHECK:
        if verbose:
            print(f"\nChecking {module}...")
        result = run_tlc(module, config=config, timeout=timeout, verbose=verbose)
        results.append(result)
        status_icon = {"pass": "OK", "fail": "FAIL", "error": "ERR", "skip": "SKIP"}[result.status]
        print(f"  [{status_icon}] {module}: {result.message} ({result.elapsed_seconds:.1f}s)")
    return results


def print_summary(results: list[TLCResult]) -> int:
    """Print summary and return exit code."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    errors = sum(1 for r in results if r.status == "error")
    skipped = sum(1 for r in results if r.status == "skip")

    print(f"\n{'=' * 50}")
    print("TLA+ Model Checking Summary")
    print(f"{'=' * 50}")
    print(f"  Total:   {total}")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Errors:  {errors}")
    print(f"  Skipped: {skipped}")

    total_time = sum(r.elapsed_seconds for r in results)
    print(f"  Time:    {total_time:.1f}s")

    if failed > 0 or errors > 0:
        print("\nFailed modules:")
        for r in results:
            if r.status in ("fail", "error"):
                print(f"  - {r.module}: {r.message}")

    return 0 if failed == 0 and errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TLC model checker on TLA+ modules")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per module (seconds)")
    parser.add_argument("--verbose", action="store_true", help="Show TLC commands")
    parser.add_argument("--json", help="Save results to JSON file")
    args = parser.parse_args()

    print("TLA+ Model Checking (TLAP-001)")
    print(f"Specs directory: {TLA_DIR}")

    jar = find_tla_tools()
    if not jar:
        print("\nERROR: tla2tools.jar not found.")
        print("Run: bash scripts/setup_tla_tools.sh")
        return 1

    print(f"Tools: {jar}")

    results = run_all_checks(timeout=args.timeout, verbose=args.verbose)

    if args.json:
        data = [
            {
                "module": r.module,
                "status": r.status,
                "elapsed": r.elapsed_seconds,
                "message": r.message,
                "states": r.states_found,
                "distinct_states": r.distinct_states,
                "warnings": r.warnings,
            }
            for r in results
        ]
        Path(args.json).write_text(json.dumps(data, indent=2))

    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
