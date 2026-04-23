#!/usr/bin/env python3
"""
TLA+ Bridge for Automated Counterexample Generation

This module provides Python integration with TLA+ model checker
for automated counterexample finding in finite magmas.

When the compiled Rust extension `magma_core` is available, generation
and property checks run 20-60x faster. Falls back to pure Python otherwise.
"""

from __future__ import annotations

import functools
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# Requires PYTHONPATH=src:tla/python (set by Makefile)
from data_models import Counterexample, Magma

_logger = logging.getLogger(__name__)

try:
    from magma_core import generate_all_magmas as _rust_generate  # type: ignore[import-not-found]
except ImportError:
    _rust_generate = None
    _logger.warning(
        "magma_core Rust extension not available; falling back to pure Python "
        "(20-60x slower). Build with: cd rust && maturin develop --release"
    )

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ETP_EQUATIONS_PATH = _PROJECT_ROOT / "research" / "data" / "etp" / "equations.txt"


@functools.lru_cache(maxsize=8)
def generate_all_magmas(size: int) -> tuple:
    """
    Generate all magmas of a given size.

    Warning: This grows as n^(n^2), so only use for small n.
    Returns a tuple (hashable for caching).

    When the Rust extension is available, returns ``magma_core.Magma``
    objects (~20x faster generation, ~20x faster property checks).
    Falls back to ``data_models.Magma`` otherwise.
    Both expose the same API: op(), is_associative(), is_commutative(),
    has_identity(), is_idempotent(), cayley_table_str(), to_tla().
    """
    if _rust_generate is not None:
        return tuple(_rust_generate(size))

    if size > 4:
        raise ValueError(f"Size {size} too large for exhaustive generation")

    magmas = []
    n = size
    total = n ** (n * n)

    for i in range(total):
        table = [[0] * n for _ in range(n)]
        temp = i
        for row in range(n):
            for col in range(n):
                table[row][col] = temp % n
                temp //= n

        magmas.append(Magma(size=size, operation=table))

    return tuple(magmas)


def to_python_magma(magma) -> Magma:
    """Convert a Rust Magma to a data_models.Magma (for serialization methods)."""
    if isinstance(magma, Magma):
        return magma
    return Magma(
        size=magma.size,
        operation=[list(row) for row in magma.operation],
    )


def evaluate_equation(magma: Magma, equation: str, assignment: dict[str, int]) -> bool:
    """Evaluate an equation in a magma given a specific variable assignment.

    Args:
        magma: The finite magma to evaluate in.
        equation: Equation string in the form "LHS = RHS", e.g. "x ◇ y = y ◇ x".
                  Accepts both ◇ and * as the binary operation symbol.
        assignment: Map from variable names to carrier elements, e.g. {"x": 0, "y": 1}.

    Returns:
        True if LHS and RHS evaluate to the same element under the assignment.
    """
    from equation_analyzer import parse_equation as _parse

    eq = _parse(equation)
    required = eq.lhs.variables() | eq.rhs.variables()
    missing = required - set(assignment)
    if missing:
        raise ValueError(
            f"Assignment missing variable(s) {sorted(missing)}; required: {sorted(required)}"
        )
    lhs_val = eq.lhs.evaluate(magma.operation, assignment)
    rhs_val = eq.rhs.evaluate(magma.operation, assignment)
    return lhs_val == rhs_val


def search_counterexample(
    equations_holding: list[int], equation_to_test: int, max_size: int = 4
) -> Counterexample | None:
    """Search for a magma where all ``equations_holding`` hold but ``equation_to_test`` does not.

    Equations are identified by their 1-based line number in the ETP equations.txt file.
    Searches exhaustively over magmas of size 2 up to ``max_size`` (capped at 3 for
    pure-Python fallback to avoid 4^16 ≈ 4B table enumeration; Rust extension allows 4).

    Args:
        equations_holding: List of ETP equation IDs that must hold in the witness magma.
        equation_to_test: ETP equation ID that must *not* hold in the witness magma.
        max_size: Maximum magma carrier size to search.

    Returns:
        A Counterexample if a witness is found, or None if none exists up to max_size.

    Raises:
        ValueError: If any equation ID is out of range for equations.txt.
    """
    from equation_analyzer import parse_equation as _parse

    if not _ETP_EQUATIONS_PATH.exists():
        _logger.warning("equations.txt not found at %s", _ETP_EQUATIONS_PATH)
        return None

    lines = _ETP_EQUATIONS_PATH.read_text(encoding="utf-8").splitlines()
    total_equations = len(lines)

    def _load(eq_id: int):
        if eq_id < 1 or eq_id > total_equations:
            raise ValueError(
                f"Equation ID {eq_id} out of range 1-{total_equations}"
            )
        return _parse(lines[eq_id - 1].strip())

    premises = [_load(eid) for eid in equations_holding]
    target = _load(equation_to_test)

    # Pure Python is too slow for size 4 (4^16 ≈ 4B tables); cap unless Rust available.
    py_max = min(max_size, 4 if _rust_generate is not None else 3)

    for size in range(2, py_max + 1):
        for magma_obj in generate_all_magmas(size):
            m = to_python_magma(magma_obj)
            table = m.operation
            if all(p.holds_in(table, size) for p in premises) and not target.holds_in(table, size):
                premise_id = equations_holding[0] if len(equations_holding) == 1 else -1
                return Counterexample(
                    premise_id=premise_id,
                    conclusion_id=equation_to_test,
                    magma=m,
                )

    return None


