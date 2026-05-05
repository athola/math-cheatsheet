"""Tests for data_models module."""

import pytest

from data_models import (
    SYNTHETIC_EQUATIONS,
    AlgebraicEquation,
    Counterexample,
    Equation,
    Magma,
    Problem,
    Property,
)


class TestProperty:
    def test_property_values(self):
        assert Property.ASSOCIATIVE.value == "associative"
        assert Property.COMMUTATIVE.value == "commutative"

    def test_all_properties_have_unique_values(self):
        values = [p.value for p in Property]
        assert len(values) == len(set(values))


class TestEquation:
    def test_creation(self):
        eq = Equation(id=1, latex="x*y=y*x", name="comm", properties=[Property.COMMUTATIVE])
        assert eq.id == 1
        assert eq.name == "comm"

    def test_str(self):
        eq = Equation(id=42, latex="", name="Test", properties=[])
        assert str(eq) == "E42: Test"

    def test_to_dict(self):
        eq = Equation(
            id=1,
            latex="x*y",
            name="test",
            properties=[Property.ASSOCIATIVE, Property.COMMUTATIVE],
            description="desc",
        )
        d = eq.to_dict()
        assert d["id"] == 1
        assert d["properties"] == ["associative", "commutative"]
        assert d["description"] == "desc"

    def test_default_description(self):
        eq = Equation(id=1, latex="", name="", properties=[])
        assert eq.description == ""


class TestProblem:
    def test_creation(self):
        p = Problem(id=1, equation_1_id=3, equation_2_id=5, answer=True, difficulty="regular")
        assert p.answer is True
        assert p.difficulty == "regular"

    def test_str(self):
        p = Problem(id=1, equation_1_id=3, equation_2_id=5, answer=None, difficulty="hard")
        assert "E3" in str(p)
        assert "E5" in str(p)

    def test_to_dict(self):
        p = Problem(id=1, equation_1_id=3, equation_2_id=5, answer=False, difficulty="hard")
        d = p.to_dict()
        assert d["equation_1"] == 3
        assert d["answer"] is False


class TestMagma:
    @pytest.fixture
    def xor_magma(self):
        """Z/2Z under XOR: associative, commutative, has identity 0."""
        return Magma(size=2, operation=[[0, 1], [1, 0]])

    @pytest.fixture
    def and_magma(self):
        """Z/2Z under AND: associative, commutative, has identity 1."""
        return Magma(size=2, operation=[[0, 0], [0, 1]])

    @pytest.fixture
    def non_assoc_magma(self):
        """A non-associative magma of size 3."""
        return Magma(size=3, operation=[[0, 2, 1], [2, 1, 0], [1, 0, 2]])

    def test_op(self, xor_magma):
        assert xor_magma.op(0, 0) == 0
        assert xor_magma.op(0, 1) == 1
        assert xor_magma.op(1, 1) == 0

    def test_is_associative(self, xor_magma, non_assoc_magma):
        assert xor_magma.is_associative() is True
        assert non_assoc_magma.is_associative() is False

    def test_is_commutative(self, xor_magma):
        assert xor_magma.is_commutative() is True

    def test_has_identity(self, xor_magma, and_magma):
        assert xor_magma.has_identity() == 0
        assert and_magma.has_identity() == 1

    def test_is_idempotent(self, and_magma, xor_magma):
        # AND: 0*0=0, 1*1=1 — idempotent
        assert and_magma.is_idempotent() is True
        # XOR: 0*0=0 but 1*1=0 — not idempotent
        assert xor_magma.is_idempotent() is False
        idem = Magma(size=1, operation=[[0]])
        assert idem.is_idempotent() is True

    def test_cayley_table_str(self, xor_magma):
        s = xor_magma.cayley_table_str()
        assert "0" in s
        assert "1" in s

    def test_to_dict_operation(self, xor_magma):
        d = xor_magma.to_dict_operation()
        assert d["0,0"] == 0
        assert d["0,1"] == 1
        assert d["1,0"] == 1
        assert d["1,1"] == 0

    def test_from_dict_operation_roundtrip(self, xor_magma):
        # from_dict_operation expects tuple keys (counterexample_db format)
        d = {
            (a, b): xor_magma.operation[a][b]
            for a in range(xor_magma.size)
            for b in range(xor_magma.size)
        }
        rebuilt = Magma.from_dict_operation(xor_magma.elements, d)
        assert rebuilt.operation == xor_magma.operation
        assert rebuilt.size == xor_magma.size

    def test_to_tla(self, xor_magma):
        tla = xor_magma.to_tla()
        assert "<<0, 0>> |-> 0" in tla
        assert "<<0, 1>> |-> 1" in tla

    def test_elements_is_computed_from_size(self):
        """Regression #39: elements is derived from size, not a stored field."""
        m = Magma(size=3, operation=[[0, 1, 2], [1, 2, 0], [2, 0, 1]])
        assert tuple(m.elements) == (0, 1, 2)

    def test_elements_is_immutable_tuple(self):
        """Regression #39: elements returns a tuple so callers can't mutate it."""
        m = Magma(size=2, operation=[[0, 1], [1, 0]])
        assert isinstance(m.elements, tuple)


