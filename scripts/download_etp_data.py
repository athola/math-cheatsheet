#!/usr/bin/env python3
"""Download ETP (Equational Theories Project) data for local analysis.

Downloads:
- equations.txt: The 4694 equational laws
- implications.csv: The 4694x4694 implication matrix (derived from graph.json)

Source: https://github.com/teorth/equational_theories
"""

import json
import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
ETP_DIR = Path(__file__).parent.parent / "research" / "data" / "etp"

URLS = {
    "equations.txt": (
        "https://raw.githubusercontent.com/teorth/equational_theories/main/data/equations.txt"
    ),
}

GRAPH_JSON_URL = (
    "https://teorth.github.io/equational_theories/implications/graph.json"
)

# Maps the internal index values from graph.json to the CSV numeric format.
# This matches the text_to_number array in the ETP website's script.js.
_RLE_VALUE_TO_CSV = [-2, 2, -4, 4, -1, 1, -3, 3, 0]
_MATRIX_DIM = 4694


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
            equations.append(
                {
                    "id": i,
                    "raw": line,
                }
            )
    return equations


def download_implications_csv(dest: Path) -> bool:
    """Download graph.json from the ETP site and expand it to implications.csv.

    The ETP site serves the 4694x4694 implication matrix as an RLE-compressed
    JSON blob (~9MB).  We decode it and write the same CSV format that the
    website's "Download raw implications table" button produces (~56MB).
    """
    print(f"Downloading graph.json from {GRAPH_JSON_URL}...")
    try:
        with urllib.request.urlopen(GRAPH_JSON_URL) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  -> FAILED to fetch graph.json: {e}")
        return False

    rle = data["rle_encoded_array"]

    # Decode RLE: pairs of (value, count)
    decoded = []
    for i in range(0, len(rle), 2):
        decoded.extend([rle[i]] * rle[i + 1])

    expected = _MATRIX_DIM * _MATRIX_DIM
    if len(decoded) != expected:
        print(f"  -> FAILED: decoded {len(decoded)} values, expected {expected}")
        return False

    print(f"  -> Decoded {len(decoded):,} values, writing CSV...")
    with open(dest, "w", encoding="utf-8") as f:
        for row_idx in range(_MATRIX_DIM):
            start = row_idx * _MATRIX_DIM
            row = decoded[start : start + _MATRIX_DIM]
            f.write(",".join(str(_RLE_VALUE_TO_CSV[v]) for v in row))
            f.write("\n")

    size = dest.stat().st_size
    print(f"  -> {size:,} bytes saved to {dest}")
    return True


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ETP_DIR.mkdir(parents=True, exist_ok=True)

    success = True
    for name, url in URLS.items():
        dest = DATA_DIR / name
        if dest.exists():
            print(f"Skipping {name} (already exists, {dest.stat().st_size:,} bytes)")
            continue
        if not download_file(url, dest):
            success = False

    # Download implications matrix
    csv_dest = ETP_DIR / "implications.csv"
    if csv_dest.exists():
        print(
            f"Skipping implications.csv "
            f"(already exists, {csv_dest.stat().st_size:,} bytes)"
        )
    elif not download_implications_csv(csv_dest):
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
