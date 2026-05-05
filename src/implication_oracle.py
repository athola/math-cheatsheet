"""Implication oracle for the ETP dataset.

Loads the 4694-equation implication matrix and provides fast queries.

Expected CSV format
-------------------
- **Shape**: square N x N (N = 4694 for the full ETP dataset).
- **Dtype**: integer values in the set ``{-4, -3, 3, 4}``; no zeros, no other
  integers. Row ``i`` describes what equation ``i+1`` implies about the
  equations in each column.

Encoding
--------
    3  = proven TRUE (implication holds)
   -3  = proven FALSE (implication does not hold)
    4  = conjectured TRUE
   -4  = conjectured FALSE

Validation
----------
At construction time the oracle enforces four integrity checks and raises
``ValueError`` (or ``FileNotFoundError``) with remediation hints if any fail:

1. The file must exist (hint: ``make download-etp``).
2. Every row must have the same number of columns (no ragged rows).
3. The matrix must be square.
4. All entries must be in the encoding set above.

Usage
-----
    oracle = ImplicationOracle("research/data/etp/implications.csv")
    result = oracle.query(43, 4512)  # Does eq 43 imply eq 4512?
    # Returns: True, False, or None (unknown)
"""

from __future__ import annotations

import csv
import functools
import hashlib
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final, NamedTuple

import numpy as np

# Single source of truth for the matrix encoding (S4 / regression #53).
# decode_truth() and the _VALID_VALUES validator both derive from this
# mapping so that the encoding cannot drift between the two sites.
_ENCODING: Final[Mapping[int, bool | None]] = MappingProxyType(
    {3: True, 4: True, -3: False, -4: False}
)


class _EquivData(NamedTuple):
    """Equivalence-class views over the implication matrix (S5 / #53).

    Replaces a bare ``tuple[dict, dict]`` whose positional indexing was
    bug-prone — a transposed ``self._equiv_data[1].get(eq_id)`` would
    return a frozenset where an int was expected. NamedTuple access via
    ``.eq_to_class`` / ``.classes_by_id`` self-documents and prevents
    transposition mistakes.
    """

    eq_to_class: dict[int, int]
    classes_by_id: dict[int, frozenset[int]]


