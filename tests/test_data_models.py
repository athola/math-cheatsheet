"""Tests for data_models module."""

from data_models import (
    SYNTHETIC_EQUATIONS,
    AlgebraicEquation,
    Counterexample,
    Difficulty,
    EquationEntry,
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
        eq = EquationEntry(id=1, latex="x*y=y*x", name="comm", properties=[Property.COMMUTATIVE])
        assert eq.id == 1
        assert eq.name == "comm"

    def test_str(self):
        eq = EquationEntry(id=42, latex="", name="Test", properties=[])
        assert str(eq) == "E42: Test"

    def test_to_dict(self):
        eq = EquationEntry(
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
        eq = EquationEntry(id=1, latex="", name="", properties=[])
        assert eq.description == ""


class TestProblem:
    def test_creation(self):
        p = Problem(
            id=1, equation_1_id=3, equation_2_id=5, answer=True, difficulty=Difficulty.REGULAR
        )
        assert p.answer is True
        assert p.difficulty == Difficulty.REGULAR

    def test_str(self):
        p = Problem(id=1, equation_1_id=3, equation_2_id=5, answer=None, difficulty=Difficulty.HARD)
        assert "E3" in str(p)
        assert "E5" in str(p)

    def test_to_dict(self):
        p = Problem(
            id=1, equation_1_id=3, equation_2_id=5, answer=False, difficulty=Difficulty.HARD
        )
        d = p.to_dict()
        assert d["equation_1"] == 3
        assert d["answer"] is False


class TestMagma:
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
        idem = Magma(size=1, elements=[0], operation=[[0]])
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


class TestAlgebraicEquation:
    def test_creation(self):
        eq = AlgebraicEquation(id=1, lhs="x*y", rhs="y*x")
        assert str(eq) == "x*y = y*x"


class TestCounterexample:
    def test_creation(self):
        magma = Magma(size=2, elements=[0, 1], operation=[[0, 1], [1, 0]])
        ce = Counterexample(
            premise_id=1, conclusion_id=2, magma=magma, red_flags={"non_commutative"}
        )
        assert ce.premise_id == 1
        assert "non_commutative" in ce.red_flags

    def test_to_dict(self):
        magma = Magma(size=2, elements=[0, 1], operation=[[0, 0], [0, 1]])
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
