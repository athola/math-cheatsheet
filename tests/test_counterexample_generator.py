"""Tests for the counterexample generation pipeline.

Tests the automated counterexample generation for FALSE equational implications:
- Exhaustive magma generation for small sizes
- Counterexample finding for known FALSE pairs
- Batch counterexample search with caching
- Optimal magma discovery (which magmas witness the most FALSE pairs)
"""

import pytest

from src.counterexample_generator import (
    BatchCounterexampleSearch,
    CounterexampleFinder,
    MagmaGenerator,
    OptimalMagmaDiscovery,
)
from src.equation_analyzer import parse_equation


class TestMagmaGenerator:
    """
    Feature: Generate all magma tables of a given size.

    As a counterexample searcher
    I want to enumerate all possible magma operations
    So that I can exhaustively search for counterexamples.
    """

    @pytest.mark.unit
    def test_size_1_generates_1_magma(self):
        """
        Scenario: Size 1 has exactly 1 magma
        Given size = 1
        When I generate all magmas
        Then I get exactly 1 table: [[0]]
        """
        tables = MagmaGenerator.generate_all(1)
        assert len(tables) == 1
        assert tables[0] == [[0]]

    @pytest.mark.unit
    def test_size_2_generates_16_magmas(self):
        """
        Scenario: Size 2 has exactly 16 magmas (2^4)
        Given size = 2
        When I generate all magmas
        Then I get exactly 16 distinct tables
        """
        tables = MagmaGenerator.generate_all(2)
        assert len(tables) == 16
        # All tables should be distinct
        table_tuples = [tuple(tuple(row) for row in t) for t in tables]
        assert len(set(table_tuples)) == 16

    @pytest.mark.unit
    def test_size_2_tables_are_valid(self):
        """
        Scenario: All size-2 tables contain only valid elements {0, 1}
        Given all size-2 magma tables
        When I check each entry
        Then every entry is in {0, 1}
        """
        tables = MagmaGenerator.generate_all(2)
        for table in tables:
            assert len(table) == 2
            for row in table:
                assert len(row) == 2
                for val in row:
                    assert val in {0, 1}

    @pytest.mark.unit
    def test_size_3_generates_19683_magmas(self):
        """
        Scenario: Size 3 has exactly 3^9 = 19683 magmas
        Given size = 3
        When I generate all magmas
        Then I get exactly 19683 tables
        """
        tables = MagmaGenerator.generate_all(3)
        assert len(tables) == 19683

    @pytest.mark.unit
    def test_size_2_includes_known_magmas(self):
        """
        Scenario: Generated size-2 tables include canonical magmas
        Given the left projection magma [[0,0],[1,1]]
        When I generate all size-2 magmas
        Then LP is among them
        """
        tables = MagmaGenerator.generate_all(2)
        lp = [[0, 0], [1, 1]]
        rp = [[0, 1], [0, 1]]
        c0 = [[0, 0], [0, 0]]
        xor = [[0, 1], [1, 0]]
        assert lp in tables
        assert rp in tables
        assert c0 in tables
        assert xor in tables

    @pytest.mark.unit
    def test_invalid_size_raises(self):
        """Size must be at least 1."""
        with pytest.raises(ValueError):
            MagmaGenerator.generate_all(0)
        with pytest.raises(ValueError):
            MagmaGenerator.generate_all(-1)


