"""Tests for magma generation and property checking."""

import pytest
from tla_bridge import generate_all_magmas


class TestGenerateAllMagmas:
    def test_size_2(self):
        magmas = generate_all_magmas(2)
        assert len(magmas) == 16  # 2^(2^2) = 16

    def test_size_3(self):
        magmas = generate_all_magmas(3)
        assert len(magmas) == 19683  # 3^(3^2) = 3^9

    def test_too_large_raises(self):
        with pytest.raises(ValueError, match="too large"):
            generate_all_magmas(5)

    def test_returns_tuple(self):
        magmas = generate_all_magmas(2)
        assert isinstance(magmas, tuple)

    def test_caching(self):
        """Second call should return same object (cached)."""
        result1 = generate_all_magmas(2)
        result2 = generate_all_magmas(2)
        assert result1 is result2


class TestMagmaPropertyCounts:
    """Verify known counts of magma properties for size 2."""

    @pytest.fixture
    def size2_magmas(self):
        return generate_all_magmas(2)

    def test_associative_count(self, size2_magmas):
        count = sum(1 for m in size2_magmas if m.is_associative())
        # Known: 8 of 16 size-2 magmas are associative
        assert count == 8

    def test_commutative_count(self, size2_magmas):
        count = sum(1 for m in size2_magmas if m.is_commutative())
        # Known: 8 of 16 size-2 magmas are commutative
        assert count == 8

    def test_identity_count(self, size2_magmas):
        count = sum(1 for m in size2_magmas if m.has_identity() is not None)
        # For size n: n * n^((n-1)^2) magmas have identity. Size 2: 2*2^1 = 4.
        assert count == 4


class TestCounterexampleSearch:
    """Test that we can actually find counterexamples."""

    def test_commutative_not_implies_associative(self):
        """There exist commutative, non-associative magmas."""
        magmas = generate_all_magmas(3)
        counter = [m for m in magmas if m.is_commutative() and not m.is_associative()]
        assert len(counter) > 0, "Expected counterexample: commutative but not associative"

    def test_associative_not_implies_commutative(self):
        """There exist associative, non-commutative magmas."""
        magmas = generate_all_magmas(3)
        counter = [m for m in magmas if m.is_associative() and not m.is_commutative()]
        assert len(counter) > 0, "Expected counterexample: associative but not commutative"
