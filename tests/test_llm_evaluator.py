"""Tests for llm_evaluator module.

Tests the pure functions (parse_verdict, load_cheatsheet) without
requiring API keys or network access.
"""

from pathlib import Path

import pytest

from llm_evaluator import load_cheatsheet, parse_verdict


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


class TestLoadCheatsheet:
    def test_loads_file(self, tmp_path: Path):
        cheatsheet = tmp_path / "test.txt"
        cheatsheet.write_text("cheatsheet content", encoding="utf-8")
        result = load_cheatsheet(str(cheatsheet))
        assert result == "cheatsheet content"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_cheatsheet("/nonexistent/path.txt")
