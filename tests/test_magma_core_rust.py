"""Tests for the Rust magma_core extension module.

Verifies that the Rust implementation matches the pure-Python Magma
from data_models in behavior, and that the Rust-only functions
(count_properties, find_counterexamples) produce correct results.
"""

import pytest

magma_core = pytest.importorskip("magma_core")


class TestRustMagmaBasic:
    """Verify Rust Magma has the same API and results as Python Magma."""

    @pytest.fixture
    def xor_magma(self):
        """Z/2Z under XOR: associative, commutative, identity=0."""
        return magma_core.Magma(2, [[0, 1], [1, 0]])

    @pytest.fixture
    def and_magma(self):
        """Z/2Z under AND: associative, commutative, identity=1, idempotent."""
        return magma_core.Magma(2, [[0, 0], [0, 1]])

    def test_op(self, xor_magma):
        assert xor_magma.op(0, 0) == 0
        assert xor_magma.op(0, 1) == 1
        assert xor_magma.op(1, 0) == 1
        assert xor_magma.op(1, 1) == 0

    def test_size(self, xor_magma):
        assert xor_magma.size == 2

    def test_elements(self, xor_magma):
        assert list(xor_magma.elements) == [0, 1]

    def test_operation_getter(self, xor_magma):
        op = xor_magma.operation
        assert op == [[0, 1], [1, 0]]

    def test_is_associative(self, xor_magma):
        assert xor_magma.is_associative() is True

    def test_is_commutative(self, xor_magma):
        assert xor_magma.is_commutative() is True

    def test_has_identity(self, xor_magma, and_magma):
        assert xor_magma.has_identity() == 0
        assert and_magma.has_identity() == 1

    def test_is_idempotent(self, and_magma, xor_magma):
        assert and_magma.is_idempotent() is True
        assert xor_magma.is_idempotent() is False

    def test_non_associative(self):
        m = magma_core.Magma(3, [[0, 2, 1], [2, 1, 0], [1, 0, 2]])
        assert m.is_associative() is False

    def test_cayley_table_str(self, xor_magma):
        s = xor_magma.cayley_table_str()
        assert "0" in s
        assert "1" in s

    def test_to_tla(self, xor_magma):
        tla = xor_magma.to_tla()
        assert "<<0, 0>> |-> 0" in tla
        assert "<<0, 1>> |-> 1" in tla

    def test_invalid_size_mismatch(self):
        with pytest.raises(Exception):
            magma_core.Magma(2, [[0, 1]])  # only 1 row for size 2

    def test_invalid_column_mismatch(self):
        with pytest.raises(Exception):
            magma_core.Magma(2, [[0], [1]])  # only 1 col for size 2


class TestGenerateAllMagmas:
    def test_size_2_count(self):
        magmas = magma_core.generate_all_magmas(2)
        assert len(magmas) == 16  # 2^(2^2) = 16

    def test_size_3_count(self):
        magmas = magma_core.generate_all_magmas(3)
        assert len(magmas) == 19683  # 3^(3^2) = 3^9

    def test_too_large_raises(self):
        with pytest.raises(ValueError, match="too large"):
            magma_core.generate_all_magmas(5)

    def test_returns_list(self):
        magmas = magma_core.generate_all_magmas(2)
        assert isinstance(magmas, list)


class TestCountProperties:
    def test_size_2(self):
        counts = magma_core.count_properties(2)
        assert counts.total == 16
        assert counts.associative == 8
        assert counts.commutative == 8
        assert counts.has_identity == 4
        assert counts.idempotent == 4

    def test_size_3(self):
        counts = magma_core.count_properties(3)
        assert counts.total == 19683
        assert counts.associative == 113
        assert counts.commutative == 729
        assert counts.has_identity == 243
        assert counts.idempotent == 729

    def test_too_large_raises(self):
        with pytest.raises(ValueError, match="too large"):
            magma_core.count_properties(5)

    def test_matches_manual_count(self):
        """count_properties must agree with iterating generate_all_magmas."""
        magmas = magma_core.generate_all_magmas(2)
        counts = magma_core.count_properties(2)

        assert sum(1 for m in magmas if m.is_associative()) == counts.associative
        assert sum(1 for m in magmas if m.is_commutative()) == counts.commutative
        assert sum(1 for m in magmas if m.has_identity() is not None) == counts.has_identity
        assert sum(1 for m in magmas if m.is_idempotent()) == counts.idempotent


