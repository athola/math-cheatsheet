"""Evaluate the cheatsheet with a real LLM (Claude via Anthropic API).

Sends the competition prompt template with the cheatsheet and equation pairs,
then parses the LLM's VERDICT response to measure real-world accuracy.

Usage:
    ANTHROPIC_API_KEY=sk-... python src/llm_evaluator.py [--sample N] [--model MODEL]

Requires: pip install anthropic
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


CACHE_VERSION = 1
# Approximate pricing for cost estimates (USD per token)
PRICE_INPUT_PER_TOKEN = 3.0 / 1_000_000  # $3 per 1M input tokens
PRICE_OUTPUT_PER_TOKEN = 15.0 / 1_000_000  # $15 per 1M output tokens


def compute_cache_key(cheatsheet: str, equation_1: str, equation_2: str) -> str:
    """Compute a deterministic cache key for a (cheatsheet, eq1, eq2) triple."""
    blob = f"{cheatsheet}\x00{equation_1}\x00{equation_2}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class EvalCache:
    """Persistent cache for LLM evaluation results.

    Stores results keyed by sha256(cheatsheet + equation pair) so that
    repeated evaluations with the same cheatsheet skip API calls.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load existing cache from disk, or start fresh."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if data.get("version") != CACHE_VERSION:
                return  # version mismatch, start fresh
            self._entries = data.get("entries", {})
        except (json.JSONDecodeError, KeyError):
            return  # corrupt file, start fresh

    def get(self, key: str) -> dict | None:
        """Retrieve a cached entry, or None on miss."""
        return self._entries.get(key)

    def put(self, key: str, entry: dict) -> None:
        """Store an entry in the cache (in memory)."""
        self._entries[key] = entry

    def get_stats(self) -> dict:
        """Compute aggregate token usage stats."""
        total_in = sum(e.get("input_tokens", 0) for e in self._entries.values())
        total_out = sum(e.get("output_tokens", 0) for e in self._entries.values())
        cost = total_in * PRICE_INPUT_PER_TOKEN + total_out * PRICE_OUTPUT_PER_TOKEN
        return {
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cost_estimate_usd": round(cost, 6),
        }

    def save(self) -> None:
        """Persist cache to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": CACHE_VERSION,
            "entries": self._entries,
            "stats": self.get_stats(),
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
    cache: EvalCache | None = None,
    client: Any | None = None,
) -> dict:
    """Evaluate problems using the Anthropic API.

    Args:
        problems: List of problem dicts with equation_1, equation_2, answer.
        cheatsheet: The cheatsheet text to include in prompts.
        model: Anthropic model identifier.
        max_problems: Limit number of problems evaluated.
        cache: Optional EvalCache instance. Pass None to skip caching.
        client: Optional pre-configured Anthropic client (for testing).
    """
    if client is None:
        try:
            import anthropic  # noqa: F811
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
    cache_hits = 0
    cache_misses = 0
    run_input_tokens = 0
    run_output_tokens = 0
    results_log: list[dict] = []

    for i, prob in enumerate(problems):
        cache_key = compute_cache_key(cheatsheet, prob["equation_1"], prob["equation_2"])

        # Check cache first
        cached_entry = cache.get(cache_key) if cache is not None else None
        if cached_entry is not None:
            cache_hits += 1
            text = cached_entry["response_text"]
            predicted = cached_entry["predicted"]
            source = "CACHE"
        else:
            cache_misses += 1
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
                text = response.content[0].text
                predicted = parse_verdict(text)

                # Track token usage
                in_tok = response.usage.input_tokens
                out_tok = response.usage.output_tokens
                run_input_tokens += in_tok
                run_output_tokens += out_tok

                # Store in cache
                if cache is not None:
                    cache.put(
                        cache_key,
                        {
                            "predicted": predicted,
                            "response_text": text,
                            "model": model,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                        },
                    )
            except Exception as e:
                print(f"  Error on problem {prob['id']}: {e}")
                errors += 1
                continue

            source = "API"

            # Rate limiting (only for API calls)
            time.sleep(0.5)

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
            f"actual={actual} pred={predicted} ({source})"
        )

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
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "token_usage": {
            "input_tokens": run_input_tokens,
            "output_tokens": run_output_tokens,
        },
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
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache, force all API calls")
    parser.add_argument(
        "--cache-file",
        default="experiments/eval_cache.json",
        help="Path to cache file (default: experiments/eval_cache.json)",
    )
    args = parser.parse_args()

    print(f"Loading cheatsheet: {args.cheatsheet}")
    cheatsheet = load_cheatsheet(args.cheatsheet)
    print(f"Cheatsheet size: {len(cheatsheet)} bytes")

    # Set up cache
    cache: EvalCache | None = None
    if not args.no_cache:
        cache = EvalCache(args.cache_file)
        print(f"Cache: {args.cache_file}")
    else:
        print("Cache: disabled (--no-cache)")

    print(f"\nGenerating {args.sample} problems...")
    n_hard = max(1, args.sample // 6)
    n_normal = args.sample - n_hard
    problems = generate_problems(n_normal, n_hard)
    print(f"Generated {len(problems)} problems")

    print(f"\nEvaluating with {args.model}...")
    result = evaluate_with_llm(problems, cheatsheet, args.model, args.sample, cache=cache)

    print(f"\n{'=' * 50}")
    print(f"RESULTS ({args.model})")
    print(f"{'=' * 50}")
    print(f"Accuracy: {result['accuracy']:.2%} ({result['tp'] + result['tn']}/{result['total']})")
    print(f"  TP={result['tp']} FP={result['fp']} TN={result['tn']} FN={result['fn']}")
    print(f"  Errors (unparseable): {result['errors']}")

    # Cache hit reporting
    print(f"  Cache: {result['cache_hits']} hits, {result['cache_misses']} misses")

    # Token usage summary
    tok = result["token_usage"]
    if tok["input_tokens"] > 0 or tok["output_tokens"] > 0:
        cost = (
            tok["input_tokens"] * PRICE_INPUT_PER_TOKEN
            + tok["output_tokens"] * PRICE_OUTPUT_PER_TOKEN
        )
        print(
            f"  Tokens (this run): {tok['input_tokens']} in + {tok['output_tokens']} out "
            f"(~${cost:.4f})"
        )

    # Save cache
    if cache is not None:
        cache.save()
        stats = cache.get_stats()
        print(
            f"  Tokens (all time): {stats['total_input_tokens']} in + "
            f"{stats['total_output_tokens']} out (~${stats['total_cost_estimate_usd']:.4f})"
        )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
