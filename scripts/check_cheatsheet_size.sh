#!/usr/bin/env bash
# Pre-commit hook: verify all cheatsheet files are within 10KB competition limit
set -euo pipefail

MAX_BYTES=10240
failed=0

for f in cheatsheet/*.txt; do
    [ -f "$f" ] || continue
    bytes=$(wc -c < "$f")
    if [ "$bytes" -gt "$MAX_BYTES" ]; then
        echo "FAIL: $f is $bytes bytes (limit $MAX_BYTES)"
        failed=1
    fi
done

if [ "$failed" -eq 1 ]; then
    exit 1
fi
echo "All cheatsheets within 10KB limit"
