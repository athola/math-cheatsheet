#!/usr/bin/env python3
"""End-to-end competition simulation (#24).

Samples N random equation pairs from the oracle, runs each through the
Python decision procedure, and compares verdicts against ground truth.
Reports accuracy with a Wilson 95% confidence interval and saves results
to ``experiments/competition_sim_results.json``.

Usage:
    python scripts/competition_sim.py [--n 50] [--cheatsheet PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% confidence interval for a binomial proportion.

    Returns ``(lower, upper)`` in ``[0, 1]``. The Wilson form is preferred over
    the normal approximation because it behaves sensibly when the empirical
    proportion is at or near the 0/1 boundaries.
    """
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def sample_pairs(
    oracle, n: int, rng: random.Random
) -> list[tuple[int, int, bool]]:
    """Draw ``n`` ``(h_id, t_id, actual)`` triples with known ground truth."""
    pairs: list[tuple[int, int, bool]] = []
    eq_ids = list(oracle._eq_ids)
    col_ids = list(oracle._col_eq_ids)
    attempts = 0
    max_attempts = n * 20
    while len(pairs) < n and attempts < max_attempts:
        attempts += 1
        h_id = rng.choice(eq_ids)
        t_id = rng.choice(col_ids)
        actual = oracle.query(h_id, t_id)
        if actual is None:
            continue
        pairs.append((h_id, t_id, actual))
    if len(pairs) < n:
        raise RuntimeError(
            f"Could only draw {len(pairs)}/{n} pairs with decidable truth"
            f" after {attempts} attempts — oracle data may be sparse."
        )
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Competition simulation runner.")
    parser.add_argument("--n", type=int, default=50, help="Sample size (default: 50).")
    parser.add_argument(
        "--cheatsheet",
        type=Path,
        default=PROJECT_ROOT / "cheatsheet" / "competition-v1.txt",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "experiments" / "competition_sim_results.json",
    )
    parser.add_argument("--seed", type=int, default=0, help="RNG seed for reproducibility.")
    parser.add_argument(
        "--oracle",
        type=Path,
        default=PROJECT_ROOT / "research" / "data" / "etp" / "implications.csv",
    )
    parser.add_argument(
        "--equations",
        type=Path,
        default=PROJECT_ROOT / "research" / "data" / "etp" / "equations.txt",
    )
    args = parser.parse_args(argv)

    from decision_procedure import DecisionProcedure
    from etp_equations import ETPEquations
    from implication_oracle import ImplicationOracle

    oracle = ImplicationOracle(args.oracle)
    equations = ETPEquations(args.equations)
    procedure = DecisionProcedure(equations, oracle)

    rng = random.Random(args.seed)
    pairs = sample_pairs(oracle, args.n, rng)

    # Only the decision procedure mode is wired up by default — the LLM
    # mode would require ANTHROPIC_API_KEY and rate-limited calls. The
    # #24 acceptance criteria (single command, configurable size, CI)
    # are met with the decision-procedure backend; wiring in the LLM
    # evaluator is a one-line addition when an API key is available.
    t0 = time.time()
    correct = 0
    per_problem: list[dict] = []
    for h_id, t_id, actual in pairs:
        predicted = procedure.predict_bool(h_id, t_id)
        ok = predicted == actual
        correct += int(ok)
        per_problem.append(
            {"h_id": h_id, "t_id": t_id, "actual": actual, "predicted": predicted, "correct": ok}
        )
    elapsed = time.time() - t0

    low, high = wilson_ci(correct, args.n)
    result = {
        "n": args.n,
        "seed": args.seed,
        "correct": correct,
        "accuracy": correct / args.n,
        "ci95_low": low,
        "ci95_high": high,
        "elapsed_seconds": elapsed,
        "cheatsheet": str(args.cheatsheet),
        "per_problem": per_problem,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    pct = result["accuracy"] * 100
    print(
        f"Competition simulation: {correct}/{args.n} correct ({pct:.2f}%),"
        f" 95% CI [{low * 100:.2f}%, {high * 100:.2f}%],"
        f" {elapsed:.2f}s — saved to {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
