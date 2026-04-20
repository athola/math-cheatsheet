"""Tests for scripts/demo.py — unified magma demo script.

Feature: Demonstrate magma properties and counterexamples
    As a developer exploring the codebase
    I want a single entry point for interactive magma demos
    So that I can quickly explore properties and counterexamples without hunting for scripts
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tla" / "python"))

from demo import count_properties, find_counterexamples  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# count_properties
# ──────────────────────────────────────────────────────────────────────────────


class TestCountProperties:
    """Feature: count_properties tallies algebraic properties across all magmas of a size."""

    @pytest.mark.unit
    def test_returns_dict_with_required_keys(self):
        """
        Scenario: count_properties returns a structured dict
        Given size=2
        When count_properties(2) is called
        Then the result has keys: total, associative, commutative, identity, idempotent
        """
        result = count_properties(2)
        assert {"total", "associative", "commutative", "identity", "idempotent"} <= result.keys()

    @pytest.mark.unit
    def test_total_is_correct_for_size_2(self):
        """
        Scenario: size-2 magmas total 2^(2^2) = 16
        Given size=2
        When count_properties is called
        Then total == 16
        """
        assert count_properties(2)["total"] == 16

    @pytest.mark.unit
    def test_total_is_correct_for_size_3(self):
        """
        Scenario: size-3 magmas total 3^(3^2) = 19683
        Given size=3
        When count_properties is called
        Then total == 19683
        """
        assert count_properties(3)["total"] == 19683

    @pytest.mark.unit
    def test_all_counts_non_negative(self):
        """
        Scenario: All property counts are non-negative integers
        Given size=2
        When count_properties is called
        Then every count is >= 0
        """
        result = count_properties(2)
        for key, val in result.items():
            assert isinstance(val, int), f"{key} should be int"
            assert val >= 0, f"{key} should be non-negative"

    @pytest.mark.unit
    def test_property_counts_do_not_exceed_total(self):
        """
        Scenario: No property count exceeds the total magma count
        Given size=2
        When count_properties is called
        Then every property count <= total
        """
        result = count_properties(2)
        total = result["total"]
        for key in ("associative", "commutative", "identity", "idempotent"):
            assert result[key] <= total, f"{key}={result[key]} exceeds total={total}"

    @pytest.mark.unit
    def test_size_returns_size_field(self):
        """
        Scenario: Returned dict includes the size queried
        Given size=2
        When count_properties is called
        Then result['size'] == 2
        """
        assert count_properties(2)["size"] == 2


# ──────────────────────────────────────────────────────────────────────────────
# find_counterexamples
# ──────────────────────────────────────────────────────────────────────────────


class TestFindCounterexamples:
    """Feature: find_counterexamples locates magmas that witness classic non-implications."""

    @pytest.mark.unit
    def test_returns_dict_with_required_keys(self):
        """
        Scenario: find_counterexamples returns the three classic non-implication groups
        Given size=3
        When find_counterexamples(3) is called
        Then keys comm_not_assoc, assoc_not_comm, idemp_not_comm are present
        """
        result = find_counterexamples(3)
        assert {"comm_not_assoc", "assoc_not_comm", "idemp_not_comm"} <= result.keys()

    @pytest.mark.unit
    def test_comm_not_assoc_witnesses_exist(self):
        """
        Scenario: There exist commutative-but-not-associative magmas of size 3
        Given size=3
        When find_counterexamples is called
        Then comm_not_assoc is non-empty and each element is commutative but not associative
        """
        result = find_counterexamples(3)
        witnesses = result["comm_not_assoc"]
        assert len(witnesses) > 0
        for m in witnesses:
            assert m.is_commutative()
            assert not m.is_associative()

    @pytest.mark.unit
    def test_assoc_not_comm_witnesses_exist(self):
        """
        Scenario: There exist associative-but-not-commutative magmas of size 3
        Given size=3
        When find_counterexamples is called
        Then assoc_not_comm is non-empty and each element is associative but not commutative
        """
        result = find_counterexamples(3)
        witnesses = result["assoc_not_comm"]
        assert len(witnesses) > 0
        for m in witnesses:
            assert m.is_associative()
            assert not m.is_commutative()

    @pytest.mark.unit
    def test_idemp_not_comm_witnesses_exist(self):
        """
        Scenario: There exist idempotent-but-not-commutative magmas of size 3
        Given size=3
        When find_counterexamples is called
        Then idemp_not_comm is non-empty and each element is idempotent but not commutative
        """
        result = find_counterexamples(3)
        witnesses = result["idemp_not_comm"]
        assert len(witnesses) > 0
        for m in witnesses:
            assert m.is_idempotent()
            assert not m.is_commutative()

    @pytest.mark.unit
    def test_size_2_result_is_a_list(self):
        """
        Scenario: find_counterexamples works for size=2
        Given size=2
        When find_counterexamples is called
        Then comm_not_assoc is a list (may be empty or non-empty)
        """
        result = find_counterexamples(2)
        assert isinstance(result["comm_not_assoc"], list)
