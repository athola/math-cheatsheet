#!/usr/bin/env bash
# Pre-commit hook: block AI co-authored-by lines in commit messages
set -euo pipefail

if git log --format="%b" -1 HEAD 2>/dev/null | grep -iqE "Co-Authored-By:.*(Claude|Opus|Sonnet|Haiku|Anthropic|GPT|OpenAI|Copilot)"; then
    echo "ERROR: Commit contains AI Co-Authored-By line. Remove it."
    exit 1
fi
