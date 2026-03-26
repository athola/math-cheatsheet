"""Tests for tla/Counterexamples/counterexample_db.py CounterexampleDatabase.

Tests initialization, add/query operations, implication status,
statistics, and cheatsheet entry generation.
"""

import pytest
from counterexample_db import CounterexampleDatabase

from data_models import Counterexample, Magma


@pytest.fixture
def empty_db(tmp_path):
    """A fresh CounterexampleDatabase backed by a non-existent file."""
    return CounterexampleDatabase(db_path=tmp_path / "test_db.json")


@pytest.fixture
def sample_magma():
    """XOR magma for use in counterexample entries."""
    return Magma(size=2, elements=[0, 1], operation=[[0, 1], [1, 0]])


@pytest.fixture
def sample_counterexample(sample_magma):
    """A single counterexample with premise_id=1, conclusion_id=2."""
    return Counterexample(
        premise_id=1,
        conclusion_id=2,
        magma=sample_magma,
        red_flags={"non_commutative"},
    )


class TestCounterexampleDatabaseInit:
    """
    Feature: CounterexampleDatabase initialization.

    As a database consumer
    I want to create an empty database when no file exists
    So that I can start collecting counterexamples from scratch.
    """

    @pytest.mark.unit
    def test_initializes_with_empty_list(self, empty_db):
        """
        Scenario: New database has no counterexamples
        Given a db_path that does not exist
        When I create a CounterexampleDatabase
        Then the counterexamples list should be empty
        """
        assert empty_db.counterexamples == []

    @pytest.mark.unit
    def test_index_is_empty_on_init(self, empty_db):
        """
        Scenario: New database has an empty index
        Given a freshly initialized database
        Then the internal index should be empty
        """
        assert empty_db._index == {}


class TestCounterexampleDatabaseAdd:
    """
    Feature: Adding counterexamples to the database.

    As a researcher
    I want to add counterexamples and have them indexed
    So that I can look them up efficiently later.
    """

    @pytest.mark.unit
    def test_add_stores_counterexample(self, empty_db, sample_counterexample):
        """
        Scenario: Adding a counterexample increases the list length
        Given an empty database
        When I add one counterexample
        Then the database should contain exactly 1 counterexample
        """
        empty_db.add(sample_counterexample)
        assert len(empty_db.counterexamples) == 1
        assert empty_db.counterexamples[0] is sample_counterexample

    @pytest.mark.unit
    def test_add_indexes_by_premise_conclusion(self, empty_db, sample_counterexample):
        """
        Scenario: Adding a counterexample updates the index
        Given an empty database
        When I add a counterexample with premise_id=1, conclusion_id=2
        Then the index key (1, 2) should contain the counterexample index
        """
        empty_db.add(sample_counterexample)
        assert (1, 2) in empty_db._index
        assert empty_db._index[(1, 2)] == [0]

    @pytest.mark.unit
    def test_add_multiple_same_key(self, empty_db, sample_magma):
        """
        Scenario: Multiple counterexamples for the same implication
        Given two counterexamples with the same (premise_id, conclusion_id)
        When I add both
        Then the index should list both indices under that key
        """
        ce1 = Counterexample(premise_id=1, conclusion_id=2, magma=sample_magma)
        ce2 = Counterexample(premise_id=1, conclusion_id=2, magma=sample_magma)
        empty_db.add(ce1)
        empty_db.add(ce2)
        assert len(empty_db._index[(1, 2)]) == 2


class TestCounterexampleDatabaseQuery:
    """
    Feature: Querying counterexamples from the database.

    As a researcher
    I want to retrieve counterexamples by implication pair
    So that I can analyze specific implications.
    """

    @pytest.mark.unit
    def test_get_counterexamples_returns_matching(self, empty_db, sample_counterexample):
        """
        Scenario: Retrieving counterexamples by (premise_id, conclusion_id)
        Given a database with one counterexample for (1, 2)
        When I query get_counterexamples(1, 2)
        Then I should get a list with that counterexample
        """
        empty_db.add(sample_counterexample)
        results = empty_db.get_counterexamples(1, 2)
        assert len(results) == 1
        assert results[0] is sample_counterexample

    @pytest.mark.unit
    def test_get_counterexamples_returns_empty_for_unknown_key(self, empty_db):
        """
        Scenario: Querying a key with no counterexamples
        Given an empty database
        When I query get_counterexamples(99, 100)
        Then I should get an empty list
        """
        results = empty_db.get_counterexamples(99, 100)
        assert results == []


