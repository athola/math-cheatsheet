#!/usr/bin/env python3
"""Demo: count magma properties across small sizes."""

# Run via: make demo-properties (sets PYTHONPATH automatically)

from tla_bridge import generate_all_magmas

for n in [2, 3]:
    ms = generate_all_magmas(n)
    a = sum(1 for m in ms if m.is_associative())
    c = sum(1 for m in ms if m.is_commutative())
    i = sum(1 for m in ms if m.has_identity() is not None)
    d = sum(1 for m in ms if m.is_idempotent())
    print(f"Size {n}: {len(ms)} magmas | assoc={a} comm={c} identity={i} idemp={d}")
