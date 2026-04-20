"""Cross-language consistency invariant tests.

Verifies that Python (data_models.Magma) and Rust (magma_core.Magma)
agree on ALL algebraic property computations. This is the critical
integration test: if these disagree, the entire verification pipeline
is unreliable.

BDD Scenarios:
  Feature: Python ↔ Rust magma property agreement
  Scenario: Given ANY Cayley table, BOTH implementations agree on every property
"""

import pytest
from hypothesis import given, settings
from strategies import magma_tables

from data_models import Magma as PyMagma

# Conditional import: Rust extension may not be built
try:
    import magma_core

    HAS_RUST = True
except ImportError:
    HAS_RUST = False

pytestmark = [
    pytest.mark.property,
    pytest.mark.cross_language,
    pytest.mark.skipif(not HAS_RUST, reason="magma_core Rust extension not built"),
]


# ── Feature: Property checker agreement ─────────────────────────
# Given: ANY Cayley table as both a Python Magma and a Rust Magma
# Then: All property checks return identical results


class TestPropertyAgreement:
    """Scenario: Python and Rust agree on every algebraic property."""

    @given(table=magma_tables(size=2))
    @settings(max_examples=16)  # There are only 16 size-2 magmas
    def test_size_2_all_properties(self, table):
        """Exhaustive: all 16 size-2 magmas agree across languages."""
        py_m = PyMagma(size=2, operation=table)
        rust_m = magma_core.Magma(2, table)

        assert py_m.is_associative() == rust_m.is_associative()
        assert py_m.is_commutative() == rust_m.is_commutative()
        assert py_m.is_idempotent() == rust_m.is_idempotent()

        py_id = py_m.has_identity()
        rust_id = rust_m.has_identity()
        assert (py_id is not None) == (rust_id is not None)
        if py_id is not None:
            assert py_id == rust_id

    @given(table=magma_tables(size=3))
    @settings(max_examples=200)
    def test_size_3_associativity(self, table):
        """Sampled: size-3 magmas agree on associativity."""
        py_m = PyMagma(size=3, operation=table)
        rust_m = magma_core.Magma(3, table)

        assert py_m.is_associative() == rust_m.is_associative()

    @given(table=magma_tables(size=3))
    @settings(max_examples=200)
    def test_size_3_commutativity(self, table):
        """Sampled: size-3 magmas agree on commutativity."""
        py_m = PyMagma(size=3, operation=table)
        rust_m = magma_core.Magma(3, table)

        assert py_m.is_commutative() == rust_m.is_commutative()

    @given(table=magma_tables(size=3))
    @settings(max_examples=200)
    def test_size_3_identity(self, table):
        """Sampled: size-3 magmas agree on identity existence."""
        py_m = PyMagma(size=3, operation=table)
        rust_m = magma_core.Magma(3, table)

        py_id = py_m.has_identity()
        rust_id = rust_m.has_identity()
        assert (py_id is not None) == (rust_id is not None)

    @given(table=magma_tables(size=3))
    @settings(max_examples=200)
    def test_size_3_idempotence(self, table):
        """Sampled: size-3 magmas agree on idempotence."""
        py_m = PyMagma(size=3, operation=table)
        rust_m = magma_core.Magma(3, table)

        assert py_m.is_idempotent() == rust_m.is_idempotent()


# ── Feature: Cayley table representation agreement ──────────────
# Given: A Rust-constructed Magma
# Then: Its operation getter returns the same table we passed in


class TestTableRepresentation:
    """Scenario: Rust Magma preserves exact Cayley table."""

    @given(table=magma_tables(size=2))
    def test_operation_getter_roundtrip_size_2(self, table):
        """Rust .operation getter returns the original table."""
        rust_m = magma_core.Magma(2, table)
        recovered = [list(row) for row in rust_m.operation]
        assert recovered == table

    @given(table=magma_tables(size=3))
    @settings(max_examples=100)
    def test_operation_getter_roundtrip_size_3(self, table):
        """Rust .operation getter returns the original table (size 3)."""
        rust_m = magma_core.Magma(3, table)
        recovered = [list(row) for row in rust_m.operation]
        assert recovered == table


# ── Feature: Exhaustive enumeration count ───────────────────────
# Given: generate_all_magmas(n)
# Then: Returns exactly n^(n²) magmas


class TestEnumerationCount:
    """Scenario: Exhaustive generation produces the correct total."""

    def test_size_1_count(self):
        """Size 1: 1^1 = 1 magma."""
        magmas = magma_core.generate_all_magmas(1)
        assert len(magmas) == 1

    def test_size_2_count(self):
        """Size 2: 2^4 = 16 magmas."""
        magmas = magma_core.generate_all_magmas(2)
        assert len(magmas) == 16

    def test_size_3_count(self):
        """Size 3: 3^9 = 19683 magmas."""
        magmas = magma_core.generate_all_magmas(3)
        assert len(magmas) == 19683


# ── Feature: Property count consistency ─────────────────────────
# Given: count_properties(n) and count_properties_parallel(n)
# Then: Sequential and parallel counts are identical


