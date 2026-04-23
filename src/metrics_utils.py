"""Shared metric utilities for confusion-matrix tracking."""

from __future__ import annotations


def update_confusion(counts: dict[str, int], predicted: bool, actual: bool) -> None:
    """Increment the correct tp/fp/tn/fn cell in *counts*.

    All evaluation code shares this function so classification logic stays
    consistent if the cell names or branching ever change.
    """
    if predicted and actual:
        counts["tp"] += 1
    elif predicted and not actual:
        counts["fp"] += 1
    elif not predicted and actual:
        counts["fn"] += 1
    else:
        counts["tn"] += 1


def compute_accuracy_metrics(tp: int, fp: int, tn: int, fn: int) -> dict[str, float]:
    """Derive accuracy, precision, recall, and F1 from raw confusion counts."""
    total = tp + fp + tn + fn
    return {
        "accuracy": (tp + tn) / total if total > 0 else 0.0,
        "precision": tp / (tp + fp) if (tp + fp) > 0 else 0.0,
        "recall": tp / (tp + fn) if (tp + fn) > 0 else 0.0,
        "f1": (2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0),
    }
