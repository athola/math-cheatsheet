#!/usr/bin/env python3
"""Enforce a minimum decision-procedure accuracy threshold.

Intended for CI (#23): runs the harness, parses the "Accuracy: X.XX%" line,
and exits non-zero if the measured accuracy drops below ``MIN_ACCURACY``.

Usage:
    python scripts/check_accuracy_gate.py [--threshold PCT] [--cheatsheet PATH]

Reads the measured value from the harness's own output so there is only one
canonical place accuracy is computed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_harness(cheatsheet: Path) -> str:
    """Invoke the accuracy harness and capture its stdout."""
    proc = subprocess.run(
        [sys.executable, "-m", "cheatsheet_harness", "accuracy", str(cheatsheet)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=None,
    )
    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        print(output, file=sys.stderr)
        raise SystemExit(
            f"Harness exited with status {proc.returncode} — see output above."
        )
    return output


def parse_accuracy_pct(text: str) -> float | None:
    """Extract the accuracy as a percentage from the harness output."""
    m = re.search(r"Accuracy[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*%", text)
    if m:
        return float(m.group(1))
    m = re.search(r"Accuracy[^0-9]*(0?\.[0-9]+)\b", text)
    if m:
        return float(m.group(1)) * 100.0
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enforce a minimum accuracy threshold.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=98.0,
        help="Minimum acceptable accuracy percentage (default: 98.0).",
    )
    parser.add_argument(
        "--cheatsheet",
        type=Path,
        default=PROJECT_ROOT / "cheatsheet" / "competition-v1.txt",
        help="Path to the cheatsheet file.",
    )
    args = parser.parse_args(argv)

    output = run_harness(args.cheatsheet)
    print(output)

    pct = parse_accuracy_pct(output)
    if pct is None:
        print("Could not parse accuracy from harness output.", file=sys.stderr)
        return 2

    print(f"Measured accuracy: {pct:.2f}%")
    print(f"Threshold:         {args.threshold:.2f}%")
    if pct < args.threshold:
        print(
            f"FAIL: accuracy {pct:.2f}% is below threshold {args.threshold:.2f}%",
            file=sys.stderr,
        )
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
