#!/usr/bin/env python3
"""
Run all data processing steps for every Excel file in data/.

Steps (per file):
1) Compute surgery totals per case
2) Compute surgeon averages with cost group
3) Group items per case with cost group
4) Summarize item combinations
5) Move the processed Excel from data/ to archive/

Pre-step (once per run):
- Extract any archives in data/ into archive/ using model/extract_data.py

Usage:
    python main.py

All scripts share the same defaults. If you need custom paths, run the individual scripts.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = ROOT / "archive"

EXTRACT_SCRIPT = ROOT / "model" / "extract_data.py"


def run_script(script_path: Path) -> None:
    print(f"\n=== Running {script_path.relative_to(ROOT)} ===")
    result = subprocess.run([PYTHON, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def move_input_file(input_file: Path):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    dest = ARCHIVE_DIR / input_file.name
    if dest.exists():
        # Avoid overwrite by adding a numeric suffix
        stem = input_file.stem
        suffix = input_file.suffix
        counter = 1
        while True:
            candidate = ARCHIVE_DIR / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                dest = candidate
                break
            counter += 1

    shutil.move(str(input_file), dest)
    print(f"Moved input file to {dest}")


def find_input_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    files = [p for p in DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".xlsx", ".xls"}]
    return sorted(files)


def build_prefix(input_file: Path) -> str:
    # First word from filename (stem)
    first_word = input_file.stem.split()[0] if input_file.stem else "file"

    # Read first non-null Actual activity code value
    try:
        df = pd.read_excel(input_file, nrows=1)
        df.columns = df.columns.str.strip().str.lower()
        col = None
        for c in df.columns:
            if c == "actual activity code":
                col = c
                break
        code_val = None
        if col and not df.empty:
            code_val = df.iloc[0][col]
        code_part = str(code_val).strip() if code_val is not None else "code"
    except Exception:
        code_part = "code"

    # Sanitize pieces
    def clean(s: str) -> str:
        return s.replace(" ", "_")

    return f"{clean(first_word)}_{clean(str(code_part))}"


def run_pipeline_for_file(input_file: Path) -> None:
    prefix = build_prefix(input_file)
    outputs = {
        "compute_surgery_totals": ROOT / "summary_files" / f"{prefix}_case_surgery_totals.xlsx",
        "compute_surgeon_averages": ROOT / "summary_files" / f"{prefix}_surgeon_avg_prices.xlsx",
        "compute_case_items": ROOT / "summary_files" / f"{prefix}_case_items_detail.xlsx",
        "compute_item_combinations": ROOT / "summary_files" / f"{prefix}_item_combinations.xlsx",
    }

    # Step 1: surgery totals
    result = subprocess.run(
        [PYTHON, str(ROOT / "model" / "compute_surgery_totals.py"), "--input", str(input_file), "--output", str(outputs["compute_surgery_totals"])],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    # Step 2: surgeon averages
    result = subprocess.run(
        [PYTHON, str(ROOT / "model" / "compute_surgeon_averages.py"), "--input", str(input_file), "--output", str(outputs["compute_surgeon_averages"])],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    # Step 3: case items detail
    result = subprocess.run(
        [PYTHON, str(ROOT / "model" / "compute_case_items.py"), "--input", str(input_file), "--output", str(outputs["compute_case_items"])],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    # Step 4: item combinations
    result = subprocess.run(
        [PYTHON, str(ROOT / "model" / "compute_item_combinations.py"), "--input", str(input_file), "--output", str(outputs["compute_item_combinations"])],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    move_input_file(input_file)


def main():
    # Pre-step: extract archives if any
    run_script(EXTRACT_SCRIPT)

    input_files = find_input_files()
    if not input_files:
        print("No Excel files found in data/. Nothing to process.")
        return

    for input_file in input_files:
        print(f"\n--- Processing {input_file.name} ---")
        run_pipeline_for_file(input_file)

    print("\nAll tasks completed.")


if __name__ == "__main__":
    main()
