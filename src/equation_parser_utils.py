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
            j = i
            while j < len(s) and s[j].isalpha():
                j += 1
            tokens.append(s[i:j])
            i = j
        else:
            i += 1
    return tokens
