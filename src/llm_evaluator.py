"""Evaluate the cheatsheet with a real LLM (Claude via Anthropic API).

Sends the competition prompt template with the cheatsheet and equation pairs,
then parses the LLM's VERDICT response to measure real-world accuracy.

Usage:
    ANTHROPIC_API_KEY=sk-... python src/llm_evaluator.py [--sample N] [--model MODEL]

Requires: pip install anthropic
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

EVAL_PROMPT = """\
You are a mathematician specializing in equational theories of magmas.
Your task is to determine whether Equation 1 ({equation1}) implies \
Equation 2 ({equation2}) over all magmas.
{cheatsheet}
Output format (use exact headers without any additional text or formatting):
VERDICT: must be exactly TRUE or FALSE (in the same line).
REASONING: must be non-empty.
PROOF: required if VERDICT is TRUE, empty otherwise.
COUNTEREXAMPLE: required if VERDICT is FALSE, empty otherwise.
"""


def load_cheatsheet(path: str = "cheatsheet/competition-v1.txt") -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_verdict(response: str) -> bool | None:
    """Extract TRUE/FALSE verdict from LLM response."""
    for line in response.split("\n"):
        line = line.strip()
        if line.upper().startswith("VERDICT:"):
            verdict_str = line.split(":", 1)[1].strip().upper()
            if "TRUE" in verdict_str:
                return True
            if "FALSE" in verdict_str:
                return False
    return None


def evaluate_with_llm(
    problems: list[dict],
    cheatsheet: str,
    model: str = "claude-sonnet-4-20250514",
    max_problems: int | None = None,
) -> dict:
    """Evaluate problems using the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key.startswith("your_"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    if max_problems:
        problems = problems[:max_problems]

    tp = fp = tn = fn = 0
    errors = 0
    results_log: list[dict] = []

    for i, prob in enumerate(problems):
        prompt = EVAL_PROMPT.format(
            equation1=prob["equation_1"],
            equation2=prob["equation_2"],
            cheatsheet=cheatsheet,
        )

        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            block = response.content[0]
            text = block.text if hasattr(block, "text") else str(block)
            predicted = parse_verdict(text)
        except Exception as e:
            print(f"  Error on problem {prob['id']}: {e}")
            errors += 1
            continue

        actual = prob["answer"]
        entry = {
            "id": prob["id"],
            "equation_1": prob["equation_1"],
            "equation_2": prob["equation_2"],
            "actual": actual,
            "predicted": predicted,
            "correct": predicted == actual,
            "difficulty": prob.get("difficulty", "unknown"),
        }
        results_log.append(entry)

        if predicted is None:
            errors += 1
        elif predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

        status = "OK" if predicted == actual else "WRONG" if predicted is not None else "ERR"
        print(
            f"  [{i + 1}/{len(problems)}] {status} "
            f"E{prob.get('equation_1_id', '?')} => E{prob.get('equation_2_id', '?')} "
            f"actual={actual} pred={predicted}"
        )

        # Rate limiting
        time.sleep(0.5)

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else 0.0

    return {
        "accuracy": accuracy,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "errors": errors,
        "total": total,
        "model": model,
        "results": results_log,
    }


def generate_problems(n_normal: int = 50, n_hard: int = 10) -> list[dict]:
    """Generate problems from the implication matrix."""
    from etp_equations import ETPEquations
    from implication_oracle import ImplicationOracle

    eqs = ETPEquations("research/data/etp/equations.txt")
    oracle = ImplicationOracle("research/data/etp/implications.csv")
    collapse_ids = set(i for i in range(1, 4695) if oracle.is_collapse(i))

    problems: list[dict] = []
    random.seed(2026)

    # Normal problems
    while len(problems) < n_normal:
        h = random.randint(1, 4694)
        t = random.randint(1, 4694)
        if h == t:
            continue
        actual = oracle.query(h, t)
        if actual is None:
            continue
        problems.append(
            {
                "id": len(problems) + 1,
                "equation_1": eqs[h].text,
                "equation_2": eqs[t].text,
                "equation_1_id": h,
                "equation_2_id": t,
                "answer": actual,
                "difficulty": "normal",
            }
        )

    # Hard problems (non-collapse, similar structure)
    while len(problems) < n_normal + n_hard:
        h = random.randint(1, 4694)
        t = random.randint(1, 4694)
        if h == t or h in collapse_ids or h == 1:
            continue
        actual = oracle.query(h, t)
        if actual is None:
            continue
        if eqs[h].var_count == eqs[t].var_count:
            problems.append(
                {
                    "id": len(problems) + 1,
                    "equation_1": eqs[h].text,
                    "equation_2": eqs[t].text,
                    "equation_1_id": h,
                    "equation_2_id": t,
                    "answer": actual,
                    "difficulty": "hard",
                }
            )

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate cheatsheet with LLM")
    parser.add_argument("--sample", type=int, default=60, help="Number of problems")
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    parser.add_argument("--cheatsheet", default="cheatsheet/competition-v1.txt")
    parser.add_argument("--output", default="research/data/etp/llm_eval_results.json")
    args = parser.parse_args()

    print(f"Loading cheatsheet: {args.cheatsheet}")
    cheatsheet = load_cheatsheet(args.cheatsheet)
    print(f"Cheatsheet size: {len(cheatsheet)} bytes")

    print(f"\nGenerating {args.sample} problems...")
    n_hard = max(1, args.sample // 6)
    n_normal = args.sample - n_hard
    problems = generate_problems(n_normal, n_hard)
    print(f"Generated {len(problems)} problems")

    print(f"\nEvaluating with {args.model}...")
    result = evaluate_with_llm(problems, cheatsheet, args.model, args.sample)

    print(f"\n{'=' * 50}")
    print(f"RESULTS ({args.model})")
    print(f"{'=' * 50}")
    print(f"Accuracy: {result['accuracy']:.2%} ({result['tp'] + result['tn']}/{result['total']})")
    print(f"  TP={result['tp']} FP={result['fp']} TN={result['tn']} FN={result['fn']}")
    print(f"  Errors (unparseable): {result['errors']}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
