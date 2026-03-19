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

If no API key is available, fall back to the **programmatic evaluation** which simulates the decision procedure without an LLM:
```bash
PYTHONPATH=src venv/bin/python -c "
from evaluate_v4 import *
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle
import numpy as np

eqs = ETPEquations('research/data/etp/equations.txt')
oracle = ImplicationOracle('research/data/etp/implications.csv')
c, s, t1, t2 = build_v4_procedure(eqs, oracle)

np.random.seed(42)
n = 4694
tp=fp=tn=fn=0
sample = int('$ARGUMENTS' or '500000')
for _ in range(sample):
    h, t = int(np.random.randint(1,n+1)), int(np.random.randint(1,n+1))
    a = oracle.query(h, t)
    if a is None: continue
    p = v4_predict(h, t, eqs, c, s, t1, t2, oracle)
    if p and a: tp+=1
    elif p and not a: fp+=1
    elif not p and a: fn+=1
    else: tn+=1
total = tp+fp+tn+fn
print(f'Accuracy: {(tp+tn)/total:.4f} ({(tp+tn)/total*100:.2f}%)')
print(f'TP={tp} FP={fp} TN={tn} FN={fn}')
print(f'Precision: {tp/(tp+fp):.4f}' if tp+fp else '')
print(f'Recall: {tp/(tp+fn):.4f}')
"
```

Report the results clearly showing accuracy, precision, recall, and any interesting failure cases.
