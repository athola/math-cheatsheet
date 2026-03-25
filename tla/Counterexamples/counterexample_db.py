#!/usr/bin/env python3
"""
Counterexample Database for Magma Implications

Stores and analyzes counterexamples found by TLA+ exploration.
Provides queries for cheatsheet generation.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

# Requires PYTHONPATH=src:tla/python (set by Makefile)
from data_models import Counterexample, Magma


class CounterexampleDatabase:
    """Database of counterexamples for magma implications.

    Uses a dict index on (premise_id, conclusion_id) for O(1) lookup
    instead of linear scan.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "counterexamples.json"

        self.db_path = db_path
        self.counterexamples: List[Counterexample] = []
        self._index: Dict[tuple, List[int]] = {}  # (premise_id, conclusion_id) -> [indices]

        if db_path.exists():
            self.load()

    def _rebuild_index(self) -> None:
        self._index.clear()
        for i, c in enumerate(self.counterexamples):
            key = (c.premise_id, c.conclusion_id)
            self._index.setdefault(key, []).append(i)

    def add(self, counterexample: Counterexample) -> None:
        idx = len(self.counterexamples)
        self.counterexamples.append(counterexample)
        key = (counterexample.premise_id, counterexample.conclusion_id)
        self._index.setdefault(key, []).append(idx)

    def load(self) -> None:
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            for item in data:
                magma_data = item["magma"]
                op_dict = {
                    (t["a"], t["b"]): t["result"]
                    for t in magma_data["operation"]
                }
                magma = Magma.from_dict_operation(
                    carrier=magma_data["carrier"],
                    op_dict=op_dict
                )
                self.counterexamples.append(Counterexample(
                    premise_id=item.get("premise_id", -1),
                    conclusion_id=item.get("conclusion_id", -1),
                    magma=magma,
                    red_flags=set(item.get("red_flags", []))
                ))
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"Warning: Could not load database: {e}")

        self._rebuild_index()

    def save(self) -> None:
        data = [c.to_dict() for c in self.counterexamples]
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_counterexamples(
        self, premise_id: int, conclusion_id: int
    ) -> List[Counterexample]:
        indices = self._index.get((premise_id, conclusion_id), [])
        return [self.counterexamples[i] for i in indices]

    def get_counterexamples_by_name(
        self, equation_e1: str, equation_e2: str
    ) -> List[Counterexample]:
        """Legacy name-based lookup for backward compatibility."""
        return [
            c for c in self.counterexamples
            if str(c.premise_id) == equation_e1 or str(c.conclusion_id) == equation_e2
        ]

    def get_red_flags(
        self, premise_id: int, conclusion_id: int, threshold: float = 0.5
    ) -> Set[str]:
        counterexamples = self.get_counterexamples(premise_id, conclusion_id)

        if not counterexamples:
            return set()

        flag_counts: Dict[str, int] = {}
        for c in counterexamples:
            for flag in c.red_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        total = len(counterexamples)
        return {
            flag for flag, count in flag_counts.items()
            if count / total > threshold
        }

    def get_implication_status(
        self, premise_id: int, conclusion_id: int
    ) -> str:
        count = len(self.get_counterexamples(premise_id, conclusion_id))

        if count == 0:
            return "always_true"
        elif count > 100:
            return "very_likely_false"
        elif count > 10:
            return "likely_false"
        else:
            return "sometimes_false"

    def generate_cheatsheet_entry(
        self, premise_id: int, conclusion_id: int
    ) -> dict:
        status = self.get_implication_status(premise_id, conclusion_id)
        red_flags = self.get_red_flags(premise_id, conclusion_id)
        count = len(self.get_counterexamples(premise_id, conclusion_id))

        return {
            "implication": f"E{premise_id} => E{conclusion_id}",
            "status": status,
            "counterexample_count": count,
            "red_flags": list(red_flags),
            "recommendation": self._get_recommendation(status, red_flags)
        }

    def _get_recommendation(self, status: str, red_flags: Set[str]) -> str:
        if status == "always_true":
            return "This implication appears to hold. Consider including in cheatsheet."
        elif status == "very_likely_false":
            return f"Very unlikely to be true. Red flags: {', '.join(red_flags)}"
        elif status == "likely_false":
            return f"Unlikely to be true. Check for: {', '.join(red_flags)}"
        else:
            return "Needs further verification. Check small magmas first."

    def get_statistics(self) -> dict:
        total = len(self.counterexamples)
        implications = set(
            (c.premise_id, c.conclusion_id)
            for c in self.counterexamples
        )
        flag_counts: Dict[str, int] = {}
        for c in self.counterexamples:
            for flag in c.red_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

        return {
            "total_counterexamples": total,
            "unique_implications": len(implications),
            "red_flag_frequencies": flag_counts
        }


def main():
    db = CounterexampleDatabase()

    if len(sys.argv) < 2:
        print("Usage: python counterexample_db.py <command>")
        print("Commands: stats, search <premise_id> <conclusion_id>, report <premise_id> <conclusion_id>")
        return

    command = sys.argv[1]

    if command == "stats":
        stats = db.get_statistics()
        print(json.dumps(stats, indent=2))

    elif command == "search" and len(sys.argv) >= 4:
        p_id, c_id = int(sys.argv[2]), int(sys.argv[3])
        examples = db.get_counterexamples(p_id, c_id)
        print(f"Found {len(examples)} counterexamples for E{p_id} => E{c_id}")

    elif command == "report" and len(sys.argv) >= 4:
        p_id, c_id = int(sys.argv[2]), int(sys.argv[3])
        entry = db.generate_cheatsheet_entry(p_id, c_id)
        print(json.dumps(entry, indent=2))

    else:
        print("Unknown command or missing arguments")


if __name__ == "__main__":
    main()
