"""Tests for ErrorAnalyzer.

Uses small synthetic fixtures (same pattern as test_decision_procedure.py)
to test error collection, bucketing, and report generation.
"""

import csv
import json
from pathlib import Path

import pytest

from decision_procedure import DecisionProcedure
from error_analyzer import ErrorAnalyzer, ErrorRecord, ErrorReport
from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle


@pytest.fixture
def equations_file(tmp_path: Path) -> Path:
    """Create a small equations file.

    Line N = Equation N:
      1: x = x         (tautology)
      2: x = y         (collapse: forces |M|=1)
      3: x * y = y * x (commutativity, 2 vars)
      4: x * y = x     (left projection, 2 vars)
      5: x * y = z     (has new var z, 3 vars)
    """
    eq_path = tmp_path / "equations.txt"
    eq_path.write_text(
        "x = x\nx = y\nx ◇ y = y ◇ x\nx ◇ y = x\nx ◇ y = z\n",
        encoding="utf-8",
    )
    return eq_path


@pytest.fixture
def oracle_csv(tmp_path: Path) -> Path:
    """Create a 5x5 implication matrix.

    Encodes:
      Eq1 (tautology): implies only itself
      Eq2 (collapse): implies everything
      Eq3 (commutative): implies 1, 3
      Eq4 (projection): implies 1, 4
      Eq5 (3-var): implies 1, 2, 5
    """
    csv_path = tmp_path / "implications.csv"
    matrix = [
        [3, -3, -3, -3, -3],  # Eq1
        [3, 3, 3, 3, 3],  # Eq2
        [3, -3, 3, -3, -3],  # Eq3
        [3, -3, -3, 3, -3],  # Eq4
        [3, 3, -3, -3, 3],  # Eq5
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in matrix:
            writer.writerow(row)
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
def analyzer(
    proc: DecisionProcedure, oracle: ImplicationOracle, eqs: ETPEquations
) -> ErrorAnalyzer:
    return ErrorAnalyzer(proc, oracle, eqs)


class TestErrorRecord:
    def test_error_record_fields(self):
        rec = ErrorRecord(
            h_id=3,
            t_id=4,
            predicted=True,
            actual=False,
            phase="P2-collapse",
            error_type="FP",
            h_depth=1,
            t_depth=1,
            h_vars=2,
            t_vars=2,
            new_vars_in_target=False,
            h_is_collapse=False,
            t_is_collapse=False,
        )
        assert rec.error_type == "FP"
        assert rec.h_id == 3
        assert rec.t_id == 4

    def test_error_record_to_dict(self):
        rec = ErrorRecord(
            h_id=1,
            t_id=2,
            predicted=False,
            actual=True,
            phase="P6-default",
            error_type="FN",
            h_depth=0,
            t_depth=0,
            h_vars=1,
            t_vars=2,
            new_vars_in_target=True,
            h_is_collapse=False,
            t_is_collapse=True,
        )
        d = rec.to_dict()
        assert d["error_type"] == "FN"
        assert d["phase"] == "P6-default"
        assert d["h_id"] == 1


class TestErrorCollection:
    def test_collect_errors_returns_list(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        assert isinstance(errors, list)

    def test_all_errors_are_actual_misclassifications(
        self,
        analyzer: ErrorAnalyzer,
        oracle: ImplicationOracle,
        proc: DecisionProcedure,
    ):
        """Every error in the list should be a genuine disagreement."""
        errors = analyzer.collect_errors()
        for err in errors:
            actual = oracle.query(err.h_id, err.t_id)
            predicted = proc.predict_bool(err.h_id, err.t_id)
            assert predicted != actual, (
                f"({err.h_id},{err.t_id}) reported as error but pred={predicted} == actual={actual}"
            )

    def test_error_type_classification(self, analyzer: ErrorAnalyzer):
        """FP means predicted True but actual False; FN vice versa."""
        errors = analyzer.collect_errors()
        for err in errors:
            if err.error_type == "FP":
                assert err.predicted is True
                assert err.actual is False
            elif err.error_type == "FN":
                assert err.predicted is False
                assert err.actual is True

    def test_no_self_implication_errors(self, analyzer: ErrorAnalyzer):
        """Phase 0 (self-implication) should never be wrong."""
        errors = analyzer.collect_errors()
        for err in errors:
            assert err.h_id != err.t_id, "Self-implication should never be misclassified"

    def test_structural_features_populated(self, analyzer: ErrorAnalyzer):
        """Depth and var counts should be populated from equations."""
        errors = analyzer.collect_errors()
        for err in errors:
            assert err.h_depth >= 0
            assert err.t_depth >= 0
            assert err.h_vars >= 1
            assert err.t_vars >= 1


class TestGrouping:
    def test_group_by_error_type(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        grouped = analyzer.group_errors(errors, "error_type")
        # Should have at most FP and FN keys
        assert all(k in ("FP", "FN") for k in grouped)

    def test_group_by_phase(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        grouped = analyzer.group_errors(errors, "phase")
        # All keys should be valid phase names
        for k in grouped:
            assert k.startswith("P"), f"Unexpected phase key: {k}"

    def test_group_counts_sum_to_total(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        grouped = analyzer.group_errors(errors, "error_type")
        total_in_groups = sum(len(v) for v in grouped.values())
        assert total_in_groups == len(errors)

    def test_group_sorted_by_count_descending(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        grouped = analyzer.group_errors(errors, "phase")
        counts = [len(v) for v in grouped.values()]
        assert counts == sorted(counts, reverse=True)


class TestTopPatterns:
    def test_top_patterns_returns_list(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        patterns = analyzer.top_patterns(errors, n=10)
        assert isinstance(patterns, list)

    def test_top_patterns_max_n(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        patterns = analyzer.top_patterns(errors, n=3)
        assert len(patterns) <= 3

    def test_pattern_has_required_fields(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        if not errors:
            pytest.skip("No errors to analyze")
        patterns = analyzer.top_patterns(errors, n=10)
        for p in patterns:
            assert "count" in p
            assert "pct_of_total" in p
            assert "example" in p
            assert "bucket" in p

    def test_patterns_sorted_descending(self, analyzer: ErrorAnalyzer):
        errors = analyzer.collect_errors()
        patterns = analyzer.top_patterns(errors, n=10)
        counts = [p["count"] for p in patterns]
        assert counts == sorted(counts, reverse=True)


class TestReport:
    def test_generate_report_returns_report(self, analyzer: ErrorAnalyzer):
        report = analyzer.generate_report()
        assert isinstance(report, ErrorReport)

    def test_report_has_summary(self, analyzer: ErrorAnalyzer):
        report = analyzer.generate_report()
        assert report.total_pairs > 0
        assert report.total_errors >= 0
        assert report.fp_count >= 0
        assert report.fn_count >= 0
        assert report.fp_count + report.fn_count == report.total_errors

    def test_report_has_phase_breakdown(self, analyzer: ErrorAnalyzer):
        report = analyzer.generate_report()
        assert isinstance(report.by_phase, dict)

    def test_report_has_top_patterns(self, analyzer: ErrorAnalyzer):
        report = analyzer.generate_report()
        assert isinstance(report.top_patterns, list)

    def test_report_to_dict(self, analyzer: ErrorAnalyzer):
        report = analyzer.generate_report()
        d = report.to_dict()
        assert "summary" in d
        assert "by_phase" in d
        assert "top_patterns" in d
        assert "phase_suggestions" in d

    def test_report_to_json(self, analyzer: ErrorAnalyzer):
        report = analyzer.generate_report()
        j = report.to_json()
        parsed = json.loads(j)
        assert "summary" in parsed

    def test_report_phase_suggestions(self, analyzer: ErrorAnalyzer):
        """Report should suggest which phases to improve."""
        report = analyzer.generate_report()
        assert isinstance(report.phase_suggestions, list)


class TestSampling:
    """Feature: Error collection supports random sampling."""

    @pytest.mark.unit
    def test_collect_errors_with_sample(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Collect errors from a random sample
        Given a small oracle with 25 total pairs
        When collect_errors(sample=10) is called
        Then it should return errors from at most 10 pairs
        """
        errors = analyzer.collect_errors(sample=10)
        assert isinstance(errors, list)
        # Sample of 10 from 25 pairs - may have 0-10 errors
        assert len(errors) <= 10

    @pytest.mark.unit
    def test_generate_report_with_sample(self, analyzer: ErrorAnalyzer):
        """
        Scenario: Generate report from sampled pairs
        Given a sample size
        When generate_report(sample=15) is called
        Then total_pairs should be at most 15
        """
        report = analyzer.generate_report(sample=15)
        assert report.total_pairs <= 15
        assert isinstance(report, ErrorReport)


class TestPrintReport:
    """Feature: Error report formats as readable stdout output."""

    @pytest.mark.unit
    def test_print_report_runs_without_error(self, analyzer: ErrorAnalyzer, capsys):
        """
        Scenario: Print report to stdout
        Given a generated error report
        When print_report is called
        Then it should produce output without errors
        """
        report = analyzer.generate_report()
        analyzer.print_report(report)
        captured = capsys.readouterr()
        assert "ERROR ANALYSIS" in captured.out
        assert "Total pairs" in captured.out

    @pytest.mark.unit
    def test_print_report_shows_phase_breakdown(self, analyzer: ErrorAnalyzer, capsys):
        """
        Scenario: Report includes phase breakdown section
        Given a report with errors
        When printed
        Then the phase breakdown section should appear
        """
        report = analyzer.generate_report()
        analyzer.print_report(report)
        captured = capsys.readouterr()
        assert "DECISION PHASE" in captured.out

    @pytest.mark.unit
    def test_print_report_shows_suggestions(self, analyzer: ErrorAnalyzer, capsys):
        """
        Scenario: Report includes improvement suggestions
        Given a report with errors
        When printed
        Then suggestions section should appear
        """
        report = analyzer.generate_report()
        analyzer.print_report(report)
        captured = capsys.readouterr()
        assert "IMPROVEMENT SUGGESTIONS" in captured.out


class TestWithKnownErrors:
    """Test with a matrix designed to produce known error types."""

    @pytest.fixture
    def designed_oracle_csv(self, tmp_path: Path) -> Path:
        """Matrix where Eq5 implies Eq3 (actual=True) but decision proc says False.

        This creates a known false negative at (5,3).
        """
        csv_path = tmp_path / "implications2.csv"
        matrix = [
            [3, -3, -3, -3, -3],  # Eq1
            [3, 3, 3, 3, 3],  # Eq2
            [3, -3, 3, -3, -3],  # Eq3
            [3, -3, -3, 3, -3],  # Eq4
            [3, 3, 3, -3, 3],  # Eq5: now implies Eq3 too
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in matrix:
                writer.writerow(row)
        return csv_path

    def test_known_fn_detected(
        self,
        eqs: ETPEquations,
        designed_oracle_csv: Path,
    ):
        oracle = ImplicationOracle(designed_oracle_csv)
        proc = DecisionProcedure(eqs, oracle)
        analyzer = ErrorAnalyzer(proc, oracle, eqs)
        errors = analyzer.collect_errors()

        # Eq5 -> Eq3: actual=True, but P4-new-vars will say False (z not in {x,y})
        fn_pairs = [(e.h_id, e.t_id) for e in errors if e.error_type == "FN"]
        assert (5, 3) in fn_pairs
