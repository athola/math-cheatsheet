#!/usr/bin/env python3
"""Demo: find counterexamples to classic non-implications."""

# Run via: make demo-counterexamples (sets PYTHONPATH automatically)

from tla_bridge import generate_all_magmas

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
