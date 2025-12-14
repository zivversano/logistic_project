#!/usr/bin/env python3
"""
Run all data processing steps for every Excel file in data/.

Steps (per file):
1) Compute surgery totals per case
2) Compute surgeon averages with cost group
3) Group items per case with cost group
4) Summarize item combinations
5) Compute outcome scores per case
6) Move the processed Excel from data/ to archive/

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
import re

import pandas as pd

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = ROOT / "archive"

EXTRACT_SCRIPT = ROOT / "model" / "extract_data.py"
DOCKER_COMPOSE = ["docker", "compose"]


def run_script(script_path: Path) -> None:
    print(f"\n=== Running {script_path.relative_to(ROOT)} ===")
    result = subprocess.run([PYTHON, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_postgres():
    """Start Postgres via docker compose in detached mode."""
    print("\n=== Ensuring Postgres is up (docker compose up -d db) ===")
    result = subprocess.run(DOCKER_COMPOSE + ["up", "-d", "db"], cwd=ROOT)
    if result.returncode != 0:
        print("docker compose up -d db failed; continuing without container", file=sys.stderr)


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
    """Build output prefix from file content (not filename).

    Uses first non-null values of:
    - actual activity
    - actual activity code
    """

    def slugify(value: str, keep: str = "") -> str:
        value = str(value or "").strip().lower()
        if not value:
            return ""
        # Replace separators/spaces with underscores and drop other punctuation
        pattern = rf"[^0-9a-zA-Z{re.escape(keep)}]+"
        value = re.sub(pattern, "_", value)
        value = re.sub(r"_+", "_", value).strip("_")
        return value

    activity_part = ""
    code_part = ""

    try:
        df = pd.read_excel(input_file, nrows=200)
        df.columns = df.columns.str.strip().str.lower()

        if "actual activity" in df.columns:
            s = df["actual activity"].dropna()
            if not s.empty:
                activity_part = slugify(s.iloc[0])
        if "actual activity code" in df.columns:
            s = df["actual activity code"].dropna()
            if not s.empty:
                # keep dot in codes like 54.01
                code_part = slugify(s.iloc[0], keep=".")
    except Exception:
        # Fall back to placeholders
        pass

    if not activity_part:
        activity_part = "activity"
    if not code_part:
        code_part = "code"

    return f"{activity_part}_{code_part}"


def run_pipeline_for_file(input_file: Path) -> None:
    prefix = build_prefix(input_file)
    outputs = {
        "compute_surgery_totals": ROOT / "summary_files" / f"{prefix}_case-surgery-totals.xlsx",
        "compute_surgeon_averages": ROOT / "summary_files" / f"{prefix}_surgeon-avg-prices.xlsx",
        "compute_case_items": ROOT / "summary_files" / f"{prefix}_case-items-detail.xlsx",
        "compute_item_combinations": ROOT / "summary_files" / f"{prefix}_item-combinations.xlsx",
        "compute_outcome_scores": ROOT / "summary_files" / f"{prefix}_case-outcome-scores.xlsx",
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

    # Step 5: outcome scores
    result = subprocess.run(
        [PYTHON, str(ROOT / "model" / "compute_outcome_scores.py"), "--input", str(input_file), "--output", str(outputs["compute_outcome_scores"])],
        cwd=ROOT,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    move_input_file(input_file)


def main():
    ensure_postgres()

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
