"""Test that Python and Rust property implementations cover the same set.

This ensures neither implementation drifts ahead of the other without
cross-language tests being updated to match.
"""

import pytest

from data_models import Property

try:
    import magma_core

    HAS_RUST = True
except ImportError:
    HAS_RUST = False

pytestmark = pytest.mark.skipif(not HAS_RUST, reason="magma_core Rust extension not built")

# Properties that Rust's property_checker function accepts
RUST_PROPERTIES = {"associative", "commutative", "has_identity", "idempotent"}

# Properties in Python's Property enum that map to Rust property_checker names
PYTHON_TO_RUST_MAP = {
    Property.ASSOCIATIVE: "associative",
    Property.COMMUTATIVE: "commutative",
    Property.BIDENTITY: "has_identity",
    Property.IDEMPOTENT: "idempotent",
}


class TestPropertyParity:
    """Verify Python and Rust property implementations stay aligned."""

    def test_rust_accepts_all_mapped_properties(self):
        """Every mapped Python property has a working Rust property_checker."""
        # Use find_counterexamples as a proxy to test property_checker
        for py_prop, rust_name in PYTHON_TO_RUST_MAP.items():
            # Should not raise - property name is recognized
            magma_core.find_counterexamples(rust_name, rust_name, max_size=2, limit=0)

    def test_unmapped_properties_documented(self):
        """Properties without Rust equivalents are explicitly tracked."""
        mapped_python = set(PYTHON_TO_RUST_MAP.keys())
        all_python = set(Property)
        unmapped = all_python - mapped_python

        # These properties don't have Rust property_checker equivalents yet
        expected_unmapped = {
            Property.LEFT_IDENTITY,
            Property.RIGHT_IDENTITY,
            Property.LEFT_INVERSE,
            Property.RIGHT_INVERSE,
            Property.INVERSE,
            Property.DISTRIBUTIVE,
            Property.ZERO,
        }
        assert unmapped == expected_unmapped, (
            f"Property parity changed! New unmapped: {unmapped - expected_unmapped}, "
            f"Newly mapped: {expected_unmapped - unmapped}"
        )
