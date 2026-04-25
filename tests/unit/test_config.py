"""Tests for src/config.py — shared configuration constants.

Feature: Centralized project configuration constants
    As a developer working across multiple modules
    I want shared constants in one place
    So that changing a value (e.g. byte limit) propagates everywhere automatically
"""

from __future__ import annotations

import pytest

from config import (
    EVAL_CACHE_VERSION,
    MAX_CHEATSHEET_BYTES,
    PRICE_INPUT_PER_TOKEN,
    PRICE_OUTPUT_PER_TOKEN,
)


class TestCheatsheetConstants:
    """Feature: Cheatsheet competition constraints are defined centrally."""

    @pytest.mark.unit
    def test_max_cheatsheet_bytes_is_importable(self):
        """
        Scenario: MAX_CHEATSHEET_BYTES is accessible from config module
        Given the config module
        When I import MAX_CHEATSHEET_BYTES
        Then it is an integer
        """
        assert isinstance(MAX_CHEATSHEET_BYTES, int)

    @pytest.mark.unit
    def test_max_cheatsheet_bytes_value(self):
        """
        Scenario: Byte limit matches the competition specification (10 KiB)
        Given the config module
        When I read MAX_CHEATSHEET_BYTES
        Then it equals 10240
        """
        assert MAX_CHEATSHEET_BYTES == 10_240

    @pytest.mark.unit
    def test_max_cheatsheet_bytes_is_positive(self):
        """
        Scenario: Byte limit is a positive value
        Given the config module
        When I read MAX_CHEATSHEET_BYTES
        Then it is strictly greater than zero
        """
        assert MAX_CHEATSHEET_BYTES > 0


class TestLLMCacheConstants:
    """Feature: LLM evaluation cache configuration is defined centrally."""

    @pytest.mark.unit
    def test_eval_cache_version_is_importable(self):
        """
        Scenario: EVAL_CACHE_VERSION is accessible from config module
        Given the config module
        When I import EVAL_CACHE_VERSION
        Then it is an integer
        """
        assert isinstance(EVAL_CACHE_VERSION, int)

    @pytest.mark.unit
    def test_eval_cache_version_is_positive(self):
        """
        Scenario: Cache version is a positive integer
        Given the config module
        When I read EVAL_CACHE_VERSION
        Then it is >= 1
        """
        assert EVAL_CACHE_VERSION >= 1


class TestPricingConstants:
    """Feature: LLM token pricing constants are defined centrally."""

    @pytest.mark.unit
    def test_price_input_per_token_is_float(self):
        """
        Scenario: Input token price is a float
        Given the config module
        When I import PRICE_INPUT_PER_TOKEN
        Then it is a positive float
        """
        assert isinstance(PRICE_INPUT_PER_TOKEN, float)
        assert PRICE_INPUT_PER_TOKEN > 0

    @pytest.mark.unit
    def test_price_output_per_token_is_float(self):
        """
        Scenario: Output token price is a positive float
        Given the config module
        When I import PRICE_OUTPUT_PER_TOKEN
        Then it is greater than zero
        """
        assert isinstance(PRICE_OUTPUT_PER_TOKEN, float)
        assert PRICE_OUTPUT_PER_TOKEN > 0

    @pytest.mark.unit
    def test_output_price_exceeds_input_price(self):
        """
        Scenario: Output tokens cost more than input tokens (Claude pricing model)
        Given the config module
        When I compare PRICE_OUTPUT_PER_TOKEN and PRICE_INPUT_PER_TOKEN
        Then output price is greater than input price
        """
        assert PRICE_OUTPUT_PER_TOKEN > PRICE_INPUT_PER_TOKEN

    @pytest.mark.unit
    def test_input_price_matches_expected_rate(self):
        """
        Scenario: Input price matches $3 per 1M tokens
        Given the config module
        When I read PRICE_INPUT_PER_TOKEN
        Then it equals 3e-6
        """
        assert abs(PRICE_INPUT_PER_TOKEN - 3e-6) < 1e-12

    @pytest.mark.unit
    def test_output_price_matches_expected_rate(self):
        """
        Scenario: Output price matches $15 per 1M tokens
        Given the config module
        When I read PRICE_OUTPUT_PER_TOKEN
        Then it equals 15e-6
        """
        assert abs(PRICE_OUTPUT_PER_TOKEN - 15e-6) < 1e-12