class TestCounterexampleFinder:
    """
    Feature: Find counterexample magmas for FALSE implications.

    As a decision procedure
    I want to find magmas where H holds but T does not
    So that I can prove implications are FALSE.
    """

    @pytest.mark.unit
    def test_assoc_does_not_imply_comm(self):
        """
        Scenario: Associativity does NOT imply commutativity
        Given H = associativity, T = commutativity
        When I search for a counterexample up to size 2
        Then I find a magma where assoc holds but comm fails
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * y = y * x")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=2)
        assert result is not None
        assert result.size == 2
        # Verify the counterexample is correct
        assert h.holds_in(result.table, result.size)
        assert not t.holds_in(result.table, result.size)

    @pytest.mark.unit
    def test_comm_does_not_imply_assoc(self):
        """
        Scenario: Commutativity does NOT imply associativity
        Given H = commutativity, T = associativity
        When I search for a counterexample up to size 2
        Then I find a counterexample
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * (y * z) = (x * y) * z")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=2)
        assert result is not None
        assert h.holds_in(result.table, result.size)
        assert not t.holds_in(result.table, result.size)

    @pytest.mark.unit
    def test_assoc_does_not_imply_idempotent(self):
        """
        Scenario: Associativity does NOT imply idempotency
        Given H = associativity, T = x*x=x
        When I search for a counterexample
        Then I find one (e.g., constant-zero magma)
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * x = x")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=2)
        assert result is not None
        assert h.holds_in(result.table, result.size)
        assert not t.holds_in(result.table, result.size)

    @pytest.mark.unit
    def test_identical_equations_no_counterexample(self):
        """
        Scenario: An equation implies itself (no counterexample)
        Given H = T = commutativity
        When I search for a counterexample
        Then None is returned
        """
        h = parse_equation("x * y = y * x")
        t = parse_equation("x * y = y * x")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=2)
        assert result is None

    @pytest.mark.unit
    def test_collapse_implies_everything(self):
        """
        Scenario: Collapse law x=y implies any equation
        Given H = x=y (forces |M|=1)
        When searching for counterexample to H => T for any T
        Then None is returned (no counterexample exists at any size)
        """
        h = parse_equation("x = y")
        t = parse_equation("x * y = y * x")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=2)
        assert result is None

    @pytest.mark.unit
    def test_counterexample_has_correct_name(self):
        """
        Scenario: Counterexample magma has a descriptive name
        Given a found counterexample
        Then it has a non-empty name with size info
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * y = y * x")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=2)
        assert result is not None
        assert result.name  # non-empty
        assert "size" in result.name.lower() or "2" in result.name

    @pytest.mark.unit
    def test_finds_at_smallest_size(self):
        """
        Scenario: Finder returns counterexample from the smallest size
        Given a FALSE implication with size-2 counterexample
        When I search up to size 3
        Then the found counterexample is size 2 (earliest found)
        """
        h = parse_equation("x * (y * z) = (x * y) * z")
        t = parse_equation("x * y = y * x")
        finder = CounterexampleFinder()
        result = finder.find_counterexample(h, t, max_size=3)
        assert result is not None
        assert result.size == 2  # Found at smallest possible size


class TestBatchCounterexampleSearch:
    """
    Feature: Search counterexamples for multiple equation pairs efficiently.

    As an implication analyzer
    I want to batch-search counterexamples for many pairs
    So that I can amortize the cost of magma generation and equation checking.
    """

    @pytest.mark.unit
    def test_batch_finds_known_false_pairs(self):
        """
        Scenario: Batch search finds counterexamples for known FALSE pairs
        Given three known FALSE implication pairs
        When I batch-search at size 2
        Then all three get counterexamples
        """
        assoc = parse_equation("x * (y * z) = (x * y) * z")
        comm = parse_equation("x * y = y * x")
        idem = parse_equation("x * x = x")
        pairs = [
            (assoc, comm),  # assoc !=> comm
            (comm, assoc),  # comm !=> assoc
            (assoc, idem),  # assoc !=> idem
        ]
        batch = BatchCounterexampleSearch()
        results = batch.search_batch(pairs, max_size=2)
        assert len(results) == 3
        for i, (h, t) in enumerate(pairs):
            assert i in results, f"No counterexample found for pair {i}"
            cx = results[i]
            assert h.holds_in(cx.table, cx.size)
            assert not t.holds_in(cx.table, cx.size)

    @pytest.mark.unit
    def test_batch_returns_empty_for_true_pairs(self):
        """
        Scenario: Batch search returns empty dict for TRUE-only pairs
        Given pairs where all implications are TRUE
        When I batch-search
        Then the result dict is empty
        """
        eq = parse_equation("x * y = y * x")
        pairs = [(eq, eq)]  # trivially true
        batch = BatchCounterexampleSearch()
        results = batch.search_batch(pairs, max_size=2)
        assert len(results) == 0

    @pytest.mark.unit
    def test_batch_mixed_true_and_false(self):
        """
        Scenario: Batch search handles mix of TRUE and FALSE pairs
        Given one TRUE and one FALSE pair
        When I batch-search
        Then only the FALSE pair has a counterexample
        """
        assoc = parse_equation("x * (y * z) = (x * y) * z")
        comm = parse_equation("x * y = y * x")
        pairs = [
            (comm, comm),  # TRUE
            (assoc, comm),  # FALSE
        ]
        batch = BatchCounterexampleSearch()
        results = batch.search_batch(pairs, max_size=2)
        assert 0 not in results  # TRUE pair has no counterexample
        assert 1 in results  # FALSE pair has counterexample

    @pytest.mark.unit
    def test_batch_uses_caching(self):
        """
        Scenario: Batch search caches satisfiability to avoid recomputation
        Given multiple pairs involving the same equations
        When I batch-search
        Then the cache is populated (internal detail, but we verify results are correct)
        """
        assoc = parse_equation("x * (y * z) = (x * y) * z")
        comm = parse_equation("x * y = y * x")
        idem = parse_equation("x * x = x")
        pairs = [
            (assoc, comm),
            (assoc, idem),
            (comm, idem),
        ]
        batch = BatchCounterexampleSearch()
        results = batch.search_batch(pairs, max_size=2)
        # All three should be FALSE and have counterexamples
        assert len(results) == 3