class TestPropertyCountConsistency:
    """Scenario: Sequential and parallel counts agree."""

    def test_size_2_seq_parallel_agree(self):
        """Sequential and parallel property counts agree for size 2."""
        seq = magma_core.count_properties(2)
        par = magma_core.count_properties_parallel(2)

        assert seq.total == par.total
        assert seq.associative == par.associative
        assert seq.commutative == par.commutative
        assert seq.has_identity == par.has_identity
        assert seq.idempotent == par.idempotent
        assert seq.assoc_and_comm == par.assoc_and_comm
        assert seq.monoid == par.monoid

    @pytest.mark.slow
    def test_size_3_seq_parallel_agree(self):
        """Sequential and parallel property counts agree for size 3."""
        seq = magma_core.count_properties(3)
        par = magma_core.count_properties_parallel(3)

        assert seq.total == par.total
        assert seq.associative == par.associative
        assert seq.commutative == par.commutative


# ── Feature: Counterexample validity ────────────────────────────
# Given: find_counterexamples(P, Q) returns magma M
# Then: M satisfies P AND M does NOT satisfy Q


class TestCounterexampleValidity:
    """Scenario: Every found counterexample is actually valid."""

    @pytest.mark.parametrize(
        "premise,conclusion",
        [
            ("associative", "commutative"),
            ("commutative", "associative"),
            ("idempotent", "commutative"),
            ("associative", "idempotent"),
        ],
    )
    def test_counterexample_satisfies_premise_not_conclusion(self, premise, conclusion):
        """Every returned counterexample genuinely witnesses non-implication."""
        counterexamples = magma_core.find_counterexamples(premise, conclusion, max_size=3, limit=10)

        checker = {
            "associative": lambda m: m.is_associative(),
            "commutative": lambda m: m.is_commutative(),
            "has_identity": lambda m: m.has_identity() is not None,
            "idempotent": lambda m: m.is_idempotent(),
        }

        for m in counterexamples:
            assert checker[premise](m), f"Counterexample doesn't satisfy premise '{premise}'"
            assert not checker[conclusion](m), f"Counterexample satisfies conclusion '{conclusion}'"


# ── Feature: Equation checking consistency ──────────────────────
# Given: A known equation (e.g., associativity) and a magma
# Then: check_equation agrees with the property checker


class TestEquationCheckConsistency:
    """Scenario: check_equation agrees with direct property checks."""

    @given(table=magma_tables(size=2))
    def test_associativity_equation_matches_property(self, table):
        """check_equation(assoc) == is_associative() for all size-2."""
        rust_m = magma_core.Magma(2, table)

        # Associativity: (x*y)*z = x*(y*z)
        lhs = ["*", ["*", ["x"], ["y"]], ["z"]]
        rhs = ["*", ["x"], ["*", ["y"], ["z"]]]
        vars = ["x", "y", "z"]

        eq_result = magma_core.check_equation(rust_m, lhs, rhs, vars)
        prop_result = rust_m.is_associative()

        assert eq_result == prop_result

    @given(table=magma_tables(size=2))
    def test_commutativity_equation_matches_property(self, table):
        """check_equation(comm) == is_commutative() for all size-2."""
        rust_m = magma_core.Magma(2, table)

        # Commutativity: x*y = y*x
        lhs = ["*", ["x"], ["y"]]
        rhs = ["*", ["y"], ["x"]]
        vars = ["x", "y"]

        eq_result = magma_core.check_equation(rust_m, lhs, rhs, vars)
        prop_result = rust_m.is_commutative()

        assert eq_result == prop_result

    @given(table=magma_tables(size=2))
    def test_idempotence_equation_matches_property(self, table):
        """check_equation(idemp) == is_idempotent() for all size-2."""
        rust_m = magma_core.Magma(2, table)

        # Idempotence: x*x = x
        lhs = ["*", ["x"], ["x"]]
        rhs = ["x"]
        vars = ["x"]

        eq_result = magma_core.check_equation(rust_m, lhs, rhs, vars)
        prop_result = rust_m.is_idempotent()

        assert eq_result == prop_result


# ── Feature: Filter consistency ─────────────────────────────────
# Given: filter_magmas(required, forbidden)
# Then: Every returned magma satisfies all required and no forbidden


class TestFilterConsistency:
    """Scenario: Filtered magmas satisfy all constraints."""

    @pytest.mark.parametrize(
        "required,forbidden",
        [
            (["associative"], ["commutative"]),
            (["commutative"], ["associative"]),
            (["associative", "commutative"], []),
            ([], ["associative", "commutative"]),
            (["idempotent"], ["has_identity"]),
        ],
    )
    def test_filtered_magmas_match_constraints(self, required, forbidden):
        """All returned magmas pass required checks and fail forbidden checks."""
        results = magma_core.filter_magmas(required, forbidden, max_size=3, limit=50)

        checker = {
            "associative": lambda m: m.is_associative(),
            "commutative": lambda m: m.is_commutative(),
            "has_identity": lambda m: m.has_identity() is not None,
            "idempotent": lambda m: m.is_idempotent(),
        }

        for m in results:
            for req in required:
                assert checker[req](m), f"Required '{req}' not satisfied"
            for forb in forbidden:
                assert not checker[forb](m), f"Forbidden '{forb}' is satisfied"