class TLAModelChecker:
    """Interface to TLA+ model checker."""

    def __init__(self, tla_dir: str):
        self.tla_dir = tla_dir
        self.tla_modules = ["Magma", "EquationChecking", "MagmaModel"]

    def _find_tla_tools(self) -> Path | None:
        """Locate tla2tools.jar in standard locations."""
        candidates = [
            Path(self.tla_dir).parent / "tools" / "tla2tools.jar",
            Path("/usr/share/tla/tla2tools.jar"),
            Path.home() / "tla" / "tools" / "tla2tools.jar",
        ]
        return next((p for p in candidates if p.exists()), None)

    def check_property(
        self, module: str, property_name: str, constants: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Run TLC model checker to verify a property.

        Args:
            module: TLA+ module name (without .tla extension).
            property_name: Name of the property/invariant to check (for logging).
            constants: CONSTANTS to inject into the TLC config file.

        Returns:
            (True, None) if no error found; (False, trace) where trace is the
            error/counterexample output from TLC.

        Raises:
            RuntimeError: If tla2tools.jar is not found.
            FileNotFoundError: If the .tla module file does not exist.
            RuntimeError: If TLC times out (>120 s).
        """
        jar = self._find_tla_tools()
        if jar is None:
            raise RuntimeError(
                "tla2tools.jar not found. Run: bash scripts/setup_tla_tools.sh"
            )

        tla_file = Path(self.tla_dir) / f"{module}.tla"
        if not tla_file.exists():
            raise FileNotFoundError(f"TLA+ module not found: {tla_file}")

        config = self._generate_config(constants)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config)
            config_path = f.name

        cmd = [
            "java", "-XX:+UseParallelGC",
            "-cp", str(jar),
            "tlc2.TLC", "-deadlock", "-cleanup",
            "-config", config_path,
            str(tla_file),
        ]
        _logger.debug("Running TLC: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.tla_dir,
            )
            output = proc.stdout + proc.stderr

            if "No error has been found" in output or (
                "Finished computing initial states" in output and proc.returncode == 0
            ):
                return True, None

            error_lines = [
                line for line in output.splitlines() if "Error" in line or "State" in line
            ]
            trace = "\n".join(error_lines) if error_lines else output
            return False, trace

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"TLC timed out after 120s for module {module}")
        finally:
            os.unlink(config_path)

    def _generate_config(self, constants: dict[str, Any]) -> str:
        lines = ["------- MODULE MagmaModelConf -------"]
        for name, value in constants.items():
            lines.append(f"{name} == {self._format_tla_value(value)}")
        lines.append("=================================")
        return "\n".join(lines)

    def _format_tla_value(self, value: Any) -> str:
        if isinstance(value, set):
            return "{" + ", ".join(self._format_tla_value(v) for v in value) + "}"
        elif isinstance(value, list):
            return "<<" + ", ".join(self._format_tla_value(v) for v in value) + ">>"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, str):
            return f'"{value}"'
        else:
            return str(value)


# Predefined counterexamples for common non-implications
COUNTEREXAMPLES: dict[tuple[int, int], Magma] = {}


def get_counterexample(premise_id: int, conclusion_id: int) -> Magma | None:
    """Get known counterexample for implication premise_id => conclusion_id."""
    return COUNTEREXAMPLES.get((premise_id, conclusion_id))


if __name__ == "__main__":
    print("Generating magmas of size 2...")
    magmas = generate_all_magmas(2)
    print(f"Found {len(magmas)} magmas")

    associative_count = sum(1 for m in magmas if m.is_associative())
    commutative_count = sum(1 for m in magmas if m.is_commutative())

    print(f"Associative: {associative_count}/{len(magmas)}")
    print(f"Commutative: {commutative_count}/{len(magmas)}")

    m = magmas[0]
    print("\nExample magma:")
    print(m.cayley_table_str())
