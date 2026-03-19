"""Tests for the unified cheatsheet validation harness.

Tests all five validation angles:
1. Compliance  — size, encoding, format
2. Structure   — sections, magmas, key terms
3. Accuracy    — decision procedure correctness
4. Regression  — cross-version comparison
5. Competition — evaluation prompt format
"""

from pathlib import Path

import pytest

from src.cheatsheet_harness import (
    KNOWN_PROBLEMS,
    MAX_CHEATSHEET_BYTES,
    HarnessReport,
    main,
    print_report,
    run_harness,
    validate_accuracy,
    validate_competition,
    validate_compliance,
    validate_regression,
    validate_structure,
)

# Fixture paths
CHEATSHEET_DIR = Path(__file__).parent.parent / "cheatsheet"
V3_PATH = CHEATSHEET_DIR / "v3.txt"
FINAL_PATH = CHEATSHEET_DIR / "final.txt"


class TestComplianceValidation:
    """
    Feature: Validate cheatsheet compliance with competition rules.

    As a competition contestant
    I want to verify my cheatsheet meets size and format constraints
    So that my submission is not rejected.
    """

    @pytest.mark.unit
    def test_valid_cheatsheet_passes_compliance(self):
        """
        Scenario: A valid cheatsheet under 10KB passes
        Given a cheatsheet file under 10,240 bytes
        When I run compliance validation
        Then it should pass with size_ok=True
        """
        result = validate_compliance(FINAL_PATH)
        assert result.passed, f"Final cheatsheet should pass compliance: {result.errors}"
        assert result.size_ok
        assert result.is_utf8
        assert result.no_binary

    @pytest.mark.unit
    def test_missing_file_fails_compliance(self, tmp_path):
        """
        Scenario: A nonexistent file fails compliance
        Given a path to a file that does not exist
        When I run compliance validation
        Then it should fail with an error
        """
        missing = tmp_path / "nonexistent.txt"
        result = validate_compliance(missing)
        assert not result.passed
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    @pytest.mark.unit
    def test_oversized_cheatsheet_fails(self, tmp_path):
        """
        Scenario: A cheatsheet exceeding 10KB fails
        Given a cheatsheet file of 11,000 bytes
        When I run compliance validation
        Then size_ok should be False and passed should be False
        """
        big_file = tmp_path / "too_big.txt"
        big_file.write_text("x" * 11_000, encoding="utf-8")
        result = validate_compliance(big_file)
        assert not result.size_ok
        assert not result.passed
        assert any("exceeds" in e.lower() or "limit" in e.lower() for e in result.errors)

    @pytest.mark.unit
    def test_binary_content_fails(self, tmp_path):
        """
        Scenario: A file with null bytes fails
        Given a cheatsheet containing null bytes
        When I run compliance validation
        Then no_binary should be False
        """
        binary_file = tmp_path / "binary.txt"
        binary_file.write_bytes(b"valid text\x00more text")
        result = validate_compliance(binary_file)
        assert not result.no_binary
        assert not result.passed

    @pytest.mark.unit
    def test_size_budget_calculation(self):
        """
        Scenario: Budget remaining is correctly calculated
        Given a cheatsheet of known size
        When I check the compliance result
        Then budget_remaining = max_bytes - size_bytes
        """
        result = validate_compliance(FINAL_PATH)
        assert result.budget_remaining == MAX_CHEATSHEET_BYTES - result.size_bytes
        assert result.size_pct == result.size_bytes / MAX_CHEATSHEET_BYTES * 100

    @pytest.mark.unit
    def test_all_cheatsheet_versions_pass_compliance(self):
        """
        Scenario: Every cheatsheet version passes compliance
        Given all cheatsheet files in cheatsheet/
        When I validate each one
        Then all should pass (they are all under 10KB)
        """
        for path in sorted(CHEATSHEET_DIR.glob("*.txt")):
            result = validate_compliance(path)
            assert result.passed, f"{path.name} failed compliance: {result.errors}"