class TestMagmaValidation:
    """Error-path tests for Magma.__post_init__ and from_dict_operation (#49).

    The validation guards in data_models.py existed since PR #36 but had no
    direct error-path tests — a full revert of __post_init__ passed every
    other test. These tests pin each guard to a specific assertion.
    """

    def test_zero_size_rejected(self):
        with pytest.raises(ValueError, match="size must be at least 1"):
            Magma(size=0, operation=[])

    def test_negative_size_rejected(self):
        with pytest.raises(ValueError, match="size must be at least 1"):
            Magma(size=-1, operation=[])

    def test_wrong_row_count_rejected(self):
        with pytest.raises(ValueError, match="must have 2 rows, got 1"):
            Magma(size=2, operation=[[0, 1]])

    def test_too_many_rows_rejected(self):
        with pytest.raises(ValueError, match="must have 2 rows, got 3"):
            Magma(size=2, operation=[[0, 1], [1, 0], [0, 0]])

    def test_short_row_rejected(self):
        with pytest.raises(ValueError, match=r"Row 0 must have 2 columns, got 1"):
            Magma(size=2, operation=[[0], [1, 0]])

    def test_long_row_rejected(self):
        with pytest.raises(ValueError, match=r"Row 1 must have 2 columns, got 3"):
            Magma(size=2, operation=[[0, 1], [1, 0, 0]])

    def test_negative_cell_value_rejected(self):
        with pytest.raises(ValueError, match=r"Entry \[0\]\[0\]=-1 out of range"):
            Magma(size=2, operation=[[-1, 0], [0, 1]])

    def test_out_of_range_cell_value_rejected(self):
        with pytest.raises(ValueError, match=r"Entry \[1\]\[0\]=2 out of range"):
            Magma(size=2, operation=[[0, 1], [2, 1]])

    def test_from_dict_operation_non_contiguous_carrier_rejected(self):
        op_dict = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
        with pytest.raises(ValueError, match="carrier must be range"):
            Magma.from_dict_operation([0, 2], op_dict)

    def test_from_dict_operation_missing_entries_rejected(self):
        with pytest.raises(ValueError, match="Missing operation entries"):
            Magma.from_dict_operation([0, 1], {(0, 0): 0, (1, 1): 0})

    def test_valid_magma_constructs_without_error(self):
        """Sanity: known-good inputs still work after the validation guards."""
        m = Magma(size=2, operation=[[0, 1], [1, 0]])
        assert m.size == 2


class TestMagmaImmutability:
    """S8 (#55): Magma is frozen and the operation table is tuple-of-tuples,
    so a constructed magma cannot have its Cayley table mutated afterwards.
    """

    def test_magma_field_assignment_rejected(self):
        m = Magma(size=2, operation=[[0, 1], [1, 0]])
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            m.size = 99  # type: ignore[misc]

    def test_operation_table_is_tuple_of_tuples(self):
        m = Magma(size=2, operation=[[0, 1], [1, 0]])
        assert isinstance(m.operation, tuple)
        assert all(isinstance(row, tuple) for row in m.operation)

    def test_operation_row_mutation_rejected(self):
        m = Magma(size=2, operation=[[0, 1], [1, 0]])
        with pytest.raises(TypeError):
            m.operation[0][0] = 99  # type: ignore[index]

    def test_magma_is_hashable(self):
        # Frozen + tuple table → hashable; can live in a set or dict key.
        m1 = Magma(size=2, operation=[[0, 1], [1, 0]])
        m2 = Magma(size=2, operation=[[0, 1], [1, 0]])
        assert hash(m1) == hash(m2)
        assert {m1, m2} == {m1}  # equal magmas dedupe


class TestFromDictOperationCarrierOptional:
    """S9 (#55): carrier=None infers size from op_dict, removing the
    redundant parameter for new callers while keeping backward compat.
    """

    def test_carrier_none_infers_size(self):
        op_dict = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
        m = Magma.from_dict_operation(None, op_dict)
        assert m.size == 2
        assert m.operation == ((0, 1), (1, 0))

    def test_carrier_none_with_empty_dict_rejected(self):
        with pytest.raises(ValueError, match="op_dict is empty"):
            Magma.from_dict_operation(None, {})

    def test_carrier_passed_must_match_inferred_size(self):
        # When the caller does pass a carrier, the contiguous-range
        # constraint still applies so legacy code paths fail the same way.
        op_dict = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
        with pytest.raises(ValueError, match="carrier must be range"):
            Magma.from_dict_operation([0, 5], op_dict)


class TestAlgebraicEquation:
    def test_creation(self):
        eq = AlgebraicEquation(id=1, lhs="x*y", rhs="y*x")
        assert str(eq) == "x*y = y*x"


class TestCounterexample:
    def test_creation(self):
        magma = Magma(size=2, operation=[[0, 1], [1, 0]])
        ce = Counterexample(
            premise_id=1, conclusion_id=2, magma=magma, red_flags={"non_commutative"}
        )
        assert ce.premise_id == 1
        assert "non_commutative" in ce.red_flags

    def test_to_dict(self):
        magma = Magma(size=2, operation=[[0, 0], [0, 1]])
        ce = Counterexample(premise_id=1, conclusion_id=2, magma=magma)
        d = ce.to_dict()
        assert d["premise_id"] == 1
        assert len(d["magma"]["operation"]) == 4


class TestSyntheticEquations:
    def test_synthetic_equations_exist(self):
        assert len(SYNTHETIC_EQUATIONS) == 16

    def test_all_have_ids(self):
        ids = [eq.id for eq in SYNTHETIC_EQUATIONS]
        assert len(ids) == len(set(ids))

    def test_all_have_properties(self):
        for eq in SYNTHETIC_EQUATIONS:
            assert len(eq.properties) > 0
