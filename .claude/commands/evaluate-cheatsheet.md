---
description: Evaluate the competition cheatsheet with Claude API on real equation pairs
---

# Evaluate Cheatsheet with LLM

Run a live evaluation of `cheatsheet/competition-v1.txt` by sending equation pairs to Claude and checking if the LLM's verdicts match the ground truth from the ETP implication matrix.

## Instructions

1. Check that `ANTHROPIC_API_KEY` is set (or use the current session's API access)
2. Generate $SAMPLE_SIZE (default: 20) random equation pairs from the 22M implication matrix
3. For each pair, construct the competition prompt with the cheatsheet injected
4. Send to Claude and parse the VERDICT line
5. Compare against ground truth and report accuracy

## Parameters
- Sample size: $ARGUMENTS or 20 (keep small to avoid burning quota)
- Cheatsheet: cheatsheet/competition-v1.txt
- Ground truth: research/data/etp/implications.csv (must exist locally)

## Execution

Run this evaluation by reading the cheatsheet, generating problems from the implication oracle, then using the Anthropic SDK (or the Bash tool with `curl`) to call the API for each problem.

Use `src/llm_evaluator.py` — run it with:
```bash
PYTHONPATH=src ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY venv/bin/python src/llm_evaluator.py --sample $ARGUMENTS
```

If no API key is available, fall back to the **programmatic evaluation** using the cheatsheet harness:
```bash
PYTHONPATH=. uv run python -m src.cheatsheet_harness accuracy cheatsheet/final.txt
```

Report the results clearly showing accuracy, precision, recall, and any interesting failure cases.
