"""Tests for scripts/generate_synthetic_data.py.

Feature: Generate synthetic competition data for equational theories
    As a developer without access to real competition data
    I want to generate representative synthetic equations and problems
    So that I can develop and test the decision procedure locally
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from generate_synthetic_data import (  # noqa: E402
    generate_extended_equations,
    generate_implication_knowledge,
    generate_synthetic_problems,
    save_synthetic_data,
)

from data_models import SYNTHETIC_EQUATIONS  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────────
# generate_extended_equations
# ──────────────────────────────────────────────────────────────────────────────


class TestGenerateExtendedEquations:
    """Feature: generate_extended_equations produces equations up to requested count."""

    @pytest.mark.unit
    def test_returns_requested_count(self):
        """
        Scenario: Request 50 equations
        Given count=50
        When generate_extended_equations is called
        Then exactly 50 equations are returned
        """
        assert len(generate_extended_equations(count=50)) == 50

    @pytest.mark.unit
    def test_starts_with_base_synthetic_equations(self):
        """
        Scenario: First entries are the canonical SYNTHETIC_EQUATIONS
        Given count > len(SYNTHETIC_EQUATIONS)
        When generate_extended_equations is called
        Then the first len(SYNTHETIC_EQUATIONS) entries match SYNTHETIC_EQUATIONS
        """
        base_count = len(SYNTHETIC_EQUATIONS)
        equations = generate_extended_equations(count=base_count + 10)
        for i, base_eq in enumerate(SYNTHETIC_EQUATIONS):
            assert equations[i].id == base_eq.id
            assert equations[i].name == base_eq.name

    @pytest.mark.unit
    def test_all_equations_have_at_least_one_property(self):
        """
        Scenario: Every generated equation has at least one property
        Given count=100
        When generate_extended_equations is called
        Then every equation has len(properties) >= 1
        """
        for eq in generate_extended_equations(count=100):
            assert len(eq.properties) >= 1, f"Equation {eq.id} has no properties"

    @pytest.mark.unit
    def test_all_ids_are_unique(self):
        """
        Scenario: IDs are unique across all generated equations
        Given count=100
        When generate_extended_equations is called
        Then all IDs are distinct
        """
        equations = generate_extended_equations(count=100)
        ids = [eq.id for eq in equations]
        assert len(ids) == len(set(ids))

    @pytest.mark.unit
    def test_count_at_base_size_returns_only_base(self):
        """
        Scenario: count == len(SYNTHETIC_EQUATIONS) returns exactly the base set
        Given count = len(SYNTHETIC_EQUATIONS)
        When generate_extended_equations is called
        Then no generated equations are appended
        """
        base_count = len(SYNTHETIC_EQUATIONS)
        equations = generate_extended_equations(count=base_count)
        assert len(equations) == base_count


# ──────────────────────────────────────────────────────────────────────────────
# generate_implication_knowledge
# ──────────────────────────────────────────────────────────────────────────────


class TestGenerateImplicationKnowledge:
    """Feature: generate_implication_knowledge encodes known mathematical implications."""

    @pytest.mark.unit
    def test_returns_non_empty_list_of_triples(self):
        """
        Scenario: Returns a non-empty list of (eq1, eq2, bool) tuples
        Given no arguments
        When generate_implication_knowledge is called
        Then a non-empty list of 3-tuples is returned
        """
        implications = generate_implication_knowledge()
        assert len(implications) > 0
        for item in implications:
            eq1_id, eq2_id, implies = item
            assert isinstance(eq1_id, int)
            assert isinstance(eq2_id, int)
            assert isinstance(implies, bool)

    @pytest.mark.unit
    def test_group_implies_associativity(self):
        """
        Scenario: Group axioms (eq 13) imply associativity (eq 1)
        Given implication knowledge
        When I look for (13, 1, True)
        Then it is present
        """
        assert (13, 1, True) in generate_implication_knowledge()

    @pytest.mark.unit
    def test_associativity_does_not_imply_commutativity(self):
        """
        Scenario: Associativity alone does not imply commutativity
        Given implication knowledge
        When I look for (1, 2, False)
        Then it is present
        """
        assert (1, 2, False) in generate_implication_knowledge()

    @pytest.mark.unit
    def test_has_both_true_and_false_implications(self):
        """
        Scenario: Knowledge contains both implications and non-implications
        Given implication knowledge
        When I check for True and False entries
        Then both exist
        """
        implications = generate_implication_knowledge()
        assert any(imp for _, _, imp in implications), "No True implications found"
        assert any(not imp for _, _, imp in implications), "No False implications found"


# ──────────────────────────────────────────────────────────────────────────────
# generate_synthetic_problems
# ──────────────────────────────────────────────────────────────────────────────


class TestGenerateSyntheticProblems:
    """Feature: generate_synthetic_problems builds a list of implication problems."""

    @pytest.mark.unit
    def test_returns_requested_count(self):
        """
        Scenario: Request 50 problems
        Given num_problems=50
        When generate_synthetic_problems is called
        Then exactly 50 problems are returned
        """
        assert len(generate_synthetic_problems(num_problems=50, num_equations=20)) == 50

    @pytest.mark.unit
    def test_ids_are_sequential_from_one(self):
        """
        Scenario: Problem IDs start at 1 and are sequential
        Given num_problems=20
        When generate_synthetic_problems is called
        Then IDs are [1, 2, ..., 20]
        """
        ids = [p.id for p in generate_synthetic_problems(num_problems=20)]
        assert ids == list(range(1, 21))

    @pytest.mark.unit
    def test_early_problems_match_known_implications(self):
        """
        Scenario: First N problems use the known implication data
        Given implication knowledge with N entries
        When generate_synthetic_problems(N+5) is called
        Then problems 0..N-1 match the known implication pairs exactly
        """
        known = generate_implication_knowledge()
        problems = generate_synthetic_problems(num_problems=len(known) + 5)
        for i, (eq1, eq2, answer) in enumerate(known):
            assert problems[i].equation_1_id == eq1
            assert problems[i].equation_2_id == eq2
            assert problems[i].answer == answer

    @pytest.mark.unit
    def test_difficulty_split_at_1000(self):
        """
        Scenario: Problems with id <= 1000 are 'regular'; id > 1000 are 'hard'
        Given num_problems=1200
        When generate_synthetic_problems is called
        Then 1000 are 'regular' and 200 are 'hard'
        """
        problems = generate_synthetic_problems(num_problems=1200)
        assert sum(1 for p in problems if p.difficulty == "regular") == 1000
        assert sum(1 for p in problems if p.difficulty == "hard") == 200

    @pytest.mark.unit
    def test_random_problems_have_distinct_equation_ids(self):
        """
        Scenario: Randomly generated problems use different equations for H and T
        Given problems beyond the known implication entries
        When I inspect each random problem
        Then equation_1_id != equation_2_id
        """
        known = generate_implication_knowledge()
        problems = generate_synthetic_problems(num_problems=len(known) + 50, num_equations=50)
        for p in problems[len(known) :]:
            assert p.equation_1_id != p.equation_2_id


# ──────────────────────────────────────────────────────────────────────────────
# save_synthetic_data
# ──────────────────────────────────────────────────────────────────────────────


class TestSaveSyntheticData:
    """Feature: save_synthetic_data writes all expected output files."""

    @pytest.mark.unit
    def test_creates_all_four_output_files(self, tmp_path: Path):
        """
        Scenario: All four output files are created
        Given an output directory
        When save_synthetic_data(output_dir) is called
        Then equations.json, equations.txt, train_problems.json, implications.json exist
        """
        save_synthetic_data(output_dir=tmp_path)
        assert (tmp_path / "equations.json").exists()
        assert (tmp_path / "equations.txt").exists()
        assert (tmp_path / "train_problems.json").exists()
        assert (tmp_path / "implications.json").exists()

    @pytest.mark.unit
    def test_equations_json_has_correct_structure(self, tmp_path: Path):
        """
        Scenario: equations.json has source, count, and equations fields
        Given save_synthetic_data ran
        When equations.json is parsed
        Then source='synthetic', count==100, len(equations)==100
        """
        save_synthetic_data(output_dir=tmp_path)
        data = json.loads((tmp_path / "equations.json").read_text())
        assert data["source"] == "synthetic"
        assert data["count"] == 100
        assert len(data["equations"]) == 100

    @pytest.mark.unit
    def test_problems_json_has_1200_problems(self, tmp_path: Path):
        """
        Scenario: train_problems.json contains 1200 problems
        Given save_synthetic_data ran
        When train_problems.json is parsed
        Then count==1200 and len(problems)==1200
        """
        save_synthetic_data(output_dir=tmp_path)
        data = json.loads((tmp_path / "train_problems.json").read_text())
        assert data["count"] == 1200
        assert len(data["problems"]) == 1200

    @pytest.mark.unit
    def test_implications_json_has_required_keys(self, tmp_path: Path):
        """
        Scenario: implications.json entries have eq1, eq2, implies keys
        Given save_synthetic_data ran
        When implications.json is parsed
        Then every entry has eq1, eq2, and implies
        """
        save_synthetic_data(output_dir=tmp_path)
        data = json.loads((tmp_path / "implications.json").read_text())
        assert len(data) > 0
        assert all({"eq1", "eq2", "implies"} <= item.keys() for item in data)

    @pytest.mark.unit
    def test_returns_equations_and_problems_tuple(self, tmp_path: Path):
        """
        Scenario: Return value is a (equations, problems) tuple of correct sizes
        Given output_dir=tmp_path
        When save_synthetic_data is called
        Then it returns (100 equations, 1200 problems)
        """
        equations, problems = save_synthetic_data(output_dir=tmp_path)
        assert len(equations) == 100
        assert len(problems) == 1200