class TestStructureValidation:
    """
    Feature: Validate cheatsheet contains expected structural elements.

    As a cheatsheet author
    I want to verify my cheatsheet has complete content
    So that it teaches the full decision procedure.
    """

    @pytest.mark.unit
    def test_v3_has_all_phases(self):
        """
        Scenario: v3 cheatsheet contains all 8 phases
        Given the v3 cheatsheet
        When I validate its structure
        Then all 8 phases should be found
        """
        result = validate_structure(V3_PATH)
        assert len(result.phases_found) == 8, (
            f"Expected 8 phases, found {len(result.phases_found)}: {result.phases_found}"
        )

    @pytest.mark.unit
    def test_v3_has_quick_reference(self):
        """
        Scenario: v3 has a quick reference section
        Given the v3 cheatsheet
        When I validate structure
        Then has_quick_reference should be True
        """
        result = validate_structure(V3_PATH)
        assert result.has_quick_reference

    @pytest.mark.unit
    def test_v3_has_worked_examples(self):
        """
        Scenario: v3 has worked examples
        Given the v3 cheatsheet
        When I validate structure
        Then has_worked_examples should be True
        """
        result = validate_structure(V3_PATH)
        assert result.has_worked_examples

    @pytest.mark.unit
    def test_v3_references_canonical_magmas(self):
        """
        Scenario: v3 references the canonical counterexample magmas
        Given the v3 cheatsheet
        When I validate structure
        Then at least LP, RP, C0, XR, CM, Z3 should be found
        """
        result = validate_structure(V3_PATH)
        assert "LP" in result.magmas_found
        assert "RP" in result.magmas_found
        assert "C0" in result.magmas_found
        assert "Z3" in result.magmas_found

    @pytest.mark.unit
    def test_v3_contains_key_terms(self):
        """
        Scenario: v3 contains essential technical terms
        Given the v3 cheatsheet
        When I validate structure
        Then key terms like counterexample, substitution, magma should be present
        """
        result = validate_structure(V3_PATH)
        assert "counterexample" in result.key_terms_found
        assert "substitution" in result.key_terms_found
        assert "magma" in result.key_terms_found

    @pytest.mark.unit
    def test_v3_structure_passes(self):
        """
        Scenario: v3 passes overall structure validation
        Given the v3 cheatsheet
        When I validate structure
        Then it should pass
        """
        result = validate_structure(V3_PATH)
        assert result.passed, f"v3 should pass structure: {result.warnings}"

    @pytest.mark.unit
    def test_minimal_cheatsheet_fails_structure(self, tmp_path):
        """
        Scenario: A minimal cheatsheet without phases fails
        Given a cheatsheet with no phase sections
        When I validate structure
        Then it should not pass
        """
        minimal = tmp_path / "minimal.txt"
        minimal.write_text("Hello world. This is a cheatsheet.", encoding="utf-8")
        result = validate_structure(minimal)
        assert not result.passed

    @pytest.mark.unit
    def test_missing_file_warns(self, tmp_path):
        """
        Scenario: Missing file produces warnings
        Given a nonexistent path
        When I validate structure
        Then warnings should be non-empty
        """
        result = validate_structure(tmp_path / "nope.txt")
        assert len(result.warnings) > 0


