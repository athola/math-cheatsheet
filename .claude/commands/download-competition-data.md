---
description: Download ETP equations and competition data files
---

# Download Competition Data

Download the required data files for the SAIR Math Distillation Challenge.

## Instructions

### 1. ETP Equations (always available)
```bash
curl -sL "https://raw.githubusercontent.com/teorth/equational_theories/main/data/equations.txt" > research/data/etp/equations.txt
echo "Downloaded $(wc -l < research/data/etp/equations.txt) equations"
```

### 2. Raw Implications Matrix (58MB, required for evaluation)
The implications CSV must be downloaded manually from the ETP website or copied from a local source:
- Source: https://teorth.github.io/equational_theories/implications/ → "Download raw implications table"
- Save to: `research/data/etp/implications.csv`
- Also check: `/mnt/c/Users/alext/Downloads/export_raw_implications_3_19_2026.csv`

```bash
if [ ! -f research/data/etp/implications.csv ]; then
    if [ -f /mnt/c/Users/alext/Downloads/export_raw_implications_3_19_2026.csv ]; then
        cp /mnt/c/Users/alext/Downloads/export_raw_implications_3_19_2026.csv research/data/etp/implications.csv
        echo "Copied from Downloads"
    else
        echo "ERROR: Download implications.csv manually from the ETP website"
    fi
fi
```

### 3. Competition Problems (gated, requires HuggingFace auth)
The official normal.jsonl and hard.jsonl require HuggingFace authentication:
```bash
# If you have huggingface-cli with auth:
# huggingface-cli download SAIR-Foundation/STEP normal.jsonl hard.jsonl --local-dir research/data/etp/competition/

# Otherwise, generate synthetic problems from the implication matrix:
PYTHONPATH=src venv/bin/python -c "
from llm_evaluator import generate_problems
import json
problems = generate_problems(1000, 200)
with open('research/data/etp/competition/synthetic_problems.json', 'w') as f:
    json.dump(problems, f, indent=2)
print(f'Generated {len(problems)} problems')
"
```

Verify all files exist and report status.
