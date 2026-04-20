"""Tests for scripts/analyze_errors.py — decision procedure error analysis.

Feature: Analyze where the decision procedure fails across the implication matrix
    As a competition developer
    I want to identify which phases produce the most errors
    So that I can improve the decision procedure's accuracy
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

# scripts/ is not on pythonpath by default
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from analyze_errors import (  # noqa: E402
    ErrorAnalyzer,
    ErrorRecord,
    ErrorReport,
    _suggestion_for_phase,
)
from decision_procedure import DecisionProcedure  # noqa: E402
from etp_equations import ETPEquations  # noqa: E402
from implication_oracle import ImplicationOracle  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def equations_file(tmp_path: Path) -> Path:
    """5-equation mini corpus: tautology, collapse, comm, projection, 3-var."""
    eq_path = tmp_path / "equations.txt"
    eq_path.write_text(
        "x = x\nx = y\nx ◇ y = y ◇ x\nx ◇ y = x\nx ◇ y = z\n",
        encoding="utf-8",
    )
    return eq_path


@pytest.fixture
def oracle_csv(tmp_path: Path) -> Path:
    """5x5 implication matrix (3=True, -3=False)."""
    csv_path = tmp_path / "implications.csv"
    matrix = [
        [3, -3, -3, -3, -3],   # Eq1 (tautology): implies only itself
        [3,  3,  3,  3,  3],   # Eq2 (collapse): implies everything
        [3, -3,  3, -3, -3],   # Eq3 (comm): implies 1, 3
        [3, -3, -3,  3, -3],   # Eq4 (proj): implies 1, 4
        [3,  3, -3, -3,  3],   # Eq5 (3-var): implies 1, 2, 5
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(matrix)
    return csv_path


@pytest.fixture
def eqs(equations_file: Path) -> ETPEquations:
    return ETPEquations(equations_file)


@pytest.fixture
def oracle(oracle_csv: Path) -> ImplicationOracle:
    return ImplicationOracle(oracle_csv)


@pytest.fixture
def proc(eqs: ETPEquations, oracle: ImplicationOracle) -> DecisionProcedure:
    return DecisionProcedure(eqs, oracle)


@pytest.fixture
def analyzer(proc: DecisionProcedure, oracle: ImplicationOracle, eqs: ETPEquations) -> ErrorAnalyzer:
    return ErrorAnalyzer(proc, oracle, eqs)


# ──────────────────────────────────────────────────────────────────────────────
# ErrorRecord
# ──────────────────────────────────────────────────────────────────────────────


class TestErrorRecord:
    """Feature: ErrorRecord captures all fields needed to diagnose a misclassification."""

    @pytest.mark.unit
    def test_fields_accessible(self):
        """
        Scenario: Create an ErrorRecord and read its fields
        Given an ErrorRecord with known values
        When I read its fields
        Then they match what was set
        """
        rec = ErrorRecord(
            h_id=3, t_id=4, predicted=True, actual=False,
            phase="P2-collapse", error_type="FP",
            h_depth=1, t_depth=1, h_vars=2, t_vars=2,
            new_vars_in_target=False,
        )
        assert rec.error_type == "FP"
        assert rec.h_id == 3
        assert rec.t_id == 4

    @pytest.mark.unit
    def test_to_dict_serialises_all_fields(self):
        """
        Scenario: Serialise an ErrorRecord to a dict
        Given a false-negative ErrorRecord
        When to_dict() is called
        Then all field values appear in the output
        """
        rec = ErrorRecord(
            h_id=1, t_id=2, predicted=False, actual=True,
            phase="P6-default", error_type="FN",
            h_depth=0, t_depth=0, h_vars=1, t_vars=2,
            new_vars_in_target=True,
        )
        d = rec.to_dict()
        assert d["error_type"] == "FN"
        assert d["phase"] == "P6-default"
        assert d["h_id"] == 1
        assert d["new_vars_in_target"] is True

    @pytest.mark.unit
    def test_record_is_frozen(self):
        """
        Scenario: ErrorRecord is immutable after creation
        Given an ErrorRecord
        When I try to mutate a field
        Then AttributeError is raised
        """
        rec = ErrorRecord(
            h_id=1, t_id=2, predicted=True, actual=False,
            phase="P6-default", error_type="FP",
            h_depth=0, t_depth=0, h_vars=1, t_vars=1,
            new_vars_in_target=False,
        )
        with pytest.raises((AttributeError, TypeError)):
            rec.h_id = 99  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# Error collection
# ──────────────────────────────────────────────────────────────────────────────


class TestErrorCollection:
    """Feature: collect_errors returns only genuine misclassifications."""

    @pytest.mark.unit
    def test_collect_errors_returns_list(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Basic call returns a list
        Given a configured analyzer
        When collect_errors() is called
        Then a list is returned
        """
        assert isinstance(analyzer.collect_errors(), list)

    @pytest.mark.unit
    def test_all_errors_are_genuine_misclassifications(
        self, analyzer: ErrorAnalyzer, oracle: ImplicationOracle, proc: DecisionProcedure
    ):
        """
        Scenario: Every record represents a real mismatch
        Given collected errors
        When we re-query oracle and proc for each error pair
        Then predicted != actual for every record
        """
        for err in analyzer.collect_errors():
            actual = oracle.query(err.h_id, err.t_id)
            predicted = proc.predict_bool(err.h_id, err.t_id)
            assert predicted != actual

    @pytest.mark.unit
    def test_fp_and_fn_classified_correctly(self, analyzer: ErrorAnalyzer):
        """
        Scenario: FP = predicted True but actual False; FN = opposite
        Given collected errors
        When I inspect error_type
        Then FP has predicted=True, actual=False and FN has the reverse
        """
        for err in analyzer.collect_errors():
            if err.error_type == "FP":
                assert err.predicted is True and err.actual is False
            else:
                assert err.predicted is False and err.actual is True

    @pytest.mark.unit
    def test_no_self_implication_errors(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Self-implication (H=T) is never misclassified
        Given collected errors
        When I check h_id == t_id
        Then no such pairs exist
        """
        for err in analyzer.collect_errors():
            assert err.h_id != err.t_id

    @pytest.mark.unit
    def test_structural_features_non_negative(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Depth and var counts are populated from the equations file
        Given collected errors
        When I inspect h_depth, t_depth, h_vars, t_vars
        Then all values are non-negative
        """
        for err in analyzer.collect_errors():
            assert err.h_depth >= 0
            assert err.t_depth >= 0
            assert err.h_vars >= 1
            assert err.t_vars >= 1


# ──────────────────────────────────────────────────────────────────────────────
# Grouping
# ──────────────────────────────────────────────────────────────────────────────


class TestGrouping:
    """Feature: group_errors aggregates errors by a named field."""

    @pytest.mark.unit
    def test_group_by_error_type_keys(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Group by error_type produces only FP/FN keys
        Given collected errors
        When grouped by 'error_type'
        Then all keys are 'FP' or 'FN'
        """
        grouped = analyzer.group_errors(analyzer.collect_errors(), "error_type")
        assert all(k in ("FP", "FN") for k in grouped)

    @pytest.mark.unit
    def test_group_counts_sum_to_total(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Group totals equal overall error count
        Given grouped errors
        When I sum all group sizes
        Then the total equals len(collect_errors())
        """
        errors = analyzer.collect_errors()
        grouped = analyzer.group_errors(errors, "error_type")
        assert sum(len(v) for v in grouped.values()) == len(errors)

    @pytest.mark.unit
    def test_groups_sorted_by_count_descending(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Groups are returned largest-first
        Given errors grouped by phase
        When I read the group sizes in order
        Then they are non-increasing
        """
        errors = analyzer.collect_errors()
        grouped = analyzer.group_errors(errors, "phase")
        counts = [len(v) for v in grouped.values()]
        assert counts == sorted(counts, reverse=True)


# ──────────────────────────────────────────────────────────────────────────────
# Top patterns
# ──────────────────────────────────────────────────────────────────────────────


class TestTopPatterns:
    """Feature: top_patterns identifies the highest-frequency error buckets."""

    @pytest.mark.unit
    def test_returns_at_most_n_patterns(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Limit output to n patterns
        Given errors with several distinct buckets
        When top_patterns(errors, n=3) is called
        Then at most 3 patterns are returned
        """
        errors = analyzer.collect_errors()
        assert len(analyzer.top_patterns(errors, n=3)) <= 3

    @pytest.mark.unit
    def test_pattern_has_required_fields(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Each pattern dict has the expected shape
        Given at least one error
        When top_patterns is called
        Then every pattern has count, pct_of_total, example, bucket keys
        """
        errors = analyzer.collect_errors()
        if not errors:
            pytest.skip("No errors in this fixture")
        for p in analyzer.top_patterns(errors, n=10):
            assert {"count", "pct_of_total", "example", "bucket"} <= p.keys()

    @pytest.mark.unit
    def test_patterns_sorted_descending_by_count(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Patterns are returned largest-first
        Given collected errors
        When top_patterns is called
        Then counts are non-increasing
        """
        errors = analyzer.collect_errors()
        counts = [p["count"] for p in analyzer.top_patterns(errors, n=10)]
        assert counts == sorted(counts, reverse=True)


# ──────────────────────────────────────────────────────────────────────────────
# Report generation
# ──────────────────────────────────────────────────────────────────────────────


class TestReportGeneration:
    """Feature: generate_report produces a structured ErrorReport."""

    @pytest.mark.unit
    def test_returns_error_report_instance(self, analyzer: ErrorAnalyzer):
        """
        Scenario: generate_report returns an ErrorReport
        Given a configured analyzer
        When generate_report() is called
        Then an ErrorReport is returned
        """
        assert isinstance(analyzer.generate_report(), ErrorReport)

    @pytest.mark.unit
    def test_fp_plus_fn_equals_total_errors(self, analyzer: ErrorAnalyzer):
        """
        Scenario: FP + FN counts must equal total_errors
        Given a generated report
        When I inspect fp_count and fn_count
        Then fp_count + fn_count == total_errors
        """
        r = analyzer.generate_report()
        assert r.fp_count + r.fn_count == r.total_errors

    @pytest.mark.unit
    def test_to_dict_has_required_sections(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Report dict has all required sections
        Given a generated report
        When to_dict() is called
        Then 'summary', 'by_phase', 'top_patterns', 'phase_suggestions' are present
        """
        d = analyzer.generate_report().to_dict()
        assert {"summary", "by_phase", "top_patterns", "phase_suggestions"} <= d.keys()

    @pytest.mark.unit
    def test_to_json_is_valid_json(self, analyzer: ErrorAnalyzer):
        """
        Scenario: to_json() produces parseable JSON
        Given a generated report
        When to_json() is called
        Then the result parses without error
        """
        parsed = json.loads(analyzer.generate_report().to_json())
        assert "summary" in parsed

    @pytest.mark.unit
    def test_sample_limits_total_pairs(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Sampling caps the total_pairs in the report
        Given a sample of 10
        When generate_report(sample=10) is called
        Then total_pairs is at most 10
        """
        assert analyzer.generate_report(sample=10).total_pairs <= 10


# ──────────────────────────────────────────────────────────────────────────────
# Print report
# ──────────────────────────────────────────────────────────────────────────────


class TestPrintReport:
    """Feature: print_report produces human-readable stdout output."""

    @pytest.mark.unit
    def test_output_contains_header(self, analyzer: ErrorAnalyzer, capsys):
        """
        Scenario: Print report contains the analysis header
        Given a generated report
        When print_report is called
        Then stdout contains 'ERROR ANALYSIS'
        """
        analyzer.print_report(analyzer.generate_report())
        assert "ERROR ANALYSIS" in capsys.readouterr().out

    @pytest.mark.unit
    def test_output_contains_phase_section(self, analyzer: ErrorAnalyzer, capsys):
        """
        Scenario: Print report includes the phase breakdown section
        Given a generated report
        When print_report is called
        Then stdout contains 'DECISION PHASE'
        """
        analyzer.print_report(analyzer.generate_report())
        assert "DECISION PHASE" in capsys.readouterr().out

    @pytest.mark.unit
    def test_output_contains_suggestions(self, analyzer: ErrorAnalyzer, capsys):
        """
        Scenario: Print report includes the improvement suggestions section
        Given a generated report
        When print_report is called
        Then stdout contains 'IMPROVEMENT SUGGESTIONS'
        """
        analyzer.print_report(analyzer.generate_report())
        assert "IMPROVEMENT SUGGESTIONS" in capsys.readouterr().out


# ──────────────────────────────────────────────────────────────────────────────
# Phase suggestion lookup
# ──────────────────────────────────────────────────────────────────────────────


class TestPhaseSuggestions:
    """Feature: _suggestion_for_phase covers all phase names the procedure emits."""

    @pytest.mark.unit
    def test_known_phase_returns_hint(self):
        """
        Scenario: A standard phase key returns a non-None hint
        Given phase name 'P2-collapse'
        When _suggestion_for_phase is called
        Then a non-empty string is returned
        """
        assert _suggestion_for_phase("P2-collapse") is not None

    @pytest.mark.unit
    def test_dynamic_suffix_resolves_to_bare_key(self):
        """
        Scenario: Parenthesised suffix on phase name is stripped before lookup
        Given phase name 'P5b-structural(Phase 4b)'
        When _suggestion_for_phase is called
        Then the hint for 'P5b-structural' is returned
        """
        msg = _suggestion_for_phase("P5b-structural(Phase 4b)")
        assert msg is not None
        assert "structural" in msg.lower() or "counterexample" in msg.lower()

    @pytest.mark.unit
    def test_unknown_phase_returns_none(self):
        """
        Scenario: An unknown phase name returns None
        Given phase name 'PX-nonexistent'
        When _suggestion_for_phase is called
        Then None is returned
        """
        assert _suggestion_for_phase("PX-nonexistent") is None


# ──────────────────────────────────────────────────────────────────────────────
# Known-error integration
# ──────────────────────────────────────────────────────────────────────────────


class TestKnownErrors:
    """Feature: analyzer detects specific known false negatives."""

    @pytest.fixture
    def fn_oracle_csv(self, tmp_path: Path) -> Path:
        """Matrix where Eq5 implies Eq3 (actual=True) but proc will say False.

        This creates a predictable FN at (5, 3).
        """
        csv_path = tmp_path / "fn_implications.csv"
        matrix = [
            [3, -3, -3, -3, -3],
            [3,  3,  3,  3,  3],
            [3, -3,  3, -3, -3],
            [3, -3, -3,  3, -3],
            [3,  3,  3, -3,  3],  # Eq5 now implies Eq3 — proc will miss it (new var z)
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(matrix)
        return csv_path

    @pytest.mark.unit
    def test_known_fn_at_5_3_detected(self, eqs: ETPEquations, fn_oracle_csv: Path):
        """
        Scenario: A designed false negative is found in the error list
        Given a matrix where Eq5 => Eq3 but the procedure says False
        When collect_errors() is called
        Then (5, 3) appears in the FN list
        """
        oracle = ImplicationOracle(fn_oracle_csv)
        proc = DecisionProcedure(eqs, oracle)
        analyzer = ErrorAnalyzer(proc, oracle, eqs)
        fn_pairs = [(e.h_id, e.t_id) for e in analyzer.collect_errors() if e.error_type == "FN"]
        assert (5, 3) in fn_pairs
