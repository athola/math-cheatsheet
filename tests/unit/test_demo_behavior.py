"""Guard tests for the behaviour-driven dogfood demo (scripts/demo_behavior.py).

The demo is itself an executable specification used in pre-commit and CI, so
these tests verify two things: that every live scenario passes against the real
code (the dogfood is green), and that the harness is a *genuine* guard — it
must report failure when a behaviour regresses, otherwise it would silently
pass forever.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent.parent
_DEMO = _ROOT / "scripts" / "demo_behavior.py"


def _load_demo():
    """Import scripts/demo_behavior.py as a module under its own name."""
    for p in (_ROOT / "src", _ROOT / "tla" / "python"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    spec = importlib.util.spec_from_file_location("demo_behavior", _DEMO)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec: @dataclass resolves cls.__module__ via sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def demo():
    return _load_demo()


@pytest.mark.unit
class TestDogfoodScenariosAreGreen:
    """
    Feature: Live behaviour dogfood

    As a maintainer of the decision stack
    I want every dogfood scenario to run the real code and pass
    So that a regression in business logic is caught before merge.
    """

    def test_full_suite_passes(self, demo):
        """
        Scenario: The full dogfood suite is green
        Given every registered behaviour scenario
        When the runner executes them against the real project code
        Then it returns exit code 0
        """
        assert demo._run(demo.SCENARIOS) == 0

    def test_quick_subset_passes(self, demo):
        """
        Scenario: The truncated pre-commit subset is green
        Given only the scenarios flagged quick=True
        When the runner executes them
        Then it returns exit code 0 and the subset is non-empty
        """
        quick = [r for r in demo.SCENARIOS if r.quick]
        assert quick, "the pre-commit subset must contain at least one scenario"
        assert demo._run(quick) == 0

    def test_quick_is_subset_of_full(self, demo):
        """
        Scenario: Quick scenarios are a strict subset of the full suite
        Given the quick subset and the full registry
        When we compare them
        Then every quick scenario is also in the full suite
        """
        quick = {r.name for r in demo.SCENARIOS if r.quick}
        full = {r.name for r in demo.SCENARIOS}
        assert quick <= full
        assert len(full) > len(quick)

    def test_negative_scenarios_present(self, demo):
        """
        Scenario: Edge/negative behaviours are covered
        Given the registry
        When we count scenarios marked negative
        Then at least three negative (rejection) scenarios exist
        """
        negatives = [r for r in demo.SCENARIOS if r.negative]
        assert len(negatives) >= 3


@pytest.mark.unit
class TestDogfoodGuardIsGenuine:
    """
    Feature: The dogfood harness fails loudly on regression

    As a maintainer
    I want the harness to return non-zero when any scenario regresses
    So that the pre-commit and CI gate cannot pass on broken behaviour.
    """

    def test_failed_then_marks_scenario_failed(self, demo):
        """
        Scenario: A false Then condition fails the scenario
        Given a fresh scenario recorder
        When a Then step is given a false condition
        Then the scenario is marked failed
        """
        sc = demo.Scenario("f", "n")
        sc.then("this should fail", False)
        assert sc.failed is True

    def test_runner_returns_nonzero_on_regression(self, demo):
        """
        Scenario: A regressed behaviour fails the gate
        Given a deliberately failing scenario injected into the runner
        When the runner executes it
        Then the runner returns a non-zero exit code
        """

        def broken(s):
            s.given("a behaviour that has regressed")
            s.then("an impossible assertion", 1 == 2)

        reg = demo.Registered("Synthetic", "synthetic", "regressed behaviour", False, False, broken)
        assert demo._run([reg]) == 1

    def test_runner_treats_crash_as_failure(self, demo):
        """
        Scenario: A scenario that raises is counted as a failure, not a crash
        Given a scenario whose body raises an exception
        When the runner executes it
        Then the runner returns non-zero instead of propagating the error
        """

        def explodes(_s):
            raise RuntimeError("synthetic crash")

        reg = demo.Registered("Synthetic", "synthetic", "crashing scenario", False, False, explodes)
        assert demo._run([reg]) == 1
