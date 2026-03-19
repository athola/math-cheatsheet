"""Tests for parsers module."""

import json

import pytest

from data_models import Equation, Problem, Property
from parsers import (
    ParseError,
    parse_equations,
    parse_problems,
    validate_equations,
    validate_problems,
)


@pytest.fixture
def tmp_equations_json(tmp_path):
    data = {
        "equations": [
            {
                "id": 1,
                "latex": "x*y=y*x",
                "name": "Commutativity",
                "properties": ["commutative"],
                "description": "Commutative property",
            },
            {
                "id": 2,
                "latex": "(x*y)*z=x*(y*z)",
                "name": "Associativity",
                "properties": ["associative"],
                "description": "Associative property",
            },
        ]
    }
    p = tmp_path / "equations.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def tmp_equations_txt(tmp_path):
    content = """# Test equations
1 | Commutativity | x*y=y*x | [commutative]
2 | Associativity | (x*y)*z=x*(y*z) | [associative]
"""
    p = tmp_path / "equations.txt"
    p.write_text(content)
    return p


@pytest.fixture
def tmp_problems_json(tmp_path):
    data = {
        "problems": [
            {"id": 1, "equation_1": 1, "equation_2": 2, "answer": False, "difficulty": "regular"},
            {"id": 2, "equation_1": 2, "equation_2": 1, "answer": False, "difficulty": "hard"},
        ]
    }
    p = tmp_path / "problems.json"
    p.write_text(json.dumps(data))
    return p


class TestParseEquations:
    def test_parse_json(self, tmp_equations_json):
        equations = parse_equations(str(tmp_equations_json))
        assert len(equations) == 2
        assert equations[0].name == "Commutativity"
        assert Property.COMMUTATIVE in equations[0].properties

    def test_parse_txt(self, tmp_equations_txt):
        equations = parse_equations(str(tmp_equations_txt))
        assert len(equations) == 2
        assert equations[0].id == 1

    def test_file_not_found(self):
        with pytest.raises(ParseError, match="File not found"):
            parse_equations("/nonexistent/file.json")

    def test_unsupported_format(self, tmp_path):
        p = tmp_path / "equations.csv"
        p.write_text("data")
        with pytest.raises(ParseError, match="Unsupported file format"):
            parse_equations(str(p))

    def test_unknown_properties_skipped(self, tmp_path):
        data = {
            "equations": [
                {
                    "id": 1,
                    "latex": "",
                    "name": "test",
                    "properties": ["associative", "unknown_prop"],
                }
            ]
        }
        p = tmp_path / "eq.json"
        p.write_text(json.dumps(data))
        equations = parse_equations(str(p))
        assert len(equations[0].properties) == 1


class TestParseProblems:
    def test_parse(self, tmp_problems_json):
        problems = parse_problems(str(tmp_problems_json))
        assert len(problems) == 2
        assert problems[0].answer is False
        assert problems[1].difficulty == "hard"

    def test_file_not_found(self):
        with pytest.raises(ParseError):
            parse_problems("/nonexistent/problems.json")


class TestValidateEquations:
    def test_valid_equations(self):
        equations = [
            Equation(id=1, latex="", name="A", properties=[Property.ASSOCIATIVE]),
            Equation(id=2, latex="", name="B", properties=[Property.COMMUTATIVE]),
        ]
        result = validate_equations(equations)
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    def test_duplicate_ids(self):
        equations = [
            Equation(id=1, latex="", name="A", properties=[Property.ASSOCIATIVE]),
            Equation(id=1, latex="", name="B", properties=[Property.COMMUTATIVE]),
        ]
        result = validate_equations(equations)
        assert len(result["errors"]) == 1
        assert "Duplicate" in result["errors"][0]

    def test_no_properties_warning(self):
        equations = [
            Equation(id=1, latex="", name="A", properties=[]),
        ]
        result = validate_equations(equations)
        assert len(result["warnings"]) == 1


class TestValidateProblems:
    def test_valid_problems(self):
        problems = [
            Problem(id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty="regular"),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert len(result["errors"]) == 0

    def test_out_of_range_equation(self):
        problems = [
            Problem(id=1, equation_1_id=99, equation_2_id=2, answer=True, difficulty="regular"),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert len(result["errors"]) == 1
        assert "out of range" in result["errors"][0]
