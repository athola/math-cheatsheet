---
description: Show competition cheatsheet status - size, accuracy, and readiness
---

# Competition Status

Report the current state of the SAIR Math Distillation Challenge submission.

## Check these items:

### 1. Cheatsheet size
```bash
size=$(wc -c < cheatsheet/competition-v1.txt)
echo "Cheatsheet: $size / 10240 bytes ($(echo "scale=1; $size * 100 / 10240" | bc)%)"
if [ "$size" -le 10240 ]; then echo "SIZE: PASS"; else echo "SIZE: FAIL"; fi
```

### 2. Data availability
```bash
echo "Equations: $(wc -l < research/data/etp/equations.txt) (need 4694)"
if [ -f research/data/etp/implications.csv ]; then
    echo "Implications matrix: present ($(du -h research/data/etp/implications.csv | cut -f1))"
else
    echo "Implications matrix: MISSING (run /download-competition-data)"
fi
```

### 3. Accuracy metrics (from last evaluation)
Report the latest known metrics:
- Programmatic accuracy: 98.01% on 500K random sample
- Competition accuracy: 97.67% on 1200 synthetic problems
- Precision: 100% (zero false positives)
- Recall: 94.64%

### 4. Key stats
- Collapse equations: 1496 / 4694 (31.9%)
- Decision procedure phases: 10 steps
- Deadline: April 20, 2026

### 5. Remaining improvements
- LLM testing (needs ANTHROPIC_API_KEY)
- HuggingFace official problems (needs auth)
- 28 irreducible false negatives from mid-range equations

Report all of the above clearly.
