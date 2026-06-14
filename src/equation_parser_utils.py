"""Shared equation tokenizer used by equation_analyzer and etp_equations."""

from __future__ import annotations


def tokenize_equation(s: str) -> list[str]:
    """Tokenize an equation string, normalizing all operator variants to '*'.

    Handles: ◇ (U+22C7), ⋄ (U+22C4), and * as the binary operation.
    Produces: variable names, '*', '(', ')', '='.
    """
    tokens: list[str] = []
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
            # Variable names start with a letter and may continue with
            # alphanumerics (e.g. ``x1``). The previous ``isalpha``-only scan
            # silently dropped trailing digits, mangling such names (review B7).
            j = i
            while j < len(s) and s[j].isalnum():
                j += 1
            tokens.append(s[i:j])
            i = j
        else:
            # Surface malformed input instead of silently skipping characters
            # (review B7); the old ``i += 1`` discard hid parse errors.
            raise ValueError(f"Unexpected character {c!r} at position {i} in {s!r}")
    return tokens