class TestFindCounterexamples:
    def test_commutative_not_implies_associative(self):
        results = magma_core.find_counterexamples("commutative", "associative", 3, 10)
        assert len(results) > 0
        for m in results:
            assert m.is_commutative() is True
            assert m.is_associative() is False

    def test_associative_not_implies_commutative(self):
        results = magma_core.find_counterexamples("associative", "commutative", 3, 10)
        assert len(results) > 0
        for m in results:
            assert m.is_associative() is True
            assert m.is_commutative() is False

    def test_idempotent_not_implies_commutative(self):
        results = magma_core.find_counterexamples("idempotent", "commutative", 3, 10)
        assert len(results) > 0

    def test_limit_respected(self):
        results = magma_core.find_counterexamples("commutative", "associative", 3, 3)
        assert len(results) <= 3

    def test_unknown_property_raises(self):
        with pytest.raises(ValueError, match="Unknown property"):
            magma_core.find_counterexamples("unknown", "associative", 2, 1)


class TestRustMatchesPython:
    """Cross-validate Rust results against the known Python results from test_data_models."""

    def test_xor_matches(self):
        m = magma_core.Magma(2, [[0, 1], [1, 0]])
        assert m.is_associative() is True
        assert m.is_commutative() is True
        assert m.has_identity() == 0
        assert m.is_idempotent() is False

    def test_and_matches(self):
        m = magma_core.Magma(2, [[0, 0], [0, 1]])
        assert m.is_associative() is True
        assert m.is_commutative() is True
        assert m.has_identity() == 1
        assert m.is_idempotent() is True

    def test_no_identity_returns_none(self):
        m = magma_core.Magma(2, [[0, 0], [0, 0]])
        assert m.has_identity() is None


class TestCountPropertiesParallel:
    def test_matches_sequential(self):
        seq = magma_core.count_properties(3)
        par = magma_core.count_properties_parallel(3)
        assert seq.total == par.total
        assert seq.associative == par.associative
        assert seq.commutative == par.commutative
        assert seq.has_identity == par.has_identity
        assert seq.idempotent == par.idempotent
        assert seq.assoc_and_comm == par.assoc_and_comm
        assert seq.monoid == par.monoid

    def test_size_2(self):
        par = magma_core.count_properties_parallel(2)
        assert par.total == 16
        assert par.associative == 8


