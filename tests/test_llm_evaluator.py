"""Tests for llm_evaluator module.

Tests the pure functions (parse_verdict, load_cheatsheet) without
requiring API keys or network access.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import llm_evaluator
from llm_evaluator import (
    EvalCache,
    compute_cache_key,
    load_cheatsheet,
    parse_verdict,
)


class TestParseVerdict:
    """Test verdict extraction from LLM response text."""

    def test_true_verdict(self):
        response = "VERDICT: TRUE\nREASONING: Self-implication."
        assert parse_verdict(response) is True

    def test_false_verdict(self):
        response = "VERDICT: FALSE\nREASONING: Counterexample exists."
        assert parse_verdict(response) is False

    def test_case_insensitive(self):
        assert parse_verdict("verdict: true\nreasoning: ...") is True
        assert parse_verdict("Verdict: False\nReasoning: ...") is False

    def test_verdict_with_extra_whitespace(self):
        assert parse_verdict("VERDICT:   TRUE  \nREASONING: ...") is True
        assert parse_verdict("VERDICT:  FALSE  \nREASONING: ...") is False

    def test_verdict_with_surrounding_text(self):
        response = (
            "Let me analyze this.\nVERDICT: TRUE\nREASONING: Tautology target.\nPROOF: Trivial.\n"
        )
        assert parse_verdict(response) is True

    def test_no_verdict_returns_none(self):
        assert parse_verdict("No verdict here.") is None

    def test_empty_string_returns_none(self):
        assert parse_verdict("") is None

    def test_verdict_without_value_returns_none(self):
        assert parse_verdict("VERDICT:\nREASONING: ...") is None

    def test_verdict_with_unexpected_value_returns_none(self):
        assert parse_verdict("VERDICT: MAYBE\nREASONING: ...") is None

    def test_multiple_verdict_lines_returns_first(self):
        response = "VERDICT: TRUE\nVERDICT: FALSE\n"
        assert parse_verdict(response) is True


class TestEvaluateWithLLMEnvironmentErrors:
    """Library-level errors must raise, not call sys.exit (#51).

    ``evaluate_with_llm`` lived in a library module but used ``sys.exit(1)``
    when the SDK was unavailable or the API key was missing. That makes
    the function unusable from a notebook or test that expects exceptions
    to surface; it should raise ``EnvironmentError`` and let the CLI
    layer translate to an exit code.
    """

    def _make_problems(self):
        return [
            {
                "id": 1,
                "equation_1": "x * y = y * x",
                "equation_2": "x * x = x",
                "equation_1_id": 10,
                "equation_2_id": 20,
                "answer": True,
                "difficulty": "normal",
            },
        ]

    def test_missing_api_key_raises_environment_error(self, monkeypatch):
        """Missing ANTHROPIC_API_KEY must raise EnvironmentError (not sys.exit)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Force the path that consults the env (no client passed).
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            llm_evaluator.evaluate_with_llm(self._make_problems(), "cheatsheet", client=None)

    def test_placeholder_api_key_raises_environment_error(self, monkeypatch):
        """A literal-placeholder ``your_*`` key must be rejected too."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "your_key_here")
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            llm_evaluator.evaluate_with_llm(self._make_problems(), "cheatsheet", client=None)

    def test_missing_anthropic_module_raises_environment_error(self, monkeypatch):
        """Without the anthropic SDK installed, library users get an exception."""
        # Set a valid-looking key so we get past the env-var check; then patch
        # the SDK to None so the import fallback fires.
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(llm_evaluator, "anthropic", None)
        with pytest.raises(EnvironmentError, match="anthropic"):
            llm_evaluator.evaluate_with_llm(self._make_problems(), "cheatsheet", client=None)


class TestParseVerdictWarnings:
    """Pin warning emission for the ambiguous-verdict failure mode (#52/M5).

    ``parse_verdict`` returns ``None`` for two distinct cases:
    (a) the response has no VERDICT line at all (the LLM did not follow
        the format),
    (b) a VERDICT line is present but its value is neither TRUE nor FALSE
        (the LLM produced an unparseable verdict — an LLM compliance
        failure that should be visible in logs).
    Case (b) must emit ``logger.warning`` so silent compliance failures
    can be detected; case (a) must not (it is the non-VERDICT side of a
    response, e.g. cheatsheet text being parsed).
    """

    def test_no_verdict_line_does_not_warn(self, caplog):
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            assert parse_verdict("Some explanatory text without the keyword.") is None
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings == []

    def test_unparseable_verdict_value_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            assert parse_verdict("VERDICT: MAYBE\nREASONING: ambiguous") is None
        assert any(
            record.levelno == logging.WARNING and "verdict" in record.message.lower()
            for record in caplog.records
        ), f"Expected WARNING about unparseable verdict; got: {caplog.text}"

    def test_empty_verdict_value_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            assert parse_verdict("VERDICT:\nREASONING: blank") is None
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) >= 1

    def test_valid_verdict_does_not_warn(self, caplog):
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            assert parse_verdict("VERDICT: TRUE\nREASONING: yes") is True
            assert parse_verdict("VERDICT: FALSE\nREASONING: no") is False
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings == []


class TestLoadCheatsheet:
    def test_loads_file(self, tmp_path: Path):
        cheatsheet = tmp_path / "test.txt"
        cheatsheet.write_text("cheatsheet content", encoding="utf-8")
        result = load_cheatsheet(str(cheatsheet))
        assert result == "cheatsheet content"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_cheatsheet("/nonexistent/path.txt")


class TestComputeCacheKey:
    """Test cache key generation from cheatsheet + equation pair."""

    def test_deterministic(self):
        """Same inputs always produce the same key."""
        key1 = compute_cache_key("cheatsheet", "eq1", "eq2")
        key2 = compute_cache_key("cheatsheet", "eq1", "eq2")
        assert key1 == key2

    def test_different_inputs_different_keys(self):
        """Different inputs produce different keys."""
        key1 = compute_cache_key("cheatsheet", "eq1", "eq2")
        key2 = compute_cache_key("cheatsheet", "eq1", "eq3")
        assert key1 != key2

    def test_key_is_hex_sha256(self):
        """Key should be a valid 64-char hex string (sha256)."""
        key = compute_cache_key("cs", "a", "b")
        assert len(key) == 64
        int(key, 16)  # should not raise

    def test_cheatsheet_change_changes_key(self):
        """Changing cheatsheet content changes the key."""
        key1 = compute_cache_key("v1", "eq1", "eq2")
        key2 = compute_cache_key("v2", "eq1", "eq2")
        assert key1 != key2

    def test_order_matters(self):
        """eq1/eq2 order matters (implication is directional)."""
        key1 = compute_cache_key("cs", "a", "b")
        key2 = compute_cache_key("cs", "b", "a")
        assert key1 != key2


class TestEvalCache:
    """Test the evaluation cache for persistence and retrieval."""

    def test_empty_cache(self, tmp_path: Path):
        """New cache has no entries."""
        cache = EvalCache(tmp_path / "cache.json")
        assert cache.get("nonexistent") is None

    def test_put_and_get(self, tmp_path: Path):
        """Can store and retrieve an entry."""
        cache = EvalCache(tmp_path / "cache.json")
        entry = {
            "predicted": True,
            "response_text": "VERDICT: TRUE",
            "model": "test-model",
            "timestamp": "2026-04-09T00:00:00",
            "input_tokens": 100,
            "output_tokens": 50,
        }
        cache.put("abc123", entry)
        result = cache.get("abc123")
        assert result is not None
        assert result["predicted"] is True
        assert result["input_tokens"] == 100

    def test_persistence_across_instances(self, tmp_path: Path):
        """Cache survives being saved and reloaded."""
        cache_path = tmp_path / "cache.json"
        cache1 = EvalCache(cache_path)
        cache1.put(
            "key1",
            {
                "predicted": False,
                "response_text": "VERDICT: FALSE",
                "model": "m",
                "timestamp": "t",
                "input_tokens": 10,
                "output_tokens": 5,
            },
        )
        cache1.save()

        # Load a fresh instance
        cache2 = EvalCache(cache_path)
        result = cache2.get("key1")
        assert result is not None
        assert result["predicted"] is False

    def test_stats_tracking(self, tmp_path: Path):
        """Stats accumulate token counts."""
        cache = EvalCache(tmp_path / "cache.json")
        cache.put(
            "k1",
            {
                "predicted": True,
                "response_text": "r",
                "model": "m",
                "timestamp": "t",
                "input_tokens": 100,
                "output_tokens": 50,
            },
        )
        cache.put(
            "k2",
            {
                "predicted": False,
                "response_text": "r",
                "model": "m",
                "timestamp": "t",
                "input_tokens": 200,
                "output_tokens": 80,
            },
        )
        stats = cache.get_stats()
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 130

    def test_cost_estimate(self, tmp_path: Path):
        """Stats include a cost estimate."""
        cache = EvalCache(tmp_path / "cache.json")
        cache.put(
            "k1",
            {
                "predicted": True,
                "response_text": "r",
                "model": "m",
                "timestamp": "t",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        )
        stats = cache.get_stats()
        assert "total_cost_estimate_usd" in stats
        assert stats["total_cost_estimate_usd"] > 0

    def test_save_creates_file(self, tmp_path: Path):
        """save() writes a valid JSON file."""
        cache_path = tmp_path / "subdir" / "cache.json"
        cache = EvalCache(cache_path)
        cache.put(
            "k",
            {
                "predicted": True,
                "response_text": "r",
                "model": "m",
                "timestamp": "t",
                "input_tokens": 1,
                "output_tokens": 1,
            },
        )
        cache.save()
        assert cache_path.exists()
        data = json.loads(cache_path.read_text())
        assert data["version"] == 1
        assert "k" in data["entries"]
        assert "stats" in data

    def test_cache_version_mismatch_resets(self, tmp_path: Path, caplog):
        """If cache file has wrong version, start fresh AND warn (regression #50/H8).

        Pre-revision tests only checked ``cache.get("old") is None`` — that
        passes even if the ``logger.warning`` line is removed. caplog pins
        the warning emission so silent reset can no longer regress.
        """
        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps({"version": 99, "entries": {"old": {}}}))
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            cache = EvalCache(cache_path)
        assert cache.get("old") is None
        # Warning must mention the version so users know why the cache was discarded.
        assert any(
            record.levelno == logging.WARNING and "version" in record.message.lower()
            for record in caplog.records
        ), f"Expected WARNING about version mismatch; got: {caplog.text}"

    def test_corrupt_file_handled(self, tmp_path: Path, caplog):
        """Corrupt JSON file doesn't crash, starts fresh AND warns (regression #50/H8)."""
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("not valid json{{{")
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            cache = EvalCache(cache_path)
        assert cache.get("any") is None
        # Warning must mention "corrupt" so root cause is visible in logs.
        assert any(
            record.levelno == logging.WARNING and "corrupt" in record.message.lower()
            for record in caplog.records
        ), f"Expected WARNING about corrupt cache; got: {caplog.text}"

    def test_missing_entries_key_handled(self, tmp_path: Path, caplog):
        """Cache file missing the 'entries' key warns and resets."""
        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps({"version": 1}))  # no 'entries'
        with caplog.at_level(logging.WARNING, logger="llm_evaluator"):
            cache = EvalCache(cache_path)
        assert cache.get("any") is None
        assert any(
            record.levelno == logging.WARNING and "entries" in record.message.lower()
            for record in caplog.records
        ), f"Expected WARNING about missing entries; got: {caplog.text}"


class TestEvaluateWithLLMCaching:
    """Test that evaluate_with_llm integrates with cache."""

    def _make_mock_response(self, text: str, input_tokens: int = 100, output_tokens: int = 50):
        """Create a mock Anthropic API response."""
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=text)]
        mock_resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
        return mock_resp

    def _make_problems(self):
        return [
            {
                "id": 1,
                "equation_1": "x * y = y * x",
                "equation_2": "x * x = x",
                "equation_1_id": 10,
                "equation_2_id": 20,
                "answer": True,
                "difficulty": "normal",
            },
            {
                "id": 2,
                "equation_1": "x * (y * z) = (x * y) * z",
                "equation_2": "x * y = x",
                "equation_1_id": 30,
                "equation_2_id": 40,
                "answer": False,
                "difficulty": "normal",
            },
        ]

    @patch("llm_evaluator.time.sleep")
    def test_cache_miss_calls_api(self, mock_sleep, tmp_path):
        """On cache miss, API is called and result is cached."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "VERDICT: TRUE\nREASONING: trivial"
        )

        cache = EvalCache(tmp_path / "cache.json")
        problems = self._make_problems()[:1]

        result = llm_evaluator.evaluate_with_llm(
            problems, "cheatsheet", cache=cache, client=mock_client
        )

        assert mock_client.messages.create.call_count == 1
        assert result["total"] == 1

    def test_cache_hit_skips_api(self, tmp_path):
        """On cache hit, API is NOT called."""
        problems = self._make_problems()[:1]
        cheatsheet = "cheatsheet"
        cache = EvalCache(tmp_path / "cache.json")

        # Pre-populate cache
        key = compute_cache_key(cheatsheet, problems[0]["equation_1"], problems[0]["equation_2"])
        cache.put(
            key,
            {
                "predicted": True,
                "response_text": "VERDICT: TRUE\nREASONING: cached",
                "model": "claude-sonnet-4-20250514",
                "timestamp": "2026-04-09T00:00:00",
                "input_tokens": 100,
                "output_tokens": 50,
            },
        )

        mock_client = MagicMock()
        result = llm_evaluator.evaluate_with_llm(
            problems, cheatsheet, cache=cache, client=mock_client
        )

        assert mock_client.messages.create.call_count == 0
        assert result["total"] == 1
        assert result["cache_hits"] == 1

    @patch("llm_evaluator.time.sleep")
    def test_no_cache_flag_bypasses(self, mock_sleep):
        """When cache=None, every problem hits the API."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "VERDICT: FALSE\nREASONING: counter"
        )

        problems = self._make_problems()

        result = llm_evaluator.evaluate_with_llm(
            problems, "cheatsheet", cache=None, client=mock_client
        )

        assert mock_client.messages.create.call_count == 2
        assert result["cache_hits"] == 0

    @patch("llm_evaluator.time.sleep")
    def test_mixed_hits_and_misses(self, mock_sleep, tmp_path):
        """Some problems cached, others need API calls."""
        problems = self._make_problems()
        cheatsheet = "cheatsheet"
        cache = EvalCache(tmp_path / "cache.json")

        # Cache only the first problem
        key = compute_cache_key(cheatsheet, problems[0]["equation_1"], problems[0]["equation_2"])
        cache.put(
            key,
            {
                "predicted": True,
                "response_text": "VERDICT: TRUE\nREASONING: cached",
                "model": "claude-sonnet-4-20250514",
                "timestamp": "2026-04-09T00:00:00",
                "input_tokens": 100,
                "output_tokens": 50,
            },
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "VERDICT: FALSE\nREASONING: counter"
        )

        result = llm_evaluator.evaluate_with_llm(
            problems, cheatsheet, cache=cache, client=mock_client
        )

        # Only 1 API call (second problem)
        assert mock_client.messages.create.call_count == 1
        assert result["cache_hits"] == 1
        assert result["cache_misses"] == 1
        assert result["total"] == 2

    @patch("llm_evaluator.time.sleep")
    def test_token_usage_in_result(self, mock_sleep, tmp_path):
        """Result includes token usage summary."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "VERDICT: TRUE\nREASONING: ok", input_tokens=150, output_tokens=75
        )

        problems = self._make_problems()[:1]
        cache = EvalCache(tmp_path / "cache.json")

        result = llm_evaluator.evaluate_with_llm(
            problems, "cheatsheet", cache=cache, client=mock_client
        )

        assert result["token_usage"]["input_tokens"] == 150
        assert result["token_usage"]["output_tokens"] == 75


class TestEvaluateWithLLMAPIErrors:
    """Regression #43/I6: API errors must increment ``errors`` and not crash."""

    def _make_problems(self):
        return [
            {
                "id": 1,
                "equation_1": "x * y = y * x",
                "equation_2": "x * x = x",
                "equation_1_id": 10,
                "equation_2_id": 20,
                "answer": True,
                "difficulty": "normal",
            },
        ]

    @patch("llm_evaluator.time.sleep")
    def test_api_exception_counts_as_error_and_continues(
        self, mock_sleep: MagicMock, tmp_path: Path
    ):
        """A raised Anthropic SDK error on one problem doesn't break the loop."""
        # Use a mock exception class whose __name__ matches an Anthropic SDK error
        # so that the exception handler classifies it as a recoverable API error.
        _MockAPIError = type("APIStatusError", (Exception,), {})

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = _MockAPIError("simulated upstream 503")

        cache = EvalCache(tmp_path / "cache.json")
        problems = self._make_problems()

        result = llm_evaluator.evaluate_with_llm(
            problems, "cheatsheet", cache=cache, client=mock_client
        )

        # One problem, one API call attempted, exception caught → error tally.
        assert mock_client.messages.create.call_count == 1
        assert result["errors"] >= 1
        # On exception we skip classification, so tp+fp+tn+fn may be zero.
        assert result["tp"] + result["fp"] + result["tn"] + result["fn"] == 0

    @patch("llm_evaluator.time.sleep")
    def test_api_exception_does_not_poison_cache(self, mock_sleep: MagicMock, tmp_path: Path):
        """Failed API calls must not write a partial/garbage entry to the cache."""
        _MockAPIError = type("APIConnectionError", (Exception,), {})

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = _MockAPIError("boom")

        cache_path = tmp_path / "cache.json"
        cache = EvalCache(cache_path)

        llm_evaluator.evaluate_with_llm(
            self._make_problems(), "cheatsheet", cache=cache, client=mock_client
        )
        cache.save()

        reloaded = EvalCache(cache_path)
        assert reloaded._entries == {}, "A failed API call leaked an entry into the persisted cache"
