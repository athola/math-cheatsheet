"""Regression tests for the 2026-06 full-review findings.

Each test class is tagged with the finding id from the review report
(B1-B9 bug/API/test findings, H1/H2/M1 math-soundness findings) so a
failure points straight back at the issue it guards.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from competition_evaluator import _load_problems
from decision_procedure import DecisionProcedure
from equation_analyzer import ImplicationVerdict, analyze_implication
from equation_analyzer import parse_equation as ea_parse
from equation_parser_utils import tokenize_equation
from etp_equations import ETPEquations, parse_equation
from implication_oracle import ImplicationOracle
from llm_evaluator import parse_verdict
from term import parse_equation_terms, parse_term


def _equations(tmp_path: Path, lines: list[str]) -> ETPEquations:
    p = tmp_path / "equations.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ETPEquations(p)


class TestB1SubstitutionBothDirections:
    """is_substitution_instance must try both variable-merge directions."""

    def test_merge_into_later_variable(self, tmp_path: Path):
        # H (eq1): x ◇ y = x  (left projection, sorted vars [x, y])
        # T (eq2): y ◇ y = y  obtained by x := y — survivor is the *later* var,
        # the direction the buggy single-direction loop never tried.
        eqs = _equations(tmp_path, ["x ◇ y = x", "y ◇ y = y"])
        assert eqs.is_substitution_instance(1, 2) is True

    def test_merge_into_earlier_variable_still_works(self, tmp_path: Path):
        # H (eq1): x ◇ y = x ; T (eq2): x ◇ x = x  via y := x (earlier survivor)
        eqs = _equations(tmp_path, ["x ◇ y = x", "x ◇ x = x"])
        assert eqs.is_substitution_instance(1, 2) is True


class TestB2FrozensetVariables:
    """Equation.variables must actually be an immutable frozenset."""

    def test_variables_is_frozenset(self):
        eq = parse_equation(1, "x ◇ y = y ◇ x")
        assert isinstance(eq.variables, frozenset)


class TestB5CollapseDepthGreaterThanOne:
    """is_collapse_structural must catch collapses with RHS depth > 1."""

    def test_deep_collapse_detected(self, tmp_path: Path):
        # x = (y ◇ z) ◇ w : LHS var x absent from RHS -> forces |M|=1.
        eqs = _equations(tmp_path, ["x = (y ◇ z) ◇ w"])
        assert eqs.is_collapse_structural(1) is True
        assert eqs.classify_structural(1) == "collapse"


class TestB4ParseVerdict:
    """parse_verdict must not be fooled by substrings like 'NOT TRUE'."""

    def test_not_true_is_not_read_as_true(self):
        assert parse_verdict("VERDICT: NOT TRUE") is not True

    def test_plain_true(self):
        assert parse_verdict("VERDICT: TRUE") is True

    def test_plain_false(self):
        assert parse_verdict("VERDICT: FALSE") is False

    def test_trailing_punctuation_tolerated(self):
        assert parse_verdict("VERDICT: TRUE.") is True


class TestB7Tokenizer:
    """tokenize_equation must not silently drop characters."""

    def test_alphanumeric_variable_preserved(self):
        assert tokenize_equation("x1 ◇ y = y ◇ x1") == [
            "x1",
            "*",
            "y",
            "=",
            "y",
            "*",
            "x1",
        ]

    def test_unexpected_char_raises(self):
        with pytest.raises(ValueError):
            tokenize_equation("x $ y")


class TestB7ParserAlphanumericVars:
    """The parser must accept the alphanumeric variable tokens the tokenizer
    emits (full-review 2026-07-12 blocker B1: _parse_primary still gated on
    str.isalpha, rejecting tokens like 'x1' that tokenize_equation produces).
    """

    def test_parse_term_accepts_alphanumeric_variable(self):
        term = parse_term("x1 ◇ y")
        assert "x1" in term.variables()

    def test_parse_equation_terms_accepts_alphanumeric_variable(self):
        lhs, rhs = parse_equation_terms("x1 ◇ y = y ◇ x1")
        assert lhs.variables() == rhs.variables() == {"x1", "y"}

    def test_etp_equations_parse_alphanumeric_variable(self, tmp_path: Path):
        eqs = _equations(tmp_path, ["x1 ◇ y = y ◇ x1"])
        assert eqs.classify_structural(1) == "balanced"


class TestB3LoadProblems:
    """_load_problems must reject malformed records instead of producing None ids."""

    def test_missing_ids_raises(self, tmp_path: Path):
        p = tmp_path / "probs.jsonl"
        p.write_text(json.dumps({"answer": True}) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            _load_problems(p)

    def test_missing_answer_raises(self, tmp_path: Path):
        p = tmp_path / "probs.jsonl"
        p.write_text(json.dumps({"hypothesis_id": 1, "target_id": 2}) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            _load_problems(p)

    def test_valid_record_loads(self, tmp_path: Path):
        p = tmp_path / "probs.jsonl"
        p.write_text(
            json.dumps({"hypothesis_id": 1, "target_id": 2, "answer": True}) + "\n",
            encoding="utf-8",
        )
        probs = _load_problems(p)
        assert probs[0]["hypothesis_id"] == 1
        assert probs[0]["target_id"] == 2
        assert probs[0]["answer"] is True


class TestB8ParseErrorFallthrough:
    """A parse failure in structural analysis must not fabricate a structural FALSE."""

    def test_parse_error_falls_through_to_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        eqs = _equations(tmp_path, ["x ◇ y = y ◇ x", "x ◇ y = x"])
        proc = DecisionProcedure(eqs, oracle=None)

        import decision_procedure as dp

        def boom(_text: str):
            raise ValueError("synthetic parse failure")

        monkeypatch.setattr(dp, "ea_parse_equation", boom)
        result = proc.predict(1, 2)
        # No proof of non-implication exists -> honest default, not "P5c-structural".
        assert result.phase == "P6-default"


class TestB9ClassifyNotMislabeledTautology:
    """A row with exactly one true entry must not be called a 'tautology'."""

    def test_single_implication_labeled_self_only(self, tmp_path: Path):
        import csv

        csv_path = tmp_path / "implications.csv"
        # Eq2 implies only itself (diagonal) -> row count 1, but it is NOT x=x.
        matrix = [
            [3, 3, 3],  # Eq1 collapse (implies all)
            [-3, 3, -3],  # Eq2 implies only itself
            [-3, -3, 3],  # Eq3 implies only itself
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for row in matrix:
                w.writerow(row)
        oracle = ImplicationOracle(csv_path)
        assert oracle.classify(2) == "implies_self_only"


class TestH1NewVarNotUnsoundFalse:
    """A congruence consequence with a fresh target variable must not be FALSE."""

    def test_congruence_consequence_not_false(self):
        # H: commutativity. T introduces z but holds in every commutative magma
        # by congruence, so H |= T. The old Phase 2 wrongly returned FALSE.
        h = ea_parse("x ◇ y = y ◇ x")
        t = ea_parse("(x ◇ y) ◇ z = (y ◇ x) ◇ z")
        result = analyze_implication(h, t)
        assert result.verdict != ImplicationVerdict.FALSE


class TestH2DepthHeuristicNotUnsoundFalse:
    """A deep congruence consequence must not be refuted by a depth heuristic."""

    def test_deep_congruence_consequence_not_false(self):
        # T has depth 3 but holds in every commutative magma (congruence), so
        # H |= T. The old Phase 7b depth rule wrongly returned FALSE.
        h = ea_parse("x ◇ y = y ◇ x")
        t = ea_parse("x ◇ (y ◇ (x ◇ y)) = x ◇ (y ◇ (y ◇ x))")
        result = analyze_implication(h, t)
        assert result.verdict != ImplicationVerdict.FALSE


class TestM1HeuristicFalseIsLabeled:
    """The new-variable heuristic must not run before sound TRUE-provers."""

    def test_equiv_class_true_beats_new_var_heuristic(self, tmp_path: Path):
        import csv

        eq_path = tmp_path / "equations.txt"
        # Eq1: commutativity ; Eq2: x◇y=z carries a fresh var z relative to Eq1 ;
        # Eq3: a tautology to keep neither row all-true (so neither is collapse).
        eq_path.write_text("x ◇ y = y ◇ x\nx ◇ y = z\nx = x\n", encoding="utf-8")
        csv_path = tmp_path / "implications.csv"
        # Eq1 and Eq2 share an identical (non-collapse) row -> same class -> sound
        # mutual implication, which must beat the new-variable heuristic.
        matrix = [[3, 3, -3], [3, 3, -3], [-3, -3, 3]]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for row in matrix:
                w.writerow(row)
        eqs = ETPEquations(eq_path)
        oracle = ImplicationOracle(csv_path)
        proc = DecisionProcedure(eqs, oracle)
        result = proc.predict(1, 2)
        # Eq2 has a "new" variable z, but the sound equivalence-class prover must
        # win over the new-variable heuristic and predict TRUE.
        assert result.prediction is True
        assert result.phase == "P5a-equiv-class"
