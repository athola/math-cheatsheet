#!/usr/bin/env python3
"""Download ETP (Equational Theories Project) data for local analysis.

Downloads:
- equations.txt: The 4694 equational laws
- The implication graph data (if available)

Source: https://github.com/teorth/equational_theories
"""

import json
import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

URLS = {
    "equations.txt": (
        "https://raw.githubusercontent.com/teorth/equational_theories"
        "/main/data/equations.txt"
    ),
}


def download_file(url: str, dest: Path) -> bool:
    """Download a file from url to dest. Returns True on success."""
    print(f"Downloading {dest.name} from {url}...")
    try:
        urllib.request.urlretrieve(url, dest)
        size = dest.stat().st_size
        print(f"  -> {size:,} bytes saved to {dest}")
        return True
    except Exception as e:
        print(f"  -> FAILED: {e}")
        return False


def parse_equations_file(path: Path) -> list[dict]:
    """Parse the ETP equations.txt format into structured data."""
    equations = []
    with open(path) as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            equations.append({
                "id": i,
                "raw": line,
            })
    return equations


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    success = True
    for name, url in URLS.items():
        dest = DATA_DIR / name
        if dest.exists():
            print(f"Skipping {name} (already exists, {dest.stat().st_size:,} bytes)")
            continue
        if not download_file(url, dest):
            success = False

    # Parse and create a summary
    eq_file = DATA_DIR / "equations.txt"
    if eq_file.exists():
        equations = parse_equations_file(eq_file)
        print(f"\nParsed {len(equations)} equations from equations.txt")

        summary = {
            "total_equations": len(equations),
            "first_5": equations[:5],
            "last_5": equations[-5:],
        }
        summary_path = DATA_DIR / "equations_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary saved to {summary_path}")

    if success:
        print("\nAll downloads complete.")
    else:
        print("\nSome downloads failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