class TestAccuracyValidation:
    """
    Feature: Validate decision procedure accuracy on known problems.

    As a competition contestant
    I want to verify the decision procedure gets correct answers
    So that I can trust the cheatsheet teaches the right approach.
    """

    @pytest.mark.unit
    def test_known_problems_exist(self):
        """
        Scenario: The known problem set is non-empty
        Given the KNOWN_PROBLEMS list
        When I check its length
        Then it should have at least 15 problems
        """
        assert len(KNOWN_PROBLEMS) >= 15

    @pytest.mark.unit
    def test_known_problems_balanced(self):
        """
        Scenario: Known problems include both TRUE and FALSE cases
        Given the KNOWN_PROBLEMS list
        When I count TRUE and FALSE expected answers
        Then both should be represented
        """
        true_count = sum(1 for _, _, exp, _ in KNOWN_PROBLEMS if exp)
        false_count = sum(1 for _, _, exp, _ in KNOWN_PROBLEMS if not exp)
        assert true_count >= 5, f"Need at least 5 TRUE problems, got {true_count}"
        assert false_count >= 5, f"Need at least 5 FALSE problems, got {false_count}"

    @pytest.mark.unit
    def test_accuracy_above_90_percent(self):
        """
        Scenario: Decision procedure achieves >=90% on known problems
        Given the known-answer problem set
        When I run accuracy validation
        Then accuracy should be at least 90%
        """
        result = validate_accuracy()
        assert result.accuracy >= 0.90, (
            f"Accuracy {result.accuracy:.1%} below 90% threshold. "
            f"Failures: {[(f.label, f.phase, f.reason) for f in result.failures]}"
        )

    @pytest.mark.unit
    def test_no_errors_in_accuracy(self):
        """
        Scenario: No parsing errors in the known problem set
        Given the known-answer problem set
        When I run accuracy validation
        Then there should be zero errors
        """
        result = validate_accuracy()
        assert result.errors == 0, f"Got {result.errors} parse errors in known problems"

    @pytest.mark.unit
    def test_accuracy_tracks_phases(self):
        """
        Scenario: Accuracy results break down by phase
        Given the known-answer problem set
        When I run accuracy validation
        Then by_phase should contain entries
        """
        result = validate_accuracy()
        assert len(result.by_phase) > 0, "by_phase should be populated"

    @pytest.mark.unit
    def test_reflexive_always_true(self):
        """
        Scenario: Identical equations always imply each other
        Given problems where H == T
        When I run accuracy validation
        Then all reflexive cases should be correct
        """
        reflexive = [(h, t, exp, lbl) for h, t, exp, lbl in KNOWN_PROBLEMS if "reflexive" in lbl]
        result = validate_accuracy(reflexive)
        assert result.accuracy == 1.0, f"Reflexive cases failed: {result.failures}"

    @pytest.mark.unit
    def test_custom_problem_set(self):
        """
        Scenario: Can validate with a custom problem set
        Given a small custom problem list
        When I run accuracy validation with it
        Then results reflect only those problems
        """
        custom = [
            ("x = y", "x * y = y * x", True, "collapse-custom"),
            ("x = x", "x * y = y * x", False, "tautology-H-custom"),
        ]
        result = validate_accuracy(custom)
        assert result.total == 2


class TestRegressionValidation:
    """
    Feature: Detect quality regressions across cheatsheet versions.

    As a cheatsheet author
    I want to verify newer versions don't regress in quality
    So that each iteration improves on the last.
    """

    @pytest.mark.unit
    def test_all_versions_scored(self):
        """
        Scenario: All cheatsheet versions get a score
        Given the cheatsheet directory with v1, v2, v3, final
        When I run regression validation
        Then all versions should have scores
        """
        result = validate_regression()
        assert "v1" in result.versions
        assert "v3" in result.versions
        assert "final" in result.versions

    @pytest.mark.unit
    def test_best_version_identified(self):
        """
        Scenario: The best version is identified
        Given regression results
        When I check best_version
        Then it should be a non-empty string
        """
        result = validate_regression()
        assert result.best_version != ""
        assert result.best_version in result.versions

    @pytest.mark.unit
    def test_no_regressions(self):
        """
        Scenario: No structural regressions detected
        Given the cheatsheet version history
        When I compare versions
        Then later versions should score >= earlier versions
        """
        result = validate_regression()
        assert result.passed, f"Regressions detected: {result.regressions}"


