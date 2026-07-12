"""Shared equation tokenizer used by equation_analyzer and etp_equations."""

from __future__ import annotations

import warnings


def tokenize_equation(s: str, *, strict: bool = False) -> list[str]:
    """Tokenize an equation string, normalizing all operator variants to '*'.

    Handles: ◇ (U+22C7), ⋄ (U+22C4), and * as the binary operation.
    Produces: variable names, '*', '(', ')', '='.

    Unknown characters (digits, punctuation, non-supported unicode) are
    surfaced rather than silently dropped (S6 / regression #54). By default
    a :class:`UserWarning` is emitted listing the offending characters and
    their indices; pass ``strict=True`` to raise :class:`ValueError`
    instead. Whitespace is always ignored.
    """
    tokens: list[str] = []
    unknown: list[tuple[int, str]] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c in "()=":
            tokens.append(c)
            i += 1
        elif c in ("*", "◇", "⋄"):
            tokens.append("*")
            i += 1
        elif c.isalpha():
            j = i
            while j < len(s) and s[j].isalpha():
                j += 1
            tokens.append(s[i:j])
            i = j
        else:
            unknown.append((i, c))
            i += 1
    if unknown:
        # Show up to the first 5 offenders verbatim so the message remains
        # bounded for pathological inputs.
        sample = ", ".join(f"{c!r}@{idx}" for idx, c in unknown[:5])
        more = "" if len(unknown) <= 5 else f" (+{len(unknown) - 5} more)"
        message = (
            f"tokenize_equation: dropped {len(unknown)} unrecognised char(s)"
            f" in {s!r}: {sample}{more}."
            " Allowed: alphabetics, '*', '◇', '⋄', '(', ')', '=', whitespace."
        )
        if strict:
            raise ValueError(message)
        warnings.warn(message, UserWarning, stacklevel=2)
    return tokens
