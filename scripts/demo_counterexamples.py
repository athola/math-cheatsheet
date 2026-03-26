#!/usr/bin/env python3
"""Demo: find counterexamples to classic non-implications.

Run via ``make demo-counterexamples`` which sets PYTHONPATH automatically.
The sys.path block below allows running the script standalone as well::

    python scripts/demo_counterexamples.py
"""

import sys
from pathlib import Path

# Allow running standalone (make demo-* sets PYTHONPATH automatically)
_root = Path(__file__).resolve().parent.parent
for _p in [_root / "src", _root / "tla" / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tla_bridge import generate_all_magmas  # noqa: E402

ms = generate_all_magmas(3)

ca = [m for m in ms if m.is_commutative() and not m.is_associative()]
ac = [m for m in ms if m.is_associative() and not m.is_commutative()]
ic = [m for m in ms if m.is_idempotent() and not m.is_commutative()]

print(f"Comm but not Assoc: {len(ca)} counterexamples")
if ca:
    print("First counterexample Cayley table:")
    print(ca[0].cayley_table_str())

print(f"Assoc but not Comm: {len(ac)} counterexamples")
if ac:
    print("First counterexample Cayley table:")
    print(ac[0].cayley_table_str())

print(f"Idemp but not Comm: {len(ic)} counterexamples")
if ic:
    print("First counterexample Cayley table:")
    print(ic[0].cayley_table_str())