class TestCheckEquation:
    """Test the arbitrary equation term evaluator."""

    ASSOC_LHS = ["*", ["*", ["x"], ["y"]], ["z"]]
    ASSOC_RHS = ["*", ["x"], ["*", ["y"], ["z"]]]
    COMM_LHS = ["*", ["x"], ["y"]]
    COMM_RHS = ["*", ["y"], ["x"]]
    IDEMP_LHS = ["*", ["x"], ["x"]]
    IDEMP_RHS = ["x"]

    @pytest.fixture
    def xor(self):
        return magma_core.Magma(2, [[0, 1], [1, 0]])

    @pytest.fixture
    def non_assoc(self):
        return magma_core.Magma(3, [[0, 2, 1], [2, 1, 0], [1, 0, 2]])

    def test_associativity_true(self, xor):
        assert (
            magma_core.check_equation(xor, self.ASSOC_LHS, self.ASSOC_RHS, ["x", "y", "z"]) is True
        )

    def test_associativity_false(self, non_assoc):
        assert (
            magma_core.check_equation(non_assoc, self.ASSOC_LHS, self.ASSOC_RHS, ["x", "y", "z"])
            is False
        )

    def test_commutativity(self, xor):
        assert magma_core.check_equation(xor, self.COMM_LHS, self.COMM_RHS, ["x", "y"]) is True

    def test_idempotency_false(self, xor):
        # XOR: 1*1=0 != 1, so not idempotent
        assert magma_core.check_equation(xor, self.IDEMP_LHS, self.IDEMP_RHS, ["x"]) is False

    def test_idempotency_true(self):
        # AND magma: 0*0=0, 1*1=1
        and_m = magma_core.Magma(2, [[0, 0], [0, 1]])
        assert magma_core.check_equation(and_m, self.IDEMP_LHS, self.IDEMP_RHS, ["x"]) is True

    def test_literal_term(self):
        """Literal element terms like ["0"] should work."""
        m = magma_core.Magma(2, [[0, 1], [1, 0]])
        # Check: 0 * x == x (left identity for XOR with identity 0)
        lhs = ["*", ["0"], ["x"]]
        rhs = ["x"]
        assert magma_core.check_equation(m, lhs, rhs, ["x"]) is True

    def test_empty_term_raises(self):
        m = magma_core.Magma(2, [[0, 0], [0, 0]])
        with pytest.raises(Exception):
            magma_core.check_equation(m, [], ["x"], ["x"])


class TestSearchEquationCounterexample:
    ASSOC_LHS = ["*", ["*", ["x"], ["y"]], ["z"]]
    ASSOC_RHS = ["*", ["x"], ["*", ["y"], ["z"]]]
    COMM_LHS = ["*", ["x"], ["y"]]
    COMM_RHS = ["*", ["y"], ["x"]]

    def test_assoc_not_implies_comm(self):
        ce = magma_core.search_equation_counterexample(
            self.ASSOC_LHS,
            self.ASSOC_RHS,
            ["x", "y", "z"],
            self.COMM_LHS,
            self.COMM_RHS,
            ["x", "y"],
            max_size=3,
        )
        assert ce is not None
        assert ce.is_associative() is True
        assert ce.is_commutative() is False

    def test_comm_not_implies_assoc(self):
        ce = magma_core.search_equation_counterexample(
            self.COMM_LHS,
            self.COMM_RHS,
            ["x", "y"],
            self.ASSOC_LHS,
            self.ASSOC_RHS,
            ["x", "y", "z"],
            max_size=3,
        )
        assert ce is not None
        assert ce.is_commutative() is True
        assert ce.is_associative() is False

    def test_reflexive_returns_none(self):
        """An equation always implies itself — no counterexample."""
        ce = magma_core.search_equation_counterexample(
            self.COMM_LHS,
            self.COMM_RHS,
            ["x", "y"],
            self.COMM_LHS,
            self.COMM_RHS,
            ["x", "y"],
            max_size=3,
        )
        assert ce is None


class TestFilterMagmas:
    def test_assoc_and_comm_not_idemp(self):
        results = magma_core.filter_magmas(["associative", "commutative"], ["idempotent"], 3, 10)
        assert len(results) > 0
        for m in results:
            assert m.is_associative() is True
            assert m.is_commutative() is True
            assert m.is_idempotent() is False

    def test_monoid_not_commutative(self):
        results = magma_core.filter_magmas(["associative", "has_identity"], ["commutative"], 3, 10)
        assert len(results) > 0
        for m in results:
            assert m.is_associative() is True
            assert m.has_identity() is not None
            assert m.is_commutative() is False

    def test_limit_respected(self):
        results = magma_core.filter_magmas(["commutative"], [], 3, 5)
        assert len(results) <= 5

    def test_unknown_required_raises(self):
        with pytest.raises(ValueError, match="Unknown property"):
            magma_core.filter_magmas(["bogus"], [], 2, 1)

    def test_unknown_forbidden_raises(self):
        with pytest.raises(ValueError, match="Unknown property"):
            magma_core.filter_magmas([], ["bogus"], 2, 1)