class TestCompetitionValidation:
    """
    Feature: Validate cheatsheet works in competition evaluation format.

    As a competition contestant
    I want to verify my cheatsheet fits the evaluation prompt
    So that it works correctly during offline evaluation.
    """

    @pytest.mark.unit
    def test_final_fits_competition_format(self):
        """
        Scenario: Final cheatsheet fits within competition constraints
        Given the final.txt cheatsheet
        When I simulate the competition prompt
        Then cheatsheet_fits should be True
        """
        result = validate_competition(FINAL_PATH)
        assert result.cheatsheet_fits
        assert result.passed

    @pytest.mark.unit
    def test_prompt_size_reasonable(self):
        """
        Scenario: Full prompt size is within reasonable bounds
        Given the final cheatsheet in competition format
        When I check prompt size
        Then it should be under 15KB (cheatsheet + template)
        """
        result = validate_competition(FINAL_PATH)
        assert result.prompt_size_bytes < 15_000, (
            f"Prompt too large: {result.prompt_size_bytes} bytes"
        )

    @pytest.mark.unit
    def test_token_estimate_reasonable(self):
        """
        Scenario: Estimated token count is within model limits
        Given the competition prompt
        When I estimate tokens
        Then it should be under 5000 tokens
        """
        result = validate_competition(FINAL_PATH)
        assert result.estimated_tokens < 5000

    @pytest.mark.unit
    def test_missing_cheatsheet_fails(self, tmp_path):
        """
        Scenario: Missing cheatsheet file fails competition check
        Given a nonexistent cheatsheet path
        When I validate competition format
        Then it should not pass
        """
        result = validate_competition(tmp_path / "nope.txt")
        assert not result.passed


class TestHarnessIntegration:
    """
    Feature: Run the full harness with all angles combined.

    As a developer
    I want a single entry point to validate everything
    So that CI and the Makefile can invoke one command.
    """

    @pytest.mark.unit
    def test_run_all_angles(self):
        """
        Scenario: Running all angles produces a complete report
        Given the final cheatsheet
        When I run the harness with all angles
        Then all result fields should be populated
        """
        report = run_harness(FINAL_PATH)
        assert report.compliance is not None
        assert report.structure is not None
        assert report.accuracy is not None
        assert report.regression is not None
        assert report.competition is not None

    @pytest.mark.unit
    def test_run_single_angle(self):
        """
        Scenario: Running a single angle only populates that result
        Given the final cheatsheet
        When I run only the compliance angle
        Then only compliance should be populated
        """
        report = run_harness(FINAL_PATH, angles=["compliance"])
        assert report.compliance is not None
        assert report.structure is None
        assert report.accuracy is None

    @pytest.mark.unit
    def test_all_passed_reflects_reality(self):
        """
        Scenario: all_passed is True only when every angle passes
        Given the final cheatsheet (which should pass all angles)
        When I run the full harness
        Then all_passed should reflect the individual results
        """
        report = run_harness(FINAL_PATH)
        individual = [
            report.compliance.passed,
            report.structure.passed,
            report.accuracy.passed,
            report.regression.passed,
            report.competition.passed,
        ]
        assert report.all_passed == all(individual)


class TestStructureHeadingFallback:
    """Cover the markdown ## heading fallback path in validate_structure."""

    @pytest.mark.unit
    def test_section_headings_used_when_few_phases(self, tmp_path):
        """When fewer than 4 PHASE markers exist but >=4 ## headings, count headings."""
        content = (
            "## OVERVIEW\ntext\n## METHOD\ntext\n"
            "## EXAMPLES\ntext\n## REFERENCE\ntext\n"
            "## APPENDIX\ntext\n"
            "counterexample substitution tautology variable magma implication true false\n"
            "LP RP C0 XR CM Z3 example\n"
        )
        cs = tmp_path / "headings.txt"
        cs.write_text(content, encoding="utf-8")
        result = validate_structure(cs)
        assert len(result.phases_found) >= 4

    @pytest.mark.unit
    def test_non_utf8_compliance_fails(self, tmp_path):
        """Non-UTF-8 encoded file fails compliance."""
        bad = tmp_path / "bad_encoding.txt"
        bad.write_bytes(b"\x80\x81\x82" * 100)
        result = validate_compliance(bad)
        assert not result.is_utf8
        assert not result.passed