class ImplicationOracle:
    """Fast lookup for the 22M implication matrix."""

    def __init__(self, csv_path: str | Path, *, expected_sha256: str | None = None):
        """Load and validate an ETP implication CSV.

        Parameters
        ----------
        csv_path:
            Path to the matrix CSV.
        expected_sha256:
            Optional SHA-256 hex digest. When provided, the file's digest
            must match or ``ValueError`` is raised (regression #22). When
            ``csv_path.with_suffix(csv_path.suffix + ".sha256")`` exists,
            its contents are used as the expected digest automatically.
        """
        self.csv_path = Path(csv_path)
        self._matrix: np.ndarray = np.array([], dtype=np.int8)
        self._eq_ids: list[int] = []  # row index → equation ID
        self._eq_to_row: dict[int, int] = {}  # equation ID → row index
        self._col_eq_ids: list[int] = []  # column index → equation ID
        self._eq_to_col: dict[int, int] = {}
        self._expected_sha256 = expected_sha256 or self._load_sidecar_digest()
        self._load()

    def _load_sidecar_digest(self) -> str | None:
        """Return the digest from a sibling ``.sha256`` file, if present."""
        sidecar = self.csv_path.with_suffix(self.csv_path.suffix + ".sha256")
        if not sidecar.exists():
            return None
        raw = sidecar.read_text(encoding="utf-8").strip()
        # Common sha256sum format: "<hex>  <filename>". Take just the hex.
        return raw.split()[0] if raw else None

    def _verify_digest(self) -> None:
        """Raise if the file digest does not match the expected one."""
        if self._expected_sha256 is None:
            return
        hasher = hashlib.sha256()
        with open(self.csv_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        actual = hasher.hexdigest()
        if actual.lower() != self._expected_sha256.lower():
            raise ValueError(
                f"Implication matrix checksum mismatch for {self.csv_path}:"
                f" expected {self._expected_sha256[:16]}..., got {actual[:16]}..."
                " Run `make download-etp` to refetch a clean copy."
            )

    # Final marker (S4 / #53): static analysers now flag any reassignment.
    # Derived from the single-source-of-truth ``_ENCODING`` so the validator
    # and ``decode_truth`` cannot drift apart.
    _VALID_VALUES: Final[tuple[int, ...]] = tuple(sorted(_ENCODING))

    def _load(self):
        """Load the CSV into a numpy array for fast queries.

        Validates shape and encoding. See module docstring for the contract.
        """
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Implication matrix CSV not found at {self.csv_path}."
                " Run `make download-etp` to fetch it from the ETP repository."
            )

        if self._expected_sha256 is not None:
            self._verify_digest()

        rows: list[list[int]] = []
        row_len: int | None = None
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            for line_no, row in enumerate(reader, start=1):
                parsed = [int(x) for x in row]
                if row_len is None:
                    row_len = len(parsed)
                elif len(parsed) != row_len:
                    raise ValueError(
                        f"Ragged matrix in {self.csv_path}: row {line_no} has"
                        f" {len(parsed)} columns, expected {row_len}."
                    )
                rows.append(parsed)

        self._matrix = np.array(rows, dtype=np.int8)
        n_rows, n_cols = self._matrix.shape
        if n_rows != n_cols:
            raise ValueError(
                f"Implication matrix must be square; got shape {n_rows}x{n_cols}"
                f" from {self.csv_path}. A truncated or mismatched file is the"
                " most likely cause — try `make download-etp` to refetch."
            )
        invalid_mask = ~np.isin(self._matrix, self._VALID_VALUES)
        if invalid_mask.any():
            bad_count = int(invalid_mask.sum())
            sample_idx = tuple(int(v) for v in np.argwhere(invalid_mask)[0])
            sample_val = int(self._matrix[sample_idx])
            raise ValueError(
                f"Implication matrix has {bad_count} entr{'y' if bad_count == 1 else 'ies'}"
                f" with invalid encoding (first: value {sample_val} at {sample_idx});"
                f" expected one of {self._VALID_VALUES}."
            )

        # Matrix is 4694x4694. Row i = Col i = Equation (i+1).
        # Verified: diagonal is all TRUE (self-implication),
        # row 0 implies only 1 (tautology x=x), row 1 implies all (collapse x=y).
        self._eq_ids = list(range(1, n_rows + 1))
        self._col_eq_ids = list(range(1, n_cols + 1))
        self._eq_to_row = {eq_id: i for i, eq_id in enumerate(self._eq_ids)}
        self._eq_to_col = {eq_id: j for j, eq_id in enumerate(self._col_eq_ids)}

    @functools.cached_property
    def _equiv_data(self) -> _EquivData:
        """Build equivalence class maps lazily (O(n²) row hashing, deferred until first use).

        Class members are stored as ``frozenset`` rather than ``set`` so that
        callers receiving them via :pyattr:`equivalence_classes` cannot
        corrupt the cache via ``.discard``/``.add`` (regression #52/M4).

        Returns a :class:`_EquivData` named tuple so call sites use named
        access (``.eq_to_class`` / ``.classes_by_id``) instead of positional
        indexing (S5 / #53).
        """
        eq_to_equiv: dict[int, int] = {}
        equiv_classes_mut: dict[int, set[int]] = {}
        row_hash_to_class: dict[bytes, int] = {}
        class_id = 0
        for i, eq_id in enumerate(self._eq_ids):
            row_bytes = self._matrix[i].tobytes()
            if row_bytes not in row_hash_to_class:
                row_hash_to_class[row_bytes] = class_id
                class_id += 1
            cid = row_hash_to_class[row_bytes]
            eq_to_equiv[eq_id] = cid
            equiv_classes_mut.setdefault(cid, set()).add(eq_id)
        equiv_classes: dict[int, frozenset[int]] = {
            cid: frozenset(members) for cid, members in equiv_classes_mut.items()
        }
        return _EquivData(eq_to_class=eq_to_equiv, classes_by_id=equiv_classes)

    def equivalence_class(self, eq_id: int) -> int | None:
        """Return the equivalence class ID for an equation, or None if out of range."""
        return self._equiv_data.eq_to_class.get(eq_id)

    @property
    def equivalence_classes(self) -> Mapping[int, frozenset[int]]:
        """Return all equivalence classes: class_id -> frozenset of equation IDs.

        The mapping itself is a :class:`types.MappingProxyType` view so callers
        cannot insert/replace classes; the values are :class:`frozenset` so
        callers cannot mutate class membership (regression #52/M4).
        """
        return MappingProxyType(self._equiv_data.classes_by_id)

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
        return self.decode_truth(self._matrix[row, col])

    @staticmethod
    def decode_truth(val: int | np.integer) -> bool | None:
        """Decode a raw matrix value into a tri-state truth.

        Returns ``True`` for proven or conjectured TRUE (3, 4),
        ``False`` for proven or conjectured FALSE (-3, -4),
        and ``None`` for any other value (no prior art). Centralising this
        decoding removes the duplicated ``if val in (3, 4) ...`` ladder that
        lived in five call sites (regression #43/I1). The mapping itself
        lives in module-level ``_ENCODING`` so that the ``_VALID_VALUES``
        validator and this decoder cannot drift apart (S4 / regression #53).
        """
        return _ENCODING.get(int(val))

    def query_raw(self, hypothesis_id: int, target_id: int) -> int:
        """Return raw matrix value (3, -3, 4, -4).

        Raises ``KeyError`` when either id is out of range. Previously this
        returned ``0`` silently (which is not a valid encoding), masking bugs
        in the caller (regression #31).
        """
        row = self._eq_to_row.get(hypothesis_id)
        col = self._eq_to_col.get(target_id)
        if row is None or col is None:
            raise KeyError(
                f"Equation id out of range in query_raw: hypothesis_id={hypothesis_id},"
                f" target_id={target_id}; valid range is"
                f" [{min(self._eq_ids)}, {max(self._eq_ids)}]."
            )
        return int(self._matrix[row, col])

    def row_true_count(self, eq_id: int) -> int:
        """How many equations does eq_id imply?

        Raises ``KeyError`` when ``eq_id`` is not in the matrix (consistent
        with ``query_raw``, regression #31). Callers that need a default of
        zero can wrap in ``try/except KeyError``.
        """
        row = self._eq_to_row.get(eq_id)
        if row is None:
            raise KeyError(
                f"row_true_count: equation {eq_id} not in range"
                f" [{min(self._eq_ids)}, {max(self._eq_ids)}]."
            )
        return int(np.count_nonzero((self._matrix[row] == 3) | (self._matrix[row] == 4)))

    def col_true_count(self, eq_id: int) -> int:
        """How many equations imply eq_id?

        Raises ``KeyError`` when ``eq_id`` is not in the matrix (consistent
        with ``query_raw``, regression #31).
        """
        col = self._eq_to_col.get(eq_id)
        if col is None:
            raise KeyError(
                f"col_true_count: equation {eq_id} not in range"
                f" [{min(self._col_eq_ids)}, {max(self._col_eq_ids)}]."
            )
        return int(np.count_nonzero((self._matrix[:, col] == 3) | (self._matrix[:, col] == 4)))

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
                actual = self.decode_truth(int(self._matrix[i, j]))
                if actual is None:
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
    classes: Counter[str] = Counter()
    for eq_id in oracle._col_eq_ids:
        classes[oracle.classify(eq_id)] += 1
    print("\n=== Classification ===")
    for cls, count in classes.most_common():
        print(f"  {cls}: {count}")
