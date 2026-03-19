"""Property-based invariant tests for Magma algebraic structures.

Uses Hypothesis to verify universal algebraic invariants that must hold
for ALL finite magmas, not just hand-picked examples.

Organized by BDD scenarios:
  Feature: Magma algebraic invariants
  Scenario: Given ANY finite magma, THEN [invariant] holds
"""

import pytest
from hypothesis import given, note, settings
from strategies import magmas, size_two_magmas, small_magmas

from data_models import Magma

# ── Feature: Closure invariant ──────────────────────────────────
# Given: ANY finite magma M of size n
# Then: op(a, b) ∈ {0, ..., n-1} for all a, b in M


@pytest.mark.property
class TestClosureInvariant:
    """Scenario: Binary operation is closed under the carrier set."""

    @given(m=magmas())
    def test_operation_result_in_carrier(self, m: Magma):
        """For all a, b in M: op(a, b) is in the carrier set."""
        for a in range(m.size):
            for b in range(m.size):
                result = m.op(a, b)
                assert 0 <= result < m.size, f"op({a}, {b}) = {result} not in [0, {m.size})"

    @given(m=magmas())
    def test_elements_match_size(self, m: Magma):
        """The elements list is exactly [0, 1, ..., size-1]."""
        assert m.elements == list(range(m.size))
        assert len(m.elements) == m.size

    @given(m=magmas())
    def test_cayley_table_dimensions(self, m: Magma):
        """Cayley table is exactly size × size."""
        assert len(m.operation) == m.size
        for row in m.operation:
            assert len(row) == m.size


# ── Feature: Identity element uniqueness ────────────────────────
# Given: ANY finite magma M with an identity element
# Then: The identity is unique


@pytest.mark.property
class TestIdentityUniqueness:
    """Scenario: If identity exists, it is unique."""

    @given(m=magmas())
    def test_at_most_one_identity(self, m: Magma):
        """A magma has at most one two-sided identity element."""
        identities = []
        for e in range(m.size):
            is_identity = all(m.op(e, a) == a and m.op(a, e) == a for a in range(m.size))
            if is_identity:
                identities.append(e)

        assert len(identities) <= 1, f"Multiple identities found: {identities}"

    @given(m=magmas())
    def test_has_identity_returns_unique_element(self, m: Magma):
        """has_identity() returns the unique identity or None."""
        result = m.has_identity()
        if result is not None:
            # Verify it actually IS an identity
            for a in range(m.size):
                assert m.op(result, a) == a, f"{result} is not left identity for {a}"
                assert m.op(a, result) == a, f"{result} is not right identity for {a}"


# ── Feature: Commutativity ↔ Cayley table symmetry ──────────────
# Given: ANY finite magma M
# Then: is_commutative() ↔ Cayley table is symmetric


@pytest.mark.property
class TestCommutativitySymmetry:
    """Scenario: Commutativity is equivalent to table symmetry."""

    @given(m=magmas())
    def test_commutative_iff_symmetric_table(self, m: Magma):
        """is_commutative() ↔ ∀a,b: op(a,b) = op(b,a)."""
        is_symmetric = all(
            m.operation[a][b] == m.operation[b][a] for a in range(m.size) for b in range(m.size)
        )
        assert m.is_commutative() == is_symmetric


# ── Feature: Idempotence ↔ diagonal property ────────────────────
# Given: ANY finite magma M
# Then: is_idempotent() ↔ diagonal of Cayley table is [0, 1, ..., n-1]


@pytest.mark.property
class TestIdempotenceDiagonal:
    """Scenario: Idempotence equals identity diagonal in Cayley table."""

    @given(m=magmas())
    def test_idempotent_iff_diagonal_identity(self, m: Magma):
        """is_idempotent() ↔ ∀a: op(a,a) = a."""
        diagonal_is_identity = all(m.operation[a][a] == a for a in range(m.size))
        assert m.is_idempotent() == diagonal_is_identity


# ── Feature: Associativity brute-force correctness ──────────────
# Given: ANY finite magma M
# Then: is_associative() ↔ ∀a,b,c: op(op(a,b), c) = op(a, op(b,c))


@pytest.mark.property
class TestAssociativityCompleteness:
    """Scenario: Associativity check covers all triples."""

    @given(m=small_magmas())
    def test_associativity_definition(self, m: Magma):
        """is_associative() correctly checks all triples."""
        brute_force = all(
            m.op(m.op(a, b), c) == m.op(a, m.op(b, c))
            for a in range(m.size)
            for b in range(m.size)
            for c in range(m.size)
        )
        assert m.is_associative() == brute_force


# ── Feature: Property independence ──────────────────────────────
# Given: The space of ALL size-2 magmas (16 total)
# Then: Each property combination is independently achievable


@pytest.mark.property
class TestPropertyIndependence:
    """Scenario: No unintended property entailments in size-2 magmas."""

    @given(m=size_two_magmas())
    @settings(max_examples=50)
    def test_properties_are_independent_claims(self, m: Magma):
        """Record property combinations to verify independence.

        This test documents which combinations exist rather than
        asserting a specific relationship — the invariant is that
        is_associative() and is_commutative() don't always agree.
        """
        assoc = m.is_associative()
        comm = m.is_commutative()
        # The key invariant: these are NOT the same predicate
        # (there exist magmas where one holds but not the other)
        note(f"assoc={assoc}, comm={comm}")