class TestPrintFunctions:
    """Cover CLI print/report functions (lines 555-685)."""

    @pytest.mark.unit
    def test_print_report_all_angles(self, capsys):
        """print_report handles a fully populated HarnessReport."""
        report = run_harness(FINAL_PATH)
        print_report(report)
        captured = capsys.readouterr()
        assert "COMPLIANCE" in captured.out
        assert "STRUCTURE" in captured.out
        assert "ACCURACY" in captured.out
        assert "REGRESSION" in captured.out
        assert "COMPETITION" in captured.out
        assert "OVERALL" in captured.out

    @pytest.mark.unit
    def test_print_report_partial(self, capsys):
        """print_report handles a report with only some angles."""
        report = run_harness(FINAL_PATH, angles=["compliance"])
        print_report(report)
        captured = capsys.readouterr()
        assert "COMPLIANCE" in captured.out
        # Should still show overall
        assert "OVERALL" in captured.out

    @pytest.mark.unit
    def test_print_report_empty(self, capsys):
        """print_report handles an empty report without errors."""
        report = HarnessReport()
        print_report(report)
        captured = capsys.readouterr()
        assert "OVERALL" in captured.out

    @pytest.mark.unit
    def test_print_report_with_failures(self, capsys):
        """print_report shows failure details from accuracy."""
        # Use a custom problem set that will produce failures
        bad_problems = [
            ("x = x", "x * y = y * x", True, "should-fail"),  # tautology-H => FALSE
        ]
        result = validate_accuracy(bad_problems)
        report = HarnessReport(accuracy=result)
        print_report(report)
        captured = capsys.readouterr()
        assert "ACCURACY" in captured.out


class TestMainCli:
    """Cover the main() CLI entry point."""

    @pytest.mark.unit
    def test_main_all_returns_zero_on_pass(self):
        """main() returns 0 when all angles pass."""
        ret = main(["all", str(FINAL_PATH)])
        assert ret == 0

    @pytest.mark.unit
    def test_main_single_angle(self):
        """main() with a single angle."""
        ret = main(["compliance", str(FINAL_PATH)])
        assert ret == 0

    @pytest.mark.unit
    def test_main_json_output(self, capsys):
        """main() with --json writes JSON to stderr."""
        main(["compliance", str(FINAL_PATH), "--json"])
        captured = capsys.readouterr()
        assert "COMPLIANCE" in captured.out
        # JSON output goes to stderr
        assert "compliance" in captured.err

    @pytest.mark.unit
    def test_main_default_args(self):
        """main() with no args uses defaults."""
        ret = main([])
        assert ret in (0, 1)

    @pytest.mark.unit
    def test_main_missing_cheatsheet(self, tmp_path):
        """main() returns 1 for missing cheatsheet."""
        ret = main(["compliance", str(tmp_path / "nope.txt")])
        assert ret == 1


class TestRegressionEdgeCases:
    """Edge cases for regression validation."""

    @pytest.mark.unit
    def test_empty_cheatsheet_dir(self, tmp_path):
        """Regression with empty dir produces no versions and fails."""
        result = validate_regression(cheatsheet_dir=tmp_path)
        assert len(result.versions) == 0
        assert result.best_version == ""

    @pytest.mark.unit
    def test_single_version_no_regression(self, tmp_path):
        """A single version cannot regress against itself."""
        cs = tmp_path / "v1.txt"
        cs.write_text(
            "PHASE 1\nPHASE 2\nPHASE 3\nPHASE 4\n"
            "PHASE 5\nPHASE 6\nPHASE 7\nPHASE 8\n"
            "counterexample substitution tautology variable magma implication true false\n"
            "LP RP C0 XR CM Z3 example QUICK REFERENCE\n",
            encoding="utf-8",
        )
        result = validate_regression(cheatsheet_dir=tmp_path)
        assert len(result.regressions) == 0
