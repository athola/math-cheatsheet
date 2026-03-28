#!/usr/bin/env python3
"""Demo: count magma properties across small sizes.

Run via ``make demo-properties`` which sets PYTHONPATH automatically.
The sys.path block below allows running the script standalone as well::

    python scripts/demo_properties.py
"""

import sys
from pathlib import Path

# Allow running standalone (make demo-* sets PYTHONPATH automatically)
_root = Path(__file__).resolve().parent.parent
for _p in [_root / "src", _root / "tla" / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tla_bridge import generate_all_magmas  # noqa: E402

for n in [2, 3]:
    ms = generate_all_magmas(n)
    a = sum(1 for m in ms if m.is_associative())
    c = sum(1 for m in ms if m.is_commutative())
    i = sum(1 for m in ms if m.has_identity() is not None)
    d = sum(1 for m in ms if m.is_idempotent())
    print(f"Size {n}: {len(ms)} magmas | assoc={a} comm={c} identity={i} idemp={d}")