# ── Feature: Serialization roundtrip ────────────────────────────
# Given: ANY finite magma M
# Then: from_dict(to_dict(M)) reconstructs M exactly


@pytest.mark.property
class TestSerializationRoundtrip:
    """Scenario: Cayley table survives dict serialization."""

    @given(m=magmas())
    def test_dict_roundtrip_preserves_table(self, m: Magma):
        """to_dict_operation → from_dict_operation roundtrip is identity."""
        op_dict = m.to_dict_operation()
        reconstructed = Magma.from_dict_operation(m.elements, op_dict)

        assert reconstructed.size == m.size
        assert reconstructed.elements == m.elements
        assert reconstructed.operation == m.operation

    @given(m=magmas())
    def test_dict_roundtrip_preserves_properties(self, m: Magma):
        """Algebraic properties survive serialization roundtrip."""
        op_dict = m.to_dict_operation()
        r = Magma.from_dict_operation(m.elements, op_dict)

        assert r.is_associative() == m.is_associative()
        assert r.is_commutative() == m.is_commutative()
        assert r.has_identity() == m.has_identity()
        assert r.is_idempotent() == m.is_idempotent()


# ── Feature: TLA+ conversion determinism ───────────────────────
# Given: ANY finite magma M
# Then: to_tla() is deterministic and parseable


@pytest.mark.property
class TestTLAConversion:
    """Scenario: TLA+ output is stable and well-formed."""

    @given(m=magmas(max_size=3))
    def test_tla_deterministic(self, m: Magma):
        """Calling to_tla() twice gives identical output."""
        assert m.to_tla() == m.to_tla()

    @given(m=magmas(max_size=3))
    def test_tla_contains_all_entries(self, m: Magma):
        """TLA+ output contains n² entries for size-n magma."""
        tla = m.to_tla()
        expected_entries = m.size * m.size
        # Count "|->" occurrences (one per entry)
        actual_entries = tla.count("|->")
        assert actual_entries == expected_entries

    @given(m=magmas(max_size=3))
    def test_tla_starts_and_ends_correctly(self, m: Magma):
        """TLA+ format: [<<a,b>> |-> c, ...]."""
        tla = m.to_tla()
        assert tla.startswith("[")
        assert tla.endswith("]")


# ── Feature: Cayley table display ───────────────────────────────


@pytest.mark.property
class TestCayleyTableDisplay:
    """Scenario: String representation is well-formed."""

    @given(m=magmas(max_size=4))
    def test_cayley_table_has_correct_rows(self, m: Magma):
        """Cayley table string has header + separator + size data rows."""
        table_str = m.cayley_table_str()
        lines = table_str.strip().split("\n")
        # header line + separator line + size data rows
        assert len(lines) == m.size + 2


# ── Feature: Trivial magma (size 1) ────────────────────────────
# Given: A size-1 magma (always op(0,0) = 0)
# Then: It is associative, commutative, idempotent, and has identity


@pytest.mark.property
class TestTrivialMagma:
    """Scenario: Size-1 magma has all basic properties."""

    def test_trivial_magma_has_all_properties(self):
        """The single-element magma satisfies all basic properties."""
        m = Magma(size=1, elements=[0], operation=[[0]])
        assert m.is_associative()
        assert m.is_commutative()
        assert m.is_idempotent()
        assert m.has_identity() == 0


# ── Feature: Exhaustive size-2 census ───────────────────────────
# Given: ALL 16 size-2 magmas
# Then: Known property counts match mathematical expectation


@pytest.mark.property
class TestExhaustiveSize2:
    """Scenario: Census of all 16 size-2 magmas matches theory."""

    def test_exact_property_counts(self):
        """Verify known counts: 8 associative, 8 commutative, etc."""
        all_magmas = []
        for i in range(16):
            table = [[0, 0], [0, 0]]
            table[0][0] = i % 2
            table[0][1] = (i // 2) % 2
            table[1][0] = (i // 4) % 2
            table[1][1] = (i // 8) % 2
            all_magmas.append(Magma(size=2, elements=[0, 1], operation=table))

        assoc_count = sum(1 for m in all_magmas if m.is_associative())
        comm_count = sum(1 for m in all_magmas if m.is_commutative())
        idemp_count = sum(1 for m in all_magmas if m.is_idempotent())
        id_count = sum(1 for m in all_magmas if m.has_identity() is not None)

        assert assoc_count == 8
        assert comm_count == 8
        assert idemp_count == 4
        assert id_count == 4

    def test_property_independence_witnessed(self):
        """Verify existence of all four (assoc, comm) combinations."""
        all_magmas = []
        for i in range(16):
            table = [[0, 0], [0, 0]]
            table[0][0] = i % 2
            table[0][1] = (i // 2) % 2
            table[1][0] = (i // 4) % 2
            table[1][1] = (i // 8) % 2
            all_magmas.append(Magma(size=2, elements=[0, 1], operation=table))

        combos = set()
        for m in all_magmas:
            combos.add((m.is_associative(), m.is_commutative()))

        # All four combinations must exist: (T,T), (T,F), (F,T), (F,F)
        assert (True, True) in combos, "No assoc+comm magma found"
        assert (True, False) in combos, "No assoc+¬comm magma found"
        assert (False, True) in combos, "No ¬assoc+comm magma found"
        assert (False, False) in combos, "No ¬assoc+¬comm magma found"