class TestOptimalMagmaDiscovery:
    """
    Feature: Find magmas that witness the most FALSE implications.

    As a cheatsheet designer
    I want to know which small magmas are most useful
    So that I can include them in the canonical counterexample set.
    """

    @pytest.mark.unit
    def test_find_optimal_among_size_2(self):
        """
        Scenario: Find the best size-2 magmas for a small set of equations
        Given a set of equations (assoc, comm, idem)
        When I find optimal magmas
        Then the result is a non-empty sorted list of (table, witness_count)
        """
        equations = [
            parse_equation("x * (y * z) = (x * y) * z"),  # assoc
            parse_equation("x * y = y * x"),  # comm
            parse_equation("x * x = x"),  # idem
        ]
        # FALSE pairs among these three
        false_pairs = [
            (0, 1),  # assoc !=> comm
            (1, 0),  # comm !=> assoc
            (0, 2),  # assoc !=> idem
            (2, 0),  # idem !=> assoc
            (1, 2),  # comm !=> idem
            (2, 1),  # idem !=> comm
        ]
        discovery = OptimalMagmaDiscovery()
        results = discovery.find_optimal_magmas(
            equations=equations,
            false_pairs=false_pairs,
            n_magmas=5,
            size=2,
        )
        assert len(results) > 0
        # Results should be sorted by witness count (descending)
        counts = [count for _, count in results]
        assert counts == sorted(counts, reverse=True)
        # Each result is (table, count) where count > 0
        for table, count in results:
            assert count > 0
            assert len(table) == 2
            assert len(table[0]) == 2

    @pytest.mark.unit
    def test_optimal_magmas_limited_by_n(self):
        """
        Scenario: Result is limited to n_magmas entries
        Given n_magmas = 3
        When I find optimal magmas
        Then at most 3 are returned
        """
        equations = [
            parse_equation("x * (y * z) = (x * y) * z"),
            parse_equation("x * y = y * x"),
            parse_equation("x * x = x"),
        ]
        false_pairs = [
            (0, 1),
            (1, 0),
            (0, 2),
            (2, 0),
            (1, 2),
            (2, 1),
        ]
        discovery = OptimalMagmaDiscovery()
        results = discovery.find_optimal_magmas(
            equations=equations,
            false_pairs=false_pairs,
            n_magmas=3,
            size=2,
        )
        assert len(results) <= 3

    @pytest.mark.unit
    def test_optimal_magma_witnesses_verified(self):
        """
        Scenario: Each optimal magma's witness count is verifiable
        Given an optimal magma result
        When I manually check which FALSE pairs it witnesses
        Then the count matches
        """
        equations = [
            parse_equation("x * (y * z) = (x * y) * z"),  # 0: assoc
            parse_equation("x * y = y * x"),  # 1: comm
            parse_equation("x * x = x"),  # 2: idem
        ]
        false_pairs = [
            (0, 1),
            (1, 0),
            (0, 2),
            (2, 0),
            (1, 2),
            (2, 1),
        ]
        discovery = OptimalMagmaDiscovery()
        results = discovery.find_optimal_magmas(
            equations=equations,
            false_pairs=false_pairs,
            n_magmas=16,
            size=2,
        )
        for table, reported_count in results:
            # Manually verify
            actual_count = 0
            for h_idx, t_idx in false_pairs:
                h_eq = equations[h_idx]
                t_eq = equations[t_idx]
                if h_eq.holds_in(table, 2) and not t_eq.holds_in(table, 2):
                    actual_count += 1
            assert actual_count == reported_count, (
                f"Table {table}: reported {reported_count} but verified {actual_count}"
            )
