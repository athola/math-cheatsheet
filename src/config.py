"""Shared configuration constants for the math-cheatsheet project."""

from __future__ import annotations

# Competition constraint: cheatsheet byte limit
MAX_CHEATSHEET_BYTES = 10_240

# LLM evaluation cache versioning — bump when cache schema changes
EVAL_CACHE_VERSION = 1

# Approximate pricing for cost estimates (USD per token, Claude Sonnet pricing)
PRICE_INPUT_PER_TOKEN = 3.0 / 1_000_000  # $3 per 1M input tokens
PRICE_OUTPUT_PER_TOKEN = 15.0 / 1_000_000  # $15 per 1M output tokens
