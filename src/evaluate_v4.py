"""Evaluate the v4 decision procedure against the full implication matrix.

This implements the same logic as cheatsheet/v4.txt programmatically,
to measure accuracy on the 22M implication pairs.
"""

from __future__ import annotations

import time

from etp_equations import ETPEquations
from implication_oracle import ImplicationOracle


def build_v4_procedure(
    eqs: ETPEquations, oracle: ImplicationOracle
) -> tuple[set[int], set[int], set[int], set[int]]:
    """Pre-compute equation sets for the v4 decision procedure."""
    collapse_ids = set(i for i in range(1, 4695) if oracle.is_collapse(i))

    tier_1556_ids = set(i for i in range(1, 4695) if oracle.row_true_count(i) == 1556)
    tier_1214_ids = set(i for i in range(1, 4695) if oracle.row_true_count(i) == 1214)

    # Compute common targets for tier 1556
    tier_1556_targets: set[int] = set()
    for eid in list(tier_1556_ids)[:10]:
        row = oracle._matrix[oracle._eq_to_row[eid]]
        this_true = set(j + 1 for j in range(4694) if row[j] in (3, 4))
        tier_1556_targets = this_true if not tier_1556_targets else tier_1556_targets & this_true

    # Common targets for tier 1214
    tier_1214_targets: set[int] = set()
    for eid in list(tier_1214_ids)[:10]:
        row = oracle._matrix[oracle._eq_to_row[eid]]
        this_true = set(j + 1 for j in range(4694) if row[j] in (3, 4))
        tier_1214_targets = this_true if not tier_1214_targets else tier_1214_targets & this_true

    return collapse_ids, tier_1556_ids | tier_1214_ids, tier_1556_targets, tier_1214_targets


def v4_predict(
    h_id: int,
    t_id: int,
    eqs: ETPEquations,
    collapse_ids: set[int],
    strong_ids: set[int],
    tier_1556_targets: set[int],
    tier_1214_targets: set[int],
    oracle: ImplicationOracle,
) -> bool:
    """V4 decision procedure prediction."""
    # Step 1: Identical
    if h_id == t_id:
        return True

    # Step 2: Tautology target
    if t_id in eqs and eqs[t_id].is_tautology:
        return True

    # Step 3: Collapse hypothesis
    if h_id in collapse_ids:
        return True

    # Step 4: Tautology hypothesis
    if h_id in eqs and eqs[h_id].is_tautology:
        return False

    # Step 5: Constant operation (tier 1556)
    if oracle.row_true_count(h_id) == 1556 and t_id in tier_1556_targets:
        return True

    # Step 6: Projection (tier 1214)
    if oracle.row_true_count(h_id) == 1214 and t_id in tier_1214_targets:
        return True

    # Step 7: Variable analysis (skip for strong equations)
    if h_id in eqs and t_id in eqs:
        h_strength = oracle.row_true_count(h_id)
        new_vars = eqs.vars_in_target_not_in_hypothesis(h_id, t_id)
        if new_vars and h_strength < 300:
            return False

    # Step 10: Default FALSE
    return False


def main() -> None:
    print("Loading data...")
    eqs = ETPEquations("research/data/etp/equations.txt")
    oracle = ImplicationOracle("research/data/etp/implications.csv")

    print("Building v4 procedure...")
    collapse_ids, strong_ids, t1556_targets, t1214_targets = build_v4_procedure(eqs, oracle)

    print(f"Collapse: {len(collapse_ids)}, Strong: {len(strong_ids)}")
    print(f"T1556 targets: {len(t1556_targets)}, T1214 targets: {len(t1214_targets)}")

    # Evaluate on full matrix
    print("\nEvaluating on full 22M matrix...")
    t0 = time.time()

    tp = fp = tn = fn = 0
    matrix = oracle._matrix
    n = matrix.shape[0]

    for i in range(n):
        h_id = i + 1
        for j in range(n):
            t_id = j + 1
            val = int(matrix[i, j])
            if val in (3, 4):
                actual = True
            elif val in (-3, -4):
                actual = False
            else:
                continue

            pred = v4_predict(
                h_id,
                t_id,
                eqs,
                collapse_ids,
                strong_ids,
                t1556_targets,
                t1214_targets,
                oracle,
            )

            if pred and actual:
                tp += 1
            elif pred and not actual:
                fp += 1
            elif not pred and actual:
                fn += 1
            else:
                tn += 1

    elapsed = time.time() - t0
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total

    print(f"\nTime: {elapsed:.0f}s")
    print(f"Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"  TP={tp:,}  FP={fp:,}  TN={tn:,}  FN={fn:,}")
    if tp + fp > 0:
        print(f"  Precision: {tp / (tp + fp):.4f}")
    if tp + fn > 0:
        print(f"  Recall:    {tp / (tp + fn):.4f}")


if __name__ == "__main__":
    main()
