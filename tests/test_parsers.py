"""Tests for parsers module."""

import json

import pytest

from data_models import Difficulty, EquationEntry, Problem, Property
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
        assert problems[1].difficulty == Difficulty.HARD

    def test_file_not_found(self):
        with pytest.raises(ParseError):
            parse_problems("/nonexistent/problems.json")


class TestValidateEquations:
    def test_valid_equations(self):
        equations = [
            EquationEntry(id=1, latex="", name="A", properties=[Property.ASSOCIATIVE]),
            EquationEntry(id=2, latex="", name="B", properties=[Property.COMMUTATIVE]),
        ]
        result = validate_equations(equations)
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    def test_duplicate_ids(self):
        equations = [
            EquationEntry(id=1, latex="", name="A", properties=[Property.ASSOCIATIVE]),
            EquationEntry(id=1, latex="", name="B", properties=[Property.COMMUTATIVE]),
        ]
        result = validate_equations(equations)
        assert len(result["errors"]) == 1
        assert "Duplicate" in result["errors"][0]

    def test_no_properties_warning(self):
        equations = [
            EquationEntry(id=1, latex="", name="A", properties=[]),
        ]
        result = validate_equations(equations)
        assert len(result["warnings"]) == 1


class TestValidateProblems:
    def test_valid_problems(self):
        problems = [
            Problem(
                id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty=Difficulty.REGULAR
            ),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert len(result["errors"]) == 0

    def test_out_of_range_equation(self):
        problems = [
            Problem(
                id=1, equation_1_id=99, equation_2_id=2, answer=True, difficulty=Difficulty.REGULAR
            ),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert len(result["errors"]) == 1
        assert "out of range" in result["errors"][0]

    def test_duplicate_problem_ids(self):
        problems = [
            Problem(
                id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty=Difficulty.REGULAR
            ),
            Problem(
                id=1, equation_1_id=3, equation_2_id=4, answer=False, difficulty=Difficulty.REGULAR
            ),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert any("Duplicate" in e for e in result["errors"])

    def test_difficulty_counts(self):
        problems = [
            Problem(
                id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty=Difficulty.REGULAR
            ),
            Problem(
                id=2, equation_1_id=1, equation_2_id=3, answer=False, difficulty=Difficulty.HARD
            ),
            Problem(
                id=3, equation_1_id=1, equation_2_id=4, answer=True, difficulty=Difficulty.HARD
            ),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert result["stats"]["by_difficulty"]["regular"] == 1
        assert result["stats"]["by_difficulty"]["hard"] == 2

    def test_with_answer_count(self):
        problems = [
            Problem(
                id=1, equation_1_id=1, equation_2_id=2, answer=True, difficulty=Difficulty.REGULAR
            ),
            Problem(
                id=2, equation_1_id=1, equation_2_id=3, answer=None, difficulty=Difficulty.REGULAR
            ),
            Problem(
                id=3, equation_1_id=1, equation_2_id=4, answer=False, difficulty=Difficulty.REGULAR
            ),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert result["stats"]["with_answer"] == 2

    def test_eq2_out_of_range(self):
        problems = [
            Problem(
                id=1, equation_1_id=1, equation_2_id=99, answer=True, difficulty=Difficulty.REGULAR
            ),
        ]
        result = validate_problems(problems, max_equation_id=10)
        assert len(result["errors"]) == 1
        assert "equation_2_id" in result["errors"][0]


class TestParseTxtEdgeCases:
    """Edge cases for the _parse_equations_txt path."""

    def test_malformed_lines_skipped(self, tmp_path):
        content = """# header
1 | Good | x*y | [associative]
bad line without pipes
2 | Also Good | x*z | [commutative]
"""
        p = tmp_path / "eq.txt"
        p.write_text(content)
        equations = parse_equations(str(p))
        assert len(equations) == 2

    def test_non_numeric_id_skipped(self, tmp_path):
        content = "abc | Bad | x | [associative]\n1 | Good | x | [commutative]\n"
        p = tmp_path / "eq.txt"
        p.write_text(content)
        equations = parse_equations(str(p))
        assert len(equations) == 1
        assert equations[0].id == 1

    def test_unknown_property_in_txt_skipped(self, tmp_path):
        content = "1 | Test | x | [associative,totally_fake_property]\n"
        p = tmp_path / "eq.txt"
        p.write_text(content)
        equations = parse_equations(str(p))
        assert len(equations) == 1
        assert len(equations[0].properties) == 1

    def test_empty_properties_bracket(self, tmp_path):
        content = "1 | Test | x | []\n"
        p = tmp_path / "eq.txt"
        p.write_text(content)
        equations = parse_equations(str(p))
        assert len(equations) == 1
        assert len(equations[0].properties) == 0

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("")
        equations = parse_equations(str(p))
        assert len(equations) == 0

    def test_problem_without_answer(self, tmp_path):
        data = {
            "problems": [
                {"id": 1, "equation_1": 1, "equation_2": 2},
            ]
        }
        p = tmp_path / "probs.json"
        p.write_text(json.dumps(data))
        problems = parse_problems(str(p))
        assert problems[0].answer is None
        assert problems[0].difficulty == Difficulty.REGULAR


class TestValidateEquationsStats:
    def test_property_count_stats(self):
        equations = [
            EquationEntry(id=1, latex="", name="A", properties=[Property.ASSOCIATIVE]),
            EquationEntry(
                id=2, latex="", name="B", properties=[Property.ASSOCIATIVE, Property.COMMUTATIVE]
            ),
        ]
        result = validate_equations(equations)
        assert result["stats"]["by_property"]["associative"] == 2
        assert result["stats"]["by_property"]["commutative"] == 1
        assert result["stats"]["total"] == 2
