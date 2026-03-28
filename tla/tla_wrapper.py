#!/usr/bin/env python3
"""
TLA+ Model Checker Wrapper

Automates running TLC (TLA+ model checker) on magma specifications
and parsing results for counterexample analysis.

Usage:
    python tla_wrapper.py --model TEST_MODEL --specs Magma,EquationChecking,MagmaModel
    python tla_wrapper.py --verify-implication --eqn1 associativity --eqn2 commutativity
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class TLCRunner:
    """Wrapper for running TLC model checker."""

    def __init__(self, tla_dir: Path, tools_path: Path | None = None):
        """
        Initialize TLC runner.

        Args:
            tla_dir: Directory containing TLA+ specifications
            tools_path: Path to TLA+ tools (tla2tools.jar). If None, tries common locations.
        """
        self.tla_dir = Path(tla_dir)
        self.tools_path = tools_path or self._find_tla_tools()

    def _find_tla_tools(self) -> Path | None:
        """Find TLA+ tools jar file in common locations."""
        common_paths = [
            Path("/usr/share/tla/tla2tools.jar"),
            Path.home() / "tla" / "tools" / "tla2tools.jar",
            Path("/opt/tla/tools/tla2tools.jar"),
            Path("C:\\Program Files\\TLA+\\Tools\\tla2tools.jar"),
        ]

        for path in common_paths:
            if path.exists():
                return path

        # Try to find in PATH
        try:
            result = subprocess.run(
                ["which", "tlc2.TLC"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except FileNotFoundError:
            pass

        return None

    def run(
        self,
        model: str,
        specs: list[str],
        depth: int = 100,
        timeout: int = 300,
        config: str | None = None,
    ) -> dict[str, Any]:
        """
        Run TLC on a model.

        Args:
            model: Name of the model module (without .tla)
            specs: List of spec modules to extend
            depth: Depth for breadth-first search
            timeout: Timeout in seconds
            config: Optional .cfg file to use

        Returns:
            Dictionary with status, output, and any counterexamples found
        """
        if not self.tools_path:
            return {
                "status": "error",
                "error": "TLA+ tools not found. Please install TLA+ Toolbox.",
            }

        cmd = [
            "java",
            "-cp",
            str(self.tools_path),
            "tlc2.TLC",
            "-depth",
            str(depth),
            "-deadlock",
        ]

        if config:
            cmd.extend(["-config", str(self.tla_dir / config)])

        cmd.append(str(self.tla_dir / f"{model}.tla"))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, cwd=str(self.tla_dir)
            )

            return self._parse_tlc_output(result.stdout, result.stderr, result.returncode)

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": f"Model checking timed out after {timeout}s"}
        except (FileNotFoundError, OSError) as e:
            return {"status": "error", "error": str(e)}

    def _parse_tlc_output(self, stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
        """Parse TLC output to extract results."""
        output = stdout + stderr

        # Check for success
        if "Model checking completed" in output:
            return {
                "status": "success",
                "message": "Model checking completed successfully",
                "output": output,
            }

        # Check for errors
        if returncode != 0:
            # Extract error message
            error_match = re.search(r"Error: (.+)", output)
            if error_match:
                return {"status": "error", "error": error_match.group(1), "output": output}

        # Check for counterexamples (invariant violations)
        counterexample = self._extract_counterexample(output)
        if counterexample:
            return {"status": "counterexample", "counterexample": counterexample, "output": output}

        return {"status": "unknown", "output": output}

    def _extract_counterexample(self, output: str) -> dict[str, Any] | None:
        """Extract counterexample from TLC output."""
        # TLC typically outputs counterexamples in a specific format
        # This is a simplified parser

        state_pattern = r"State (\d+):\s*\n((?:\s+\w+\s*=\s*.*\n)*)"
        states = re.findall(state_pattern, output)

        if not states:
            return None

        parsed_states = []
        for state_num, state_vars in states:
            variables = {}
            for line in state_vars.strip().split("\n"):
                if "=" in line:
                    var, val = line.split("=", 1)
                    variables[var.strip()] = val.strip()

            parsed_states.append({"state_number": int(state_num), "variables": variables})

        return {"states": parsed_states} if parsed_states else None


class EquationChecker:
    """Check equation implications using TLA+."""

    def __init__(self, tla_dir: Path):
        self.tla_dir = tla_dir
        self.runner = TLCRunner(tla_dir)

        # Common equation encodings
        self.equations = {
            "associativity": [["*", ["*", ["x"], ["y"]], ["z"]], ["*", ["x"], ["*", ["y"], ["z"]]]],
            "commutativity": [["*", ["x"], ["y"]], ["*", ["y"], ["x"]]],
            "idempotence": [["*", ["x"], ["x"]], ["x"]],
            "left_identity": [["*", ["e"], ["x"]], ["x"]],
            "right_identity": [["*", ["x"], ["e"]], ["x"]],
        }

    def check_implication(self, eqn1: str, eqn2: str, magma_size: int = 2) -> dict[str, Any]:
        """
        Check if equation 1 implies equation 2.

        Args:
            eqn1: Name/encoding of premise equation
            eqn2: Name/encoding of conclusion equation
            magma_size: Size of magma to search for counterexamples

        Returns:
            Result with status ("proves", "disproves", "unknown") and counterexample if found
        """
        raise NotImplementedError(
            "Full implication checking requires dynamic TLA+ module generation. "
            "Use tla/python/explore_magmas.find_implication_counterexamples() "
            "for property-based counterexample search."
        )


def main():
    parser = argparse.ArgumentParser(description="TLA+ Model Checker Wrapper")
    parser.add_argument("--tla-dir", default=".", help="Directory containing TLA+ specs")
    parser.add_argument("--model", help="Model module to run")
    parser.add_argument("--specs", help="Comma-separated list of spec modules")
    parser.add_argument("--depth", type=int, default=100, help="Search depth")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")

    args = parser.parse_args()

    if not args.model or not args.specs:
        parser.error("--model and --specs are required")

    runner = TLCRunner(Path(args.tla_dir))
    result = runner.run(
        model=args.model, specs=args.specs.split(","), depth=args.depth, timeout=args.timeout
    )

    print(json.dumps(result, indent=2))

    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
