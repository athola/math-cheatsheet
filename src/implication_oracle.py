"""Implication oracle for the ETP dataset.

Loads the 4694-equation implication matrix and provides fast queries.
The CSV contains 4693 rows x 4694 columns (equation 1 / x=x is omitted
as a row since it implies only itself, but appears as column 0).

Encoding:
    3  = proven TRUE (implication holds)
   -3  = proven FALSE (implication does not hold)
    4  = conjectured TRUE
   -4  = conjectured FALSE

Usage:
    oracle = ImplicationOracle("research/data/etp/implications.csv")
    result = oracle.query(43, 4512)  # Does eq 43 imply eq 4512?
    # Returns: True, False, or None (unknown)
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


class ImplicationOracle:
    """Fast lookup for the 22M implication matrix."""

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self._matrix: np.ndarray = np.array([], dtype=np.int8)
        self._eq_ids: list[int] = []  # row index → equation ID
        self._eq_to_row: dict[int, int] = {}  # equation ID → row index
        self._col_eq_ids: list[int] = []  # column index → equation ID
        self._eq_to_col: dict[int, int] = {}
        self._load()

    def _load(self):
        """Load the CSV into a numpy array for fast queries."""
        rows = []
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append([int(x) for x in row])

        self._matrix = np.array(rows, dtype=np.int8)
        n_rows, n_cols = self._matrix.shape

        # Matrix is 4694x4694. Row i = Col i = Equation (i+1).
        # Verified: diagonal is all TRUE (self-implication),
        # row 0 implies only 1 (tautology x=x), row 1 implies all (collapse x=y).
        self._eq_ids = list(range(1, n_rows + 1))
        self._col_eq_ids = list(range(1, n_cols + 1))
        self._eq_to_row = {eq_id: i for i, eq_id in enumerate(self._eq_ids)}
        self._eq_to_col = {eq_id: j for j, eq_id in enumerate(self._col_eq_ids)}

        # Build equivalence classes: equations with identical row profiles
        self._eq_to_equiv: dict[int, int] = {}
        self._equiv_classes: dict[int, set[int]] = {}
        self._build_equivalence_classes()

    def _build_equivalence_classes(self):
        """Group equations by identical row profiles.

        Equations with the same row in the implication matrix imply exactly
        the same targets. By the diagonal argument (self-implication is TRUE),
        same-row equations mutually imply each other.
        """
        row_hash_to_class: dict[bytes, int] = {}
        class_id = 0
        for i, eq_id in enumerate(self._eq_ids):
            row_bytes = self._matrix[i].tobytes()
            if row_bytes not in row_hash_to_class:
                row_hash_to_class[row_bytes] = class_id
                class_id += 1
            cid = row_hash_to_class[row_bytes]
            self._eq_to_equiv[eq_id] = cid
            if cid not in self._equiv_classes:
                self._equiv_classes[cid] = set()
            self._equiv_classes[cid].add(eq_id)

    def equivalence_class(self, eq_id: int) -> int | None:
        """Return the equivalence class ID for an equation.

        Equations in the same class have identical implication row profiles
        and mutually imply each other. Returns None if eq_id is out of range.
        """
        return self._eq_to_equiv.get(eq_id)

    @property
    def equivalence_classes(self) -> dict[int, set[int]]:
        """Return all equivalence classes: class_id -> set of equation IDs."""
        return self._equiv_classes

    @property
    def num_equations(self) -> int:
        return len(self._col_eq_ids)

    @property
    def shape(self) -> tuple[int, int]:
        return self._matrix.shape

    def query(self, hypothesis_id: int, target_id: int) -> bool | None:
        """Query whether hypothesis implies target.

        Returns True, False, or None (unknown/out of range).
        """
        if hypothesis_id not in self._eq_to_row:
            return None
        if target_id not in self._eq_to_col:
            return None

        row = self._eq_to_row[hypothesis_id]
        col = self._eq_to_col[target_id]
        val = int(self._matrix[row, col])

        if val in (3, 4):
            return True
        elif val in (-3, -4):
            return False
        return None

    def query_raw(self, hypothesis_id: int, target_id: int) -> int:
        """Return raw matrix value (3, -3, 4, -4)."""
        row = self._eq_to_row.get(hypothesis_id)
        col = self._eq_to_col.get(target_id)
        if row is None or col is None:
            return 0
        return int(self._matrix[row, col])

    def row_true_count(self, eq_id: int) -> int:
        """How many equations does eq_id imply?"""
        row = self._eq_to_row.get(eq_id)
        if row is None:
            return 0
        return int(np.sum((self._matrix[row] == 3) | (self._matrix[row] == 4)))

    def col_true_count(self, eq_id: int) -> int:
        """How many equations imply eq_id?"""
        col = self._eq_to_col.get(eq_id)
        if col is None:
            return 0
        return int(np.sum((self._matrix[:, col] == 3) | (self._matrix[:, col] == 4)))

    def is_collapse(self, eq_id: int) -> bool:
        """Does this equation imply ALL others (force |M|=1)?"""
        return self.row_true_count(eq_id) == self.num_equations

    def classify(self, eq_id: int) -> str:
        """Classify equation by implication strength."""
        n = self.row_true_count(eq_id)
        total = self.num_equations
        if n == total:
            return "collapse"
        if n == 1:
            return "tautology"
        if n <= 5:
            return "weak"
        if n <= 1000:
            return "mid"
        return "strong"

    def accuracy_of(self, predict_fn) -> dict[str, object]:
        """Evaluate a prediction function against the full matrix.

        predict_fn(hypothesis_id, target_id) -> bool

        Returns accuracy metrics.
        """
        tp = fp = tn = fn = 0

        for i, h_id in enumerate(self._eq_ids):
            for j, t_id in enumerate(self._col_eq_ids):
                actual_val = int(self._matrix[i, j])
                if actual_val in (3, 4):
                    actual = True
                elif actual_val in (-3, -4):
                    actual = False
                else:
                    continue

                predicted = predict_fn(h_id, t_id)

                if predicted and actual:
                    tp += 1
                elif predicted and not actual:
                    fp += 1
                elif not predicted and actual:
                    fn += 1
                else:
                    tn += 1

        # Matrix is now 4694x4694 with all equations including eq 1,
        # so the loop above covers everything.

        total = tp + fp + tn + fn
        accuracy = (tp + tn) / total if total > 0 else 0.0

        return {
            "accuracy": accuracy,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": tp / (tp + fp) if (tp + fp) > 0 else 0.0,
            "recall": tp / (tp + fn) if (tp + fn) > 0 else 0.0,
            "total": total,
        }

    def stats(self) -> dict:
        """Return summary statistics about the matrix."""
        m = self._matrix
        return {
            "shape": m.shape,
            "proven_true": int(np.sum(m == 3)),
            "proven_false": int(np.sum(m == -3)),
            "conj_true": int(np.sum(m == 4)),
            "conj_false": int(np.sum(m == -4)),
            "equation_ids": (min(self._col_eq_ids), max(self._col_eq_ids)),
        }


if __name__ == "__main__":
    oracle = ImplicationOracle("research/data/etp/implications.csv")
    stats = oracle.stats()
    print("=== Implication Oracle ===")
    print(f"Shape: {stats['shape']}")
    print(f"Proven TRUE:  {stats['proven_true']:,}")
    print(f"Proven FALSE: {stats['proven_false']:,}")
    print(f"Conj TRUE:    {stats['conj_true']:,}")
    print(f"Conj FALSE:   {stats['conj_false']:,}")
    print(f"Equation range: {stats['equation_ids']}")

    # Test some known implications
    print("\n=== Spot checks ===")
    for h, t in [(2, 43), (43, 2), (2, 2), (1, 1), (1, 43)]:
        result = oracle.query(h, t)
        print(f"  E{h} => E{t}: {result}")

    # Classification distribution
    from collections import Counter

    classes: Counter[str] = Counter()
    for eq_id in oracle._col_eq_ids:
        classes[oracle.classify(eq_id)] += 1
    print("\n=== Classification ===")
    for cls, count in classes.most_common():
        print(f"  {cls}: {count}")
