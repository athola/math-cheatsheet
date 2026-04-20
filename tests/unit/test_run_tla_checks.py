"""Tests for TLA+ model checking automation (issues #16, #18).

Feature: Automated TLA+ model checking
    As a developer
    I want to run TLC on all TLA+ modules with a single command
    So that I can verify formal specifications without manual toolbox steps
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


class TestTLCOutputParsing:
    """Feature: Parse TLC model checker output into structured results."""

    @pytest.mark.unit
    def test_successful_model_check(self):
        """
        Scenario: TLC completes without errors
        Given TLC output containing 'Model checking completed. No error has been found.'
        When the output is parsed
        Then status should be 'pass'
        """
        from run_tla_checks import parse_tlc_output

        output = (
            "TLC2 Version 2.18\n"
            "Running breadth-first search...\n"
            "Finished computing initial states: 1 distinct state generated.\n"
            "Model checking completed. No error has been found.\n"
            "4 states generated, 2 distinct states found.\n"
        )
        result = parse_tlc_output("TestModule", output, returncode=0, elapsed=1.5)

        assert result.status == "pass"
        assert result.module == "TestModule"
        assert result.elapsed_seconds == 1.5
        assert result.states_found == 4
        assert result.distinct_states == 2

    @pytest.mark.unit
    def test_failed_model_check(self):
        """
        Scenario: TLC finds a property violation
        Given TLC output containing 'Error: Invariant TypeOK is violated.'
        When the output is parsed
        Then status should be 'fail' and message should contain the error
        """
        from run_tla_checks import parse_tlc_output

        output = (
            "TLC2 Version 2.18\n"
            "Error: Invariant TypeOK is violated.\n"
            "Error: The behavior up to this point is:\n"
        )
        result = parse_tlc_output("BadModule", output, returncode=12, elapsed=0.8)

        assert result.status == "fail"
        assert "Error" in result.message

    @pytest.mark.unit
    def test_warnings_extracted(self):
        """
        Scenario: TLC output contains warnings
        Given TLC output with 'Warning: ...' lines
        When the output is parsed
        Then warnings should be captured in the result
        """
        from run_tla_checks import parse_tlc_output

        output = "Warning: Unused variable x\nModel checking completed. No error has been found.\n"
        result = parse_tlc_output("WarnModule", output, returncode=0, elapsed=0.5)

        assert result.status == "pass"
        assert len(result.warnings) == 1
        assert "Unused variable" in result.warnings[0]


class TestTLCRunnerIntegration:
    """Feature: Run TLC on TLA+ modules with proper error handling."""

    @pytest.mark.unit
    def test_missing_tools_returns_skip(self):
        """
        Scenario: tla2tools.jar is not installed
        Given the TLA+ tools jar does not exist
        When run_tlc is called
        Then it should return status 'skip' with installation instructions
        """
        from run_tla_checks import run_tlc

        with patch("run_tla_checks.find_tla_tools", return_value=None):
            result = run_tlc("TestModule")

        assert result.status == "skip"
        assert "setup_tla_tools" in result.message

    @pytest.mark.unit
    def test_missing_tla_file_returns_error(self):
        """
        Scenario: The requested .tla file doesn't exist
        Given a module name that has no corresponding .tla file
        When run_tlc is called
        Then it should return status 'error'
        """
        from run_tla_checks import run_tlc

        with patch("run_tla_checks.find_tla_tools", return_value=Path("/fake/tla2tools.jar")):
            with patch("run_tla_checks.TLA_DIR", Path("/nonexistent/dir")):
                result = run_tlc("NonexistentModule")

        assert result.status == "error"
        assert "not found" in result.message.lower()

    @pytest.mark.unit
    def test_timeout_handled_gracefully(self):
        """
        Scenario: TLC times out on a complex model
        Given TLC takes longer than the timeout
        When run_tlc is called with a short timeout
        Then it should return status 'error' with timeout message
        """
        from run_tla_checks import run_tlc

        with patch("run_tla_checks.find_tla_tools", return_value=Path("/fake/tla2tools.jar")):
            with patch.object(Path, "exists", return_value=True):
                with patch(
                    "subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("java", 1)
                ):
                    result = run_tlc("SlowModule", timeout=1)

        assert result.status == "error"
        assert "timeout" in result.message.lower()


class TestSummaryReport:
    """Feature: Generate summary reports from TLC results."""

    @pytest.mark.unit
    def test_all_pass_returns_zero(self):
        """
        Scenario: All modules pass
        Given results where all modules have status 'pass'
        When print_summary is called
        Then it should return exit code 0
        """
        from run_tla_checks import TLCResult, print_summary

        results = [
            TLCResult(module="Magma", status="pass", elapsed_seconds=1.0, message="OK"),
            TLCResult(module="Model", status="pass", elapsed_seconds=2.0, message="OK"),
        ]
        assert print_summary(results) == 0

    @pytest.mark.unit
    def test_any_fail_returns_nonzero(self):
        """
        Scenario: One module fails
        Given results where one module failed
        When print_summary is called
        Then it should return non-zero exit code
        """
        from run_tla_checks import TLCResult, print_summary

        results = [
            TLCResult(module="Magma", status="pass", elapsed_seconds=1.0, message="OK"),
            TLCResult(
                module="Bad", status="fail", elapsed_seconds=0.5, message="Invariant violated"
            ),
        ]
        assert print_summary(results) != 0

    @pytest.mark.unit
    def test_skipped_modules_dont_cause_failure(self):
        """
        Scenario: Some modules skipped due to missing tools
        Given results where modules are skipped but none fail
        When print_summary is called
        Then it should return exit code 0
        """
        from run_tla_checks import TLCResult, print_summary

        results = [
            TLCResult(module="Magma", status="pass", elapsed_seconds=1.0, message="OK"),
            TLCResult(module="Model", status="skip", elapsed_seconds=0.0, message="No tools"),
        ]
        assert print_summary(results) == 0


class TestToolDiscovery:
    """Feature: Locate tla2tools.jar in standard locations."""

    @pytest.mark.unit
    def test_finds_jar_in_project_tools_dir(self):
        """
        Scenario: tla2tools.jar exists in project tla/tools/ directory
        Given tla2tools.jar is at tla/tools/tla2tools.jar
        When find_tla_tools is called
        Then it should return that path
        """
        from run_tla_checks import find_tla_tools

        with patch.object(Path, "exists", return_value=True):
            result = find_tla_tools()
        assert result is not None

    @pytest.mark.unit
    def test_returns_none_when_not_found(self):
        """
        Scenario: tla2tools.jar is not installed anywhere
        Given no tla2tools.jar exists in any standard location
        When find_tla_tools is called
        Then it should return None
        """
        from run_tla_checks import find_tla_tools

        with patch.object(Path, "exists", return_value=False):
            result = find_tla_tools()
        assert result is None
