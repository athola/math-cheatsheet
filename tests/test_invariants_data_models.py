"""Property-based invariant tests for data model serialization and consistency.

Verifies that Equation, Problem, and Counterexample data structures
maintain consistency through serialization, conversion, and comparison.

BDD Scenarios:
  Feature: Data model integrity
  Scenario: Given ANY valid data model instance, THEN structural invariants hold
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from strategies import equations, magmas, problems

from data_models import (
    SYNTHETIC_EQUATIONS,
    Counterexample,
    Difficulty,
    EquationEntry,
    Magma,
    Problem,
    Property,
)

# ── Feature: Equation invariants ────────────────────────────────
# Given: ANY Equation
# Then: Serialization preserves all fields


@pytest.mark.property
class TestEquationInvariants:
    """Scenario: Equation data survives serialization."""

    @given(eq=equations())
    def test_to_dict_roundtrip(self, eq: EquationEntry):
        """to_dict preserves all fields."""
        d = eq.to_dict()
        assert d["id"] == eq.id
        assert d["latex"] == eq.latex
        assert d["name"] == eq.name
        assert d["description"] == eq.description
        assert d["properties"] == [p.value for p in eq.properties]

    @given(eq=equations())
    def test_str_contains_id(self, eq: EquationEntry):
        """String representation contains the equation id."""
        s = str(eq)
        assert str(eq.id) in s

    @given(eq=equations())
    def test_properties_are_valid_enums(self, eq: EquationEntry):
        """All properties are valid Property enum members."""
        for p in eq.properties:
            assert isinstance(p, Property)

    def test_synthetic_equations_unique_ids(self):
        """All synthetic equations have unique IDs."""
        ids = [eq.id for eq in SYNTHETIC_EQUATIONS]
        assert len(ids) == len(set(ids)), "Duplicate IDs in SYNTHETIC_EQUATIONS"

    def test_synthetic_equations_all_have_properties(self):
        """Every synthetic equation has at least one property."""
        for eq in SYNTHETIC_EQUATIONS:
            assert len(eq.properties) >= 1, f"E{eq.id} has no properties"


# ── Feature: Problem invariants ─────────────────────────────────
# Given: ANY Problem
# Then: Structure is consistent


@pytest.mark.property
class TestProblemInvariants:
    """Scenario: Problem fields are well-formed."""

    @given(p=problems())
    def test_to_dict_roundtrip(self, p: Problem):
        """to_dict preserves all fields."""
        d = p.to_dict()
        assert d["id"] == p.id
        assert d["equation_1"] == p.equation_1_id
        assert d["equation_2"] == p.equation_2_id
        assert d["answer"] == p.answer
        assert d["difficulty"] == p.difficulty.value

    @given(p=problems())
    def test_str_contains_equation_ids(self, p: Problem):
        """String representation contains both equation IDs."""
        s = str(p)
        assert str(p.equation_1_id) in s
        assert str(p.equation_2_id) in s

    @given(p=problems())
    def test_difficulty_is_valid(self, p: Problem):
        """Difficulty is either 'regular' or 'hard'."""
        assert p.difficulty in (Difficulty.REGULAR, Difficulty.HARD)

    @given(p=problems())
    def test_answer_is_optional_bool(self, p: Problem):
        """Answer is None or bool."""
        assert p.answer is None or isinstance(p.answer, bool)


# ── Feature: Counterexample invariants ──────────────────────────
# Given: ANY Counterexample
# Then: Structure includes valid magma


@pytest.mark.property
class TestCounterexampleInvariants:
    """Scenario: Counterexample structure is consistent."""

    @given(m=magmas(max_size=3))
    def test_counterexample_to_dict_includes_magma(self, m: Magma):
        """to_dict includes magma carrier and operation."""
        cx = Counterexample(
            premise_id=1,
            conclusion_id=2,
            magma=m,
            red_flags={"test"},
            assignment={"x": 0},
        )
        d = cx.to_dict()

        assert "magma" in d
        assert "carrier" in d["magma"]
        assert "operation" in d["magma"]
        assert d["magma"]["carrier"] == m.elements
        assert len(d["magma"]["operation"]) == m.size * m.size

    @given(m=magmas(max_size=3))
    def test_counterexample_operation_entries(self, m: Magma):
        """Each operation entry has a, b, and result fields."""
        cx = Counterexample(premise_id=1, conclusion_id=2, magma=m)
        d = cx.to_dict()

        for entry in d["magma"]["operation"]:
            assert "a" in entry
            assert "b" in entry
            assert "result" in entry
            assert 0 <= entry["a"] < m.size
            assert 0 <= entry["b"] < m.size
            assert 0 <= entry["result"] < m.size


# ── Feature: Property enum exhaustiveness ───────────────────────


@pytest.mark.property
class TestPropertyEnum:
    """Scenario: Property enum covers all expected values."""

    def test_all_properties_have_string_values(self):
        """Every Property has a non-empty string value."""
        for p in Property:
            assert isinstance(p.value, str)
            assert len(p.value) > 0

    def test_property_values_are_unique(self):
        """No two properties share the same string value."""
        values = [p.value for p in Property]
        assert len(values) == len(set(values))

    def test_known_properties_exist(self):
        """Essential properties are defined."""
        names = {p.value for p in Property}
        assert "associative" in names
        assert "commutative" in names
        assert "idempotent" in names
        assert "bidentity" in names

    @given(p=st.sampled_from(list(Property)))
    def test_property_roundtrip_via_value(self, p: Property):
        """Property(p.value) == p for all properties."""
        assert Property(p.value) == p
