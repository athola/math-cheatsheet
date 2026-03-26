"""Tests for tla/python/explore_magmas.py magma exploration functions.

Tests analyze_magmas(), find_property_correlations(), and
find_implication_counterexamples() against known size-2 magma counts.
"""

import pytest
from explore_magmas import (
    analyze_magmas,
    find_implication_counterexamples,
    find_property_correlations,
)


class TestAnalyzeMagmas:
    """
    Feature: Exhaustive analysis of all magmas of a given size.

    As a magma researcher
    I want to enumerate all magmas and count their properties
    So that I can understand the distribution of algebraic structures.
    """

    @pytest.mark.unit
    def test_size_2_total_count(self):
        """
        Scenario: There are exactly 16 magmas of size 2
        Given size = 2 (binary operations on {0, 1})
        When I analyze all magmas
        Then total should be 16 (2^(2*2) = 16)
        """
        results = analyze_magmas(size=2)
        assert results["total"] == 16

    @pytest.mark.unit
    def test_size_2_property_counts(self):
        """
        Scenario: Property counts for size-2 magmas match known values
        Given all 16 size-2 magmas
        When I count each property
        Then associative count should be 8
        And commutative count should be 8
        And has_identity count should be 4
        And monoids count should be 4
        """
        results = analyze_magmas(size=2)
        assert results["associative"] == 8
        assert results["commutative"] == 8
        assert results["has_identity"] == 4
        assert results["monoids"] == 4

    @pytest.mark.unit
    def test_size_2_result_keys(self):
        """
        Scenario: Result dict contains all expected keys
        Given size = 2
        When I analyze all magmas
        Then the result should include size, total, and all property keys
        """
        results = analyze_magmas(size=2)
        expected_keys = {
            "size",
            "total",
            "associative",
            "commutative",
            "has_identity",
            "monoids",
            "groups",
        }
        assert set(results.keys()) == expected_keys
        assert results["size"] == 2


class TestFindPropertyCorrelations:
    """
    Feature: Find correlations between magma properties.

    As a magma researcher
    I want to know how often property pairs co-occur
    So that I can identify potential implications.
    """

    @pytest.mark.unit
    def test_size_2_returns_nonempty(self):
        """
        Scenario: Correlations for size-2 magmas are non-empty
        Given size = 2
        When I find property correlations
        Then at least one correlation tuple should be returned
        """
        correlations = find_property_correlations(size=2)
        assert len(correlations) > 0

    @pytest.mark.unit
    def test_size_2_correlation_structure(self):
        """
        Scenario: Each correlation is a 4-tuple of (prop1, prop2, both_count, total)
        Given size = 2
        When I find property correlations
        Then each entry should be a 4-tuple with string names and integer counts
        """
        correlations = find_property_correlations(size=2)
        for prop1, prop2, both, total in correlations:
            assert isinstance(prop1, str)
            assert isinstance(prop2, str)
            assert isinstance(both, int)
            assert isinstance(total, int)
            assert total == 16
            assert 0 <= both <= total


class TestFindImplicationCounterexamples:
    """
    Feature: Find counterexamples to property implications.

    As a magma researcher
    I want to find magmas where one property holds but another does not
    So that I can disprove conjectured implications.
    """

    @pytest.mark.unit
    def test_commutative_does_not_imply_associative(self):
        """
        Scenario: Commutativity does not imply associativity
        Given premise = "commutative" and conclusion = "associative"
        When I search for counterexamples
        Then at least one counterexample should be found
        And each counterexample magma should be commutative but not associative
        """
        counterexamples = find_implication_counterexamples("commutative", "associative")
        assert len(counterexamples) > 0
        for ce in counterexamples:
            assert ce.magma.is_commutative()
            assert not ce.magma.is_associative()

    @pytest.mark.unit
    def test_associative_does_not_imply_commutative(self):
        """
        Scenario: Associativity does not imply commutativity
        Given premise = "associative" and conclusion = "commutative"
        When I search for counterexamples
        Then at least one counterexample should be found
        And each counterexample magma should be associative but not commutative
        """
        counterexamples = find_implication_counterexamples("associative", "commutative")
        assert len(counterexamples) > 0
        for ce in counterexamples:
            assert ce.magma.is_associative()
            assert not ce.magma.is_commutative()

    @pytest.mark.unit
    def test_invalid_premise_raises_valueerror(self):
        """
        Scenario: Invalid property name as premise raises ValueError
        Given premise = "nonexistent_property"
        When I call find_implication_counterexamples
        Then a ValueError should be raised with a message about valid properties
        """
        with pytest.raises(ValueError, match="Unknown property 'nonexistent_property'"):
            find_implication_counterexamples("nonexistent_property", "commutative")

    @pytest.mark.unit
    def test_invalid_conclusion_raises_valueerror(self):
        """
        Scenario: Invalid property name as conclusion raises ValueError
        Given conclusion = "bogus"
        When I call find_implication_counterexamples
        Then a ValueError should be raised
        """
        with pytest.raises(ValueError, match="Unknown property 'bogus'"):
            find_implication_counterexamples("commutative", "bogus")

    @pytest.mark.unit
    def test_counterexamples_are_counterexample_objects(self):
        """
        Scenario: Returned counterexamples are Counterexample dataclass instances
        Given a known non-implication
        When counterexamples are found
        Then each should be a Counterexample with a valid Magma
        """
        from data_models import Counterexample

        counterexamples = find_implication_counterexamples("commutative", "associative")
        assert len(counterexamples) > 0
        for ce in counterexamples:
            assert isinstance(ce, Counterexample)
            assert ce.magma.size >= 2
