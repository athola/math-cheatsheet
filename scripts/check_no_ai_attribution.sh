#!/usr/bin/env bash
# Pre-commit hook: block AI co-authored-by lines in commit messages.
# Runs at the commit-msg stage, where pre-commit passes the path of the
# in-progress commit message file as $1 (git log -1 HEAD would inspect
# the PREVIOUS commit — the new one does not exist yet at this stage).
set -euo pipefail

MSG_FILE="${1:?usage: check_no_ai_attribution.sh <commit-msg-file>}"

if grep -iqE "Co-Authored-By:.*(Claude|Opus|Sonnet|Haiku|Anthropic|GPT|OpenAI|Copilot)" "$MSG_FILE"; then
    echo "ERROR: Commit contains AI Co-Authored-By line. Remove it."
    exit 1
fi
