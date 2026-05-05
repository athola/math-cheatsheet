"""Lean 4 proof coverage scanner and dashboard (issue #25).

Walks a directory of ``.lean`` files, extracts each top-level
declaration (``theorem``, ``lemma``, ``def``, ``example``), notes whether
the body still contains ``sorry`` or ``admit`` placeholders, and reports
how much of the corpus has a finished proof.

This is a lightweight dashboard — the goal is visibility, not formal
verification. "Finished" means the text of the declaration contains no
placeholder; the scanner does not invoke ``lean`` itself, so the caller
should understand that a declaration counted as finished may still fail
to compile. Checking compilation is a job for the Lean toolchain and
would belong in a CI step, not in this coverage report.

Intended use from the CLI::

    uv run python -m lean_coverage [lean_root]

Emits a human-readable summary followed by the full inventory. For
machine consumption, callers can import ``scan_lean_declarations`` /
``compute_coverage`` directly.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_DECLARATION_RE = re.compile(
    r"""
    ^                    # start of line
    (?:@\[[^\]]*\]\s*)*  # optional @[attr] prefix(es) — e.g. @[simp]
    (?:                  # optional visibility / modifier prefix
        (?:private|protected|noncomputable)
        \s+
    )?
    (?P<kind>theorem|lemma|def|example|instance|structure)
    \b                   # keyword boundary
    \s*
    (?P<name>[^\s:({\[]+)?  # name (optional for `example`/`instance`)
    """,
    re.VERBOSE | re.MULTILINE,
)

_PLACEHOLDER_RE = re.compile(r"\b(?:sorry|admit)\b")

# NEW-C3: strip Lean comments and string literals before scanning for
# placeholder keywords. Matches ``-- to end of line``, ``/- ... -/`` block
# comments (single-level — sufficient for typical project Lean), and
# double-quoted string literals.
_COMMENT_OR_STRING_RE = re.compile(
    r"""
      --[^\n]*           # line comment to end of line
    | /-.*?-/            # block comment, lazy match (single level)
    | "(?:\\.|[^"\\])*"  # string literal with escapes
    """,
    re.VERBOSE | re.DOTALL,
)


def _strip_comments_and_strings(text: str) -> str:
    """Replace comments and string literals with whitespace of equal length.

    Preserves line numbers and column positions so that downstream regexes
    (declaration matching, placeholder scan) operate on the same text
    layout as the source.
    """
    return _COMMENT_OR_STRING_RE.sub(lambda m: " " * len(m.group(0)), text)


@dataclass(frozen=True)
class LeanDeclaration:
    """One top-level declaration in a Lean file.

    Stored as data so downstream tooling (tests, CLI output, CI checks)
    can filter and regroup without re-parsing the source.
    """

    path: Path
    kind: str
    name: str
    unfinished: bool


@dataclass(frozen=True)
class CoverageSummary:
    total: int
    finished: int
    unfinished: int
    percentage: float
    by_kind: dict[str, int]


_DEFAULT_EXCLUDE_DIRS = frozenset({".lake", "lake-packages", "build"})


def scan_lean_declarations(
    root: Path, exclude_dirs: frozenset[str] = _DEFAULT_EXCLUDE_DIRS
) -> list[LeanDeclaration]:
    """Recursively scan ``root`` for ``.lean`` files and extract declarations.

    The regex-based scanner is intentionally simple: it catches the four
    kinds that appear in the existing ``lean/EquationalTheories`` tree
    (``theorem``, ``lemma``, ``def``, ``example``) and assigns each to
    the text that runs until the next top-level keyword or end of file.
    That's enough to count placeholders without depending on the Lean
    parser, which would need a full Lean toolchain to run.

    Skips vendored dependency directories by default (``.lake``,
    ``lake-packages``, ``build``) so the dashboard reflects
    project-local proofs instead of Mathlib's 100K+ theorems. Pass an
    explicit ``exclude_dirs`` (possibly empty) to override.

    Files that cannot be read (non-UTF-8 encoding, permission denied,
    transient I/O failure) are logged at WARNING level and skipped instead
    of aborting the whole scan (NEW-I10 / regression #61). For a coverage
    dashboard, surfacing partial results with a warning is more useful
    than crashing on one bad file.
    """
    results: list[LeanDeclaration] = []
    for lean_file in sorted(root.rglob("*.lean")):
        if any(part in exclude_dirs for part in lean_file.parts):
            continue
        try:
            text = lean_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError) as exc:
            logger.warning(
                "lean_coverage: skipping unreadable file %s (%s: %s)",
                lean_file,
                type(exc).__name__,
                exc,
            )
            continue
        results.extend(_extract_declarations(lean_file, text))
    return results


def _extract_declarations(path: Path, text: str) -> list[LeanDeclaration]:
    """Pull declarations out of one file's text.

    Comments and string literals are blanked out before the placeholder
    scan so ``-- TODO: remove sorry`` does not mark a finished proof
    unfinished (NEW-C3). Declaration matching uses the original text so
    column positions in error messages stay accurate.
    """
    matches = list(_DECLARATION_RE.finditer(text))
    stripped = _strip_comments_and_strings(text)
    results: list[LeanDeclaration] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = stripped[start:end]
        unfinished = bool(_PLACEHOLDER_RE.search(body))
        kind = match.group("kind")
        name = match.group("name") or "<anonymous>"
        # Strip a trailing colon or brace that the regex may capture with the
        # name (e.g. ``theorem foo:`` in one-liners).
        name = name.rstrip(":{")
        results.append(LeanDeclaration(path=path, kind=kind, name=name, unfinished=unfinished))
    return results


def compute_coverage(declarations: list[LeanDeclaration]) -> CoverageSummary:
    """Summarise the inventory into a CoverageSummary.

    When there are zero declarations we report 0% rather than raising —
    an empty project should not crash the dashboard.
    """
    total = len(declarations)
    finished = sum(1 for d in declarations if not d.unfinished)
    unfinished = total - finished
    percentage = (finished / total * 100.0) if total else 0.0
    by_kind: dict[str, int] = {}
    for d in declarations:
        by_kind[d.kind] = by_kind.get(d.kind, 0) + 1
    return CoverageSummary(
        total=total,
        finished=finished,
        unfinished=unfinished,
        percentage=percentage,
        by_kind=by_kind,
    )


def _format_report(summary: CoverageSummary, declarations: list[LeanDeclaration]) -> str:
    """Human-readable dashboard. Printed by ``__main__`` below."""
    lines = [
        "Lean 4 Proof Coverage",
        "=" * 40,
        f"Total declarations: {summary.total}",
        f"Finished (no sorry/admit): {summary.finished}",
        f"Unfinished: {summary.unfinished}",
        f"Coverage: {summary.percentage:.1f}%",
        "",
        "By kind:",
    ]
    for kind, count in sorted(summary.by_kind.items()):
        lines.append(f"  {kind}: {count}")
    if summary.unfinished:
        lines.extend(["", "Unfinished declarations (competition-relevance gaps):"])
        for d in declarations:
            if d.unfinished:
                lines.append(f"  [{d.kind}] {d.name}  ({d.path})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m lean_coverage [path]``."""
    description = (__doc__ or "").split("\n", maxsplit=1)[0]
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "path",
        nargs="?",
        default="lean",
        type=Path,
        help="Root directory to scan for .lean files (default: ./lean)",
    )
    args = parser.parse_args(argv)
    if not args.path.exists():
        print(f"No such directory: {args.path}")
        return 2
    declarations = scan_lean_declarations(args.path)
    summary = compute_coverage(declarations)
    print(_format_report(summary, declarations))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "LeanDeclaration",
    "CoverageSummary",
    "scan_lean_declarations",
    "compute_coverage",
    "main",
]
