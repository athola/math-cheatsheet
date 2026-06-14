#!/usr/bin/env python3
"""Behaviour-driven dogfood demo for the equational-theories decision stack.

This is a LIVE dogfood: every scenario runs the *real* project code on small
crafted inputs and prints the *real* observed output in Given/When/Then form.
It doubles as an executable specification — a non-zero exit means a behaviour
regressed, so it is safe to wire into pre-commit (`--quick`) and CI (full).

The scenarios encode the business logic and user-facing behaviour surfaced by
the 2026-06 full-review findings (B1-B9, H1/H2, M1): decision-procedure
soundness, congruence reasoning, structural classification, and robust parsing
of equations, LLM verdicts, and problem records — including edge cases and
negative tests.

Usage:
    python scripts/demo_behavior.py            # all scenarios (CI)
    python scripts/demo_behavior.py --quick    # truncated fast subset (pre-commit)
    python scripts/demo_behavior.py --list     # list scenarios without running
    python scripts/demo_behavior.py --feature parsing   # filter by feature slug
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# ── Make `src/` importable whether run via Makefile (PYTHONPATH set) or directly.
_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "src", _ROOT / "tla" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from competition_evaluator import _load_problems  # noqa: E402
from decision_procedure import DecisionProcedure  # noqa: E402
from equation_analyzer import ImplicationVerdict, analyze_implication  # noqa: E402
from equation_analyzer import parse_equation as ea_parse  # noqa: E402
from equation_parser_utils import tokenize_equation  # noqa: E402
from etp_equations import ETPEquations, parse_equation  # noqa: E402
from implication_oracle import ImplicationOracle  # noqa: E402
from llm_evaluator import parse_verdict  # noqa: E402

GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


# ── Tiny BDD recorder ────────────────────────────────────────────────────────
@dataclass
class Scenario:
    """Records and prints Given/When/Then steps and tracks pass/fail."""

    feature: str
    name: str
    failed: bool = False
    _checks: int = 0

    def _line(self, keyword: str, text: str) -> None:
        print(f"      {DIM}{keyword:<5}{RESET} {text}")

    def given(self, text: str) -> None:
        self._line("Given", text)

    def when(self, text: str) -> None:
        self._line("When", text)

    def and_(self, text: str) -> None:
        self._line("And", text)

    def observe(self, label: str, value: object) -> None:
        """Print real observed output — the heart of dogfooding."""
        self._line("→", f"{label}: {BOLD}{value}{RESET}")

    def then(self, text: str, ok: bool) -> None:
        self._checks += 1
        mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗ FAIL{RESET}"
        self._line("Then", f"{text}  {mark}")
        if not ok:
            self.failed = True


@dataclass
class Registered:
    feature: str
    slug: str
    name: str
    quick: bool
    negative: bool
    fn: Callable[[Scenario], None]


SCENARIOS: list[Registered] = []


def scenario(
    feature: str, slug: str, name: str, *, quick: bool = False, negative: bool = False
) -> Callable[[Callable[[Scenario], None]], Callable[[Scenario], None]]:
    def deco(fn: Callable[[Scenario], None]) -> Callable[[Scenario], None]:
        SCENARIOS.append(Registered(feature, slug, name, quick, negative, fn))
        return fn

    return deco


# ── Test-data helpers (small, self-contained — no network or ETP download) ────
@dataclass
class _Tmp:
    dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="dogfood_")))

    def equations(self, lines: list[str]) -> ETPEquations:
        p = self.dir / "equations.txt"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return ETPEquations(p)

    def matrix(self, rows: list[list[int]]) -> ImplicationOracle:
        p = self.dir / "implications.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        return ImplicationOracle(p)

    def jsonl(self, records: list[dict]) -> Path:
        p = self.dir / "problems.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        return p


# ═════════════════════════════════════════════════════════════════════════════
# Feature: decision — the decision procedure picks SOUND proofs over heuristics
# ═════════════════════════════════════════════════════════════════════════════
@scenario(
    "Decision procedure soundness",
    "decision",
    "A sound equivalence-class proof outranks the new-variable heuristic (M1)",
    quick=True,
)
def _decision_equiv_class_wins(s: Scenario) -> None:
    t = _Tmp()
    s.given("two equations sharing an identical (non-collapse) implication row")
    s.and_("the target equation Eq2 carries a 'new' variable z relative to Eq1")
    eqs = t.equations(["x ◇ y = y ◇ x", "x ◇ y = z", "x = x"])
    oracle = t.matrix([[3, 3, -3], [3, 3, -3], [-3, -3, 3]])
    s.when("the decision procedure predicts Eq1 ⇒ Eq2")
    r = DecisionProcedure(eqs, oracle).predict(1, 2)
    s.observe("prediction", r.prediction)
    s.observe("phase", r.phase)
    s.then("the sound equivalence-class prover wins (prediction is True)", r.prediction is True)
    s.then(
        "the proof is attributed to P5a-equiv-class, not a heuristic", r.phase == "P5a-equiv-class"
    )


@scenario(
    "Decision procedure soundness",
    "decision",
    "With no proof of non-implication, the procedure returns an honest default (B8)",
    quick=True,
)
def _decision_honest_default(s: Scenario) -> None:
    t = _Tmp()
    s.given("H = commutativity and T = (x ◇ x) ◇ y = y ◇ (x ◇ x), with no oracle")
    s.and_("no sound prover and no structural disproof settles the pair")
    eqs = t.equations(["x ◇ y = y ◇ x", "(x ◇ x) ◇ y = y ◇ (x ◇ x)"])
    proc = DecisionProcedure(eqs, oracle=None)
    s.when("the procedure predicts Eq1 ⇒ Eq2")
    r = proc.predict(1, 2)
    s.observe("phase", r.phase)
    s.observe("reason", r.reason)
    s.then(
        "it falls through to the honest default phase, never a fabricated proof",
        r.phase == "P6-default",
    )
    s.then("the reason flags the answer as a non-proof default", "not a proof" in r.reason.lower())


# ═════════════════════════════════════════════════════════════════════════════
# Feature: congruence — congruence consequences must never be refuted (H1, H2)
# ═════════════════════════════════════════════════════════════════════════════
@scenario(
    "Congruence soundness",
    "congruence",
    "A fresh-variable congruence consequence is not wrongly refuted (H1)",
    quick=True,
)
def _congruence_fresh_var(s: Scenario) -> None:
    s.given("H = commutativity:  x ◇ y = y ◇ x")
    s.and_("T introduces a fresh variable z but holds by congruence in every commutative magma")
    h, target = ea_parse("x ◇ y = y ◇ x"), ea_parse("(x ◇ y) ◇ z = (y ◇ x) ◇ z")
    s.when("we analyse whether H ⇒ T")
    r = analyze_implication(h, target)
    s.observe("verdict", r.verdict.value)
    s.then("the verdict is NOT a false refutation", r.verdict != ImplicationVerdict.FALSE)


@scenario(
    "Congruence soundness",
    "congruence",
    "A deep congruence consequence is not refuted by a depth heuristic (H2)",
)
def _congruence_deep(s: Scenario) -> None:
    s.given("H = commutativity:  x ◇ y = y ◇ x")
    s.and_("T has nesting depth 3 but still holds by congruence")
    h = ea_parse("x ◇ y = y ◇ x")
    target = ea_parse("x ◇ (y ◇ (x ◇ y)) = x ◇ (y ◇ (y ◇ x))")
    s.when("we analyse whether H ⇒ T")
    r = analyze_implication(h, target)
    s.observe("verdict", r.verdict.value)
    s.then(
        "the depth heuristic does not produce a false refutation",
        r.verdict != ImplicationVerdict.FALSE,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Feature: structure — structural classification of equation rows (B1, B5, B9)
# ═════════════════════════════════════════════════════════════════════════════
@scenario(
    "Structural classification",
    "structure",
    "Substitution-instance detection tries both variable-merge directions (B1)",
    quick=True,
)
def _structure_substitution_both_ways(s: Scenario) -> None:
    t = _Tmp()
    s.given("H: x ◇ y = x   and   T: y ◇ y = y  (obtained by merging into the *later* variable)")
    eqs = t.equations(["x ◇ y = x", "y ◇ y = y"])
    s.when("we ask whether T is a substitution instance of H")
    ok = eqs.is_substitution_instance(1, 2)
    s.observe("is_substitution_instance(1, 2)", ok)
    s.then("the later-variable merge direction is found", ok is True)


@scenario(
    "Structural classification",
    "structure",
    "A collapse with RHS depth > 1 is still detected (B5)",
)
def _structure_deep_collapse(s: Scenario) -> None:
    t = _Tmp()
    s.given("the equation  x = (y ◇ z) ◇ w  whose LHS variable x is absent from a depth-2 RHS")
    eqs = t.equations(["x = (y ◇ z) ◇ w"])
    s.when("we classify its structure")
    structural = eqs.is_collapse_structural(1)
    label = eqs.classify_structural(1)
    s.observe("is_collapse_structural(1)", structural)
    s.observe("classify_structural(1)", label)
    s.then(
        "the deep collapse forces |M| = 1 and is labelled 'collapse'",
        structural is True and label == "collapse",
    )


@scenario(
    "Structural classification",
    "structure",
    "A row with a single true entry is 'implies_self_only', not a tautology (B9)",
    quick=True,
)
def _structure_self_only(s: Scenario) -> None:
    t = _Tmp()
    s.given("a matrix where Eq2 implies only itself (one true entry on the diagonal)")
    oracle = t.matrix([[3, 3, 3], [-3, 3, -3], [-3, -3, 3]])
    s.when("we classify Eq2")
    label = oracle.classify(2)
    s.observe("classify(2)", label)
    s.then(
        "it is labelled 'implies_self_only', not mislabelled a tautology",
        label == "implies_self_only",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Feature: parsing — robust parsing of verdicts, equations, problems (B4,B7,B3,B2)
# ═════════════════════════════════════════════════════════════════════════════
@scenario(
    "Robust LLM verdict parsing",
    "parsing",
    "'NOT TRUE' is never misread as TRUE (B4)",
    quick=True,
    negative=True,
)
def _parsing_not_true(s: Scenario) -> None:
    s.given("an LLM response containing the substring 'TRUE' inside 'NOT TRUE'")
    text = "VERDICT: NOT TRUE"
    s.when(f"we parse the verdict from {text!r}")
    v = parse_verdict(text)
    s.observe("parse_verdict", v)
    s.then("the substring trap does not yield True", v is not True)


@scenario(
    "Robust LLM verdict parsing",
    "parsing",
    "Plain verdicts parse and trailing punctuation is tolerated (B4)",
    quick=True,
)
def _parsing_plain_verdicts(s: Scenario) -> None:
    s.given("well-formed verdict strings")
    cases = {"VERDICT: TRUE": True, "VERDICT: FALSE": False, "VERDICT: TRUE.": True}
    for text, expected in cases.items():
        s.when(f"we parse {text!r}")
        got = parse_verdict(text)
        s.observe("parse_verdict", got)
        s.then(f"it reads as {expected}", got is expected)


@scenario(
    "Robust equation tokenising",
    "parsing",
    "Alphanumeric variables survive tokenising (B7)",
)
def _parsing_alnum_var(s: Scenario) -> None:
    s.given("an equation with a multi-character variable name x1")
    s.when("we tokenise  x1 ◇ y = y ◇ x1")
    toks = tokenize_equation("x1 ◇ y = y ◇ x1")
    s.observe("tokens", toks)
    s.then("no characters are silently dropped", toks == ["x1", "*", "y", "=", "y", "*", "x1"])


@scenario(
    "Robust equation tokenising",
    "parsing",
    "An unexpected character is rejected, not swallowed (B7)",
    quick=True,
    negative=True,
)
def _parsing_bad_char(s: Scenario) -> None:
    s.given("an equation containing the unsupported character '$'")
    s.when("we tokenise  x $ y")
    raised = False
    try:
        tokenize_equation("x $ y")
    except ValueError as exc:
        raised = True
        s.observe("raised", f"ValueError: {exc}")
    s.then("a ValueError is raised instead of corrupt tokens", raised)


@scenario(
    "Problem-record loading",
    "parsing",
    "Malformed problem records are rejected (B3)",
    quick=True,
    negative=True,
)
def _parsing_bad_records(s: Scenario) -> None:
    t = _Tmp()
    s.given("a problems file whose record is missing the hypothesis/target ids")
    bad = t.jsonl([{"answer": True}])
    s.when("we load the problems")
    raised = False
    try:
        _load_problems(bad)
    except ValueError as exc:
        raised = True
        s.observe("raised", f"ValueError: {exc}")
    s.then("loading fails loudly rather than producing None ids", raised)


@scenario(
    "Problem-record loading",
    "parsing",
    "A well-formed problem record loads cleanly (B3)",
    quick=True,
)
def _parsing_good_record(s: Scenario) -> None:
    t = _Tmp()
    s.given("a problems file with one valid record")
    good = t.jsonl([{"hypothesis_id": 1, "target_id": 2, "answer": True}])
    s.when("we load the problems")
    probs = _load_problems(good)
    s.observe("first record", probs[0])
    s.then(
        "the ids and answer round-trip intact",
        probs[0]["hypothesis_id"] == 1
        and probs[0]["target_id"] == 2
        and probs[0]["answer"] is True,
    )


@scenario(
    "Data integrity",
    "parsing",
    "Equation variables are exposed as an immutable frozenset (B2)",
)
def _parsing_frozenset_vars(s: Scenario) -> None:
    s.given("a parsed equation  x ◇ y = y ◇ x")
    eq = parse_equation(1, "x ◇ y = y ◇ x")
    s.when("we inspect its .variables collection")
    s.observe("type", type(eq.variables).__name__)
    s.observe("value", sorted(eq.variables))
    s.then("the collection is an immutable frozenset", isinstance(eq.variables, frozenset))


# ── Runner ───────────────────────────────────────────────────────────────────
def _run(selected: list[Registered]) -> int:
    by_feature: dict[str, list[Registered]] = {}
    for reg in selected:
        by_feature.setdefault(reg.feature, []).append(reg)

    total = passed = 0
    failures: list[str] = []
    for feature, regs in by_feature.items():
        print(f"\n{BOLD}Feature: {feature}{RESET}")
        for reg in regs:
            tag = " [negative]" if reg.negative else ""
            print(f"\n  Scenario: {reg.name}{DIM}{tag}{RESET}")
            sc = Scenario(reg.feature, reg.name)
            try:
                reg.fn(sc)
            except Exception as exc:  # a crash is a failed scenario, not a traceback dump
                sc.failed = True
                print(f"      {RED}✗ raised {type(exc).__name__}: {exc}{RESET}")
            total += 1
            if sc.failed:
                failures.append(reg.name)
            else:
                passed += 1

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    status = f"{GREEN}PASS{RESET}" if not failures else f"{RED}FAIL{RESET}"
    print(f"Dogfood behaviour demo: {status} — {passed}/{total} scenarios green")
    if failures:
        print(f"{RED}Regressed:{RESET}")
        for name in failures:
            print(f"  - {name}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--quick", action="store_true", help="run only the fast pre-commit subset")
    parser.add_argument(
        "--feature", help="filter scenarios by feature slug (e.g. parsing, decision)"
    )
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = parser.parse_args()

    selected = SCENARIOS
    if args.quick:
        selected = [r for r in selected if r.quick]
    if args.feature:
        selected = [r for r in selected if r.slug == args.feature]

    if not selected:
        print("no scenarios matched the given filters", file=sys.stderr)
        return 2

    if args.list:
        for reg in selected:
            flags = "".join(["Q" if reg.quick else "-", "N" if reg.negative else "-"])
            print(f"  [{flags}] {reg.slug:<10} {reg.name}")
        return 0

    mode = "quick" if args.quick else "full"
    print(f"{BOLD}=== Decision-stack behaviour dogfood ({mode}) — LIVE ==={RESET}")
    return _run(selected)


if __name__ == "__main__":
    raise SystemExit(main())
