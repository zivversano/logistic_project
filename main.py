#!/usr/bin/env python3
"""
Run all data processing steps in order to generate summary Excel outputs.

Steps (in order created):
1) Extract archives from data/ into archive/ (if archives exist) using model/extract_data.py
2) Compute surgery totals per case -> summary_files/case_surgery_totals.xlsx
3) Compute surgeon averages with cost group -> summary_files/surgeon_avg_prices.xlsx
4) Group items per case with cost group -> summary_files/case_items_detail.xlsx
5) Summarize item combinations -> summary_files/item_combinations.xlsx

Usage:
    python main.py

All scripts share the same defaults. If you need custom paths, run the individual scripts.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

SCRIPTS = [
    ROOT / "model" / "extract_data.py",
    ROOT / "model" / "compute_surgery_totals.py",
    ROOT / "model" / "compute_surgeon_averages.py",
    ROOT / "model" / "compute_case_items.py",
    ROOT / "model" / "compute_item_combinations.py",
]


def run_script(script_path: Path) -> None:
    print(f"\n=== Running {script_path.relative_to(ROOT)} ===")
    result = subprocess.run([PYTHON, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    for script in SCRIPTS:
        run_script(script)
    print("\nAll tasks completed.")


if __name__ == "__main__":
    main()
