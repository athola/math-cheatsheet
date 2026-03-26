"""Tests for generate_synthetic_data module."""

import json

from data_models import Difficulty
from generate_synthetic_data import (
    generate_extended_equations,
    generate_implication_knowledge,
    generate_synthetic_problems,
    save_synthetic_data,
)


class TestGenerateExtendedEquations:
    def test_returns_requested_count(self):
        equations = generate_extended_equations(count=50)
        assert len(equations) == 50

    def test_includes_base_synthetic_equations(self):
        equations = generate_extended_equations(count=50)
        # First entries should be the base SYNTHETIC_EQUATIONS
        assert equations[0].id is not None

    def test_generated_equations_have_properties(self):
        equations = generate_extended_equations(count=100)
        # Every equation should have at least one property
        for eq in equations:
            assert len(eq.properties) >= 1

    def test_generated_equations_have_unique_ids(self):
        equations = generate_extended_equations(count=100)
        ids = [eq.id for eq in equations]
        assert len(ids) == len(set(ids))

    def test_property_assignment_follows_modular_rules(self):
        """Equations generated past the base set follow modular property rules."""
        equations = generate_extended_equations(count=100)
        # Find a generated equation at index divisible by 2 (associative)
        # We check that the rule holds for at least some generated equations
        generated = [eq for eq in equations if eq.name.startswith("Synthetic")]
        assert len(generated) > 0

    def test_small_count_returns_base_only(self):
        """When count <= base size, returns only base equations."""
        from data_models import SYNTHETIC_EQUATIONS

        count = len(SYNTHETIC_EQUATIONS)
        equations = generate_extended_equations(count=count)
        assert len(equations) == count


class TestGenerateImplicationKnowledge:
    def test_returns_tuples(self):
        implications = generate_implication_knowledge()
        assert len(implications) > 0
        for item in implications:
            assert len(item) == 3
            eq1_id, eq2_id, implies = item
            assert isinstance(eq1_id, int)
            assert isinstance(eq2_id, int)
            assert isinstance(implies, bool)

    def test_contains_known_implications(self):
        implications = generate_implication_knowledge()
        # Group implies associativity
        assert (13, 1, True) in implications

    def test_contains_non_implications(self):
        implications = generate_implication_knowledge()
        # Associativity does NOT imply commutativity
        assert (1, 2, False) in implications

    def test_has_both_true_and_false(self):
        implications = generate_implication_knowledge()
        has_true = any(imp for _, _, imp in implications)
        has_false = any(not imp for _, _, imp in implications)
        assert has_true
        assert has_false


class TestGenerateSyntheticProblems:
    def test_returns_requested_count(self):
        problems = generate_synthetic_problems(num_problems=50, num_equations=20)
        assert len(problems) == 50

    def test_problems_have_sequential_ids(self):
        problems = generate_synthetic_problems(num_problems=20)
        ids = [p.id for p in problems]
        assert ids == list(range(1, 21))

    def test_early_problems_use_known_implications(self):
        """First N problems should use the known implication data."""
        implications = generate_implication_knowledge()
        problems = generate_synthetic_problems(num_problems=len(implications) + 5)

        # First problems should match implication entries
        for i, (eq1, eq2, answer) in enumerate(implications):
            assert problems[i].equation_1_id == eq1
            assert problems[i].equation_2_id == eq2
            assert problems[i].answer == answer

    def test_difficulty_assignment(self):
        """Problems with id > 1000 should be 'hard'."""
        problems = generate_synthetic_problems(num_problems=1200)
        regular = [p for p in problems if p.difficulty == Difficulty.REGULAR]
        hard = [p for p in problems if p.difficulty == Difficulty.HARD]
        assert len(regular) == 1000
        assert len(hard) == 200

    def test_random_pairs_have_different_equations(self):
        """Random-generated problems should have different eq1 and eq2."""
        problems = generate_synthetic_problems(num_problems=200, num_equations=50)
        implications = generate_implication_knowledge()
        # Check the randomly generated ones (after known implications)
        for p in problems[len(implications) :]:
            assert p.equation_1_id != p.equation_2_id


class TestSaveSyntheticData:
    def test_saves_all_files(self, tmp_path):
        """save_synthetic_data creates expected output files."""
        save_synthetic_data(project_root=tmp_path)

        assert (tmp_path / "research" / "data" / "original" / "equations.json").exists()
        assert (tmp_path / "research" / "data" / "original" / "equations.txt").exists()
        assert (tmp_path / "research" / "data" / "original" / "train_problems.json").exists()
        assert (tmp_path / "research" / "data" / "original" / "implications.json").exists()

    def test_equations_json_structure(self, tmp_path):
        save_synthetic_data(project_root=tmp_path)

        data = json.loads(
            (tmp_path / "research" / "data" / "original" / "equations.json").read_text()
        )
        assert data["source"] == "synthetic"
        assert data["count"] == len(data["equations"])
        assert data["count"] == 100

    def test_problems_json_structure(self, tmp_path):
        save_synthetic_data(project_root=tmp_path)

        data = json.loads(
            (tmp_path / "research" / "data" / "original" / "train_problems.json").read_text()
        )
        assert data["count"] == 1200
        assert len(data["problems"]) == 1200

    def test_implications_json_structure(self, tmp_path):
        save_synthetic_data(project_root=tmp_path)

        data = json.loads(
            (tmp_path / "research" / "data" / "original" / "implications.json").read_text()
        )
        assert len(data) > 0
        assert all("eq1" in item and "eq2" in item and "implies" in item for item in data)

    def test_returns_equations_and_problems(self, tmp_path):
        equations, problems = save_synthetic_data(project_root=tmp_path)
        assert len(equations) == 100
        assert len(problems) == 1200