class TestImplicationStatus:
    """
    Feature: Determine implication status based on counterexample count.

    As a cheatsheet author
    I want to classify implications by how many counterexamples exist
    So that I can indicate confidence levels.
    """

    @pytest.mark.unit
    def test_always_true_with_no_counterexamples(self, empty_db):
        """
        Scenario: No counterexamples means implication appears to hold
        Given no counterexamples for (1, 2)
        When I check get_implication_status(1, 2)
        Then the status should be "always_true"
        """
        assert empty_db.get_implication_status(1, 2) == "always_true"

    @pytest.mark.unit
    def test_sometimes_false_with_few_counterexamples(self, empty_db, sample_magma):
        """
        Scenario: A few counterexamples yields "sometimes_false"
        Given 5 counterexamples for (1, 2)
        When I check get_implication_status(1, 2)
        Then the status should be "sometimes_false"
        """
        for _ in range(5):
            empty_db.add(Counterexample(premise_id=1, conclusion_id=2, magma=sample_magma))
        assert empty_db.get_implication_status(1, 2) == "sometimes_false"

    @pytest.mark.unit
    def test_likely_false_with_moderate_counterexamples(self, empty_db, sample_magma):
        """
        Scenario: 11-100 counterexamples yields "likely_false"
        Given 50 counterexamples for (1, 2)
        When I check get_implication_status(1, 2)
        Then the status should be "likely_false"
        """
        for _ in range(50):
            empty_db.add(Counterexample(premise_id=1, conclusion_id=2, magma=sample_magma))
        assert empty_db.get_implication_status(1, 2) == "likely_false"

    @pytest.mark.unit
    def test_very_likely_false_with_many_counterexamples(self, empty_db, sample_magma):
        """
        Scenario: Over 100 counterexamples yields "very_likely_false"
        Given 101 counterexamples for (1, 2)
        When I check get_implication_status(1, 2)
        Then the status should be "very_likely_false"
        """
        for _ in range(101):
            empty_db.add(Counterexample(premise_id=1, conclusion_id=2, magma=sample_magma))
        assert empty_db.get_implication_status(1, 2) == "very_likely_false"


class TestGetStatistics:
    """
    Feature: Database statistics summarize the collection.

    As a researcher
    I want aggregate statistics on the counterexample database
    So that I can assess coverage.
    """

    @pytest.mark.unit
    def test_empty_statistics(self, empty_db):
        """
        Scenario: Empty database returns zero counts
        Given an empty database
        When I call get_statistics
        Then total_counterexamples should be 0
        And unique_implications should be 0
        """
        stats = empty_db.get_statistics()
        assert stats["total_counterexamples"] == 0
        assert stats["unique_implications"] == 0
        assert stats["red_flag_frequencies"] == {}

    @pytest.mark.unit
    def test_statistics_with_entries(self, empty_db, sample_magma):
        """
        Scenario: Statistics reflect added counterexamples
        Given 3 counterexamples for 2 distinct implications
        When I call get_statistics
        Then total should be 3 and unique_implications should be 2
        """
        empty_db.add(
            Counterexample(premise_id=1, conclusion_id=2, magma=sample_magma, red_flags={"flag_a"})
        )
        empty_db.add(
            Counterexample(
                premise_id=1, conclusion_id=2, magma=sample_magma, red_flags={"flag_a", "flag_b"}
            )
        )
        empty_db.add(
            Counterexample(premise_id=3, conclusion_id=4, magma=sample_magma, red_flags={"flag_b"})
        )

        stats = empty_db.get_statistics()
        assert stats["total_counterexamples"] == 3
        assert stats["unique_implications"] == 2
        assert stats["red_flag_frequencies"]["flag_a"] == 2
        assert stats["red_flag_frequencies"]["flag_b"] == 2


class TestGenerateCheatsheetEntry:
    """
    Feature: Generate formatted cheatsheet entries for implications.

    As a cheatsheet author
    I want structured entries with status, count, and recommendations
    So that I can build the final cheatsheet document.
    """

    @pytest.mark.unit
    def test_cheatsheet_entry_always_true(self, empty_db):
        """
        Scenario: Cheatsheet entry for an implication with no counterexamples
        Given no counterexamples for (1, 2)
        When I generate a cheatsheet entry
        Then status should be "always_true"
        And counterexample_count should be 0
        And the entry should contain implication, status, and recommendation keys
        """
        entry = empty_db.generate_cheatsheet_entry(1, 2)
        assert entry["implication"] == "E1 => E2"
        assert entry["status"] == "always_true"
        assert entry["counterexample_count"] == 0
        assert "recommendation" in entry
        assert "red_flags" in entry

    @pytest.mark.unit
    def test_cheatsheet_entry_with_counterexamples(self, empty_db, sample_magma):
        """
        Scenario: Cheatsheet entry reflects counterexample data
        Given 5 counterexamples for (10, 20) with red flags
        When I generate a cheatsheet entry
        Then status should be "sometimes_false"
        And counterexample_count should be 5
        """
        for _ in range(5):
            empty_db.add(
                Counterexample(
                    premise_id=10,
                    conclusion_id=20,
                    magma=sample_magma,
                    red_flags={"size_2_only"},
                )
            )
        entry = empty_db.generate_cheatsheet_entry(10, 20)
        assert entry["implication"] == "E10 => E20"
        assert entry["status"] == "sometimes_false"
        assert entry["counterexample_count"] == 5
        assert "size_2_only" in entry["red_flags"]
