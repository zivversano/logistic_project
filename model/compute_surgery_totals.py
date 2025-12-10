#!/usr/bin/env python3
"""
Aggregate surgery totals per case from the hernia dataset.

- Reads the Excel file (defaults to `data/hernia both sides final copilot.xlsx`).
- Groups by case number and sums total price and quantity.
- Picks the first non-null surgeon name and surgeon score per case.
- Writes results to Excel (defaults to `summary_files/case_surgery_totals.xlsx`).

Usage:
    python model/compute_surgery_totals.py
    python model/compute_surgery_totals.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/case_surgery_totals.xlsx
"""

import argparse
from pathlib import Path
import sys
import pandas as pd


DEFAULT_INPUT = Path("data/hernia both sides final copilot.xlsx")
DEFAULT_OUTPUT = Path("summary_files/case_surgery_totals.xlsx")
REQUIRED_COLUMNS = {
    "case number",
    "surgeon name",
    "surgeon score",
    "total price",
    "quantity",
    "all_ procedures",
    "all_ procedures code",
}


def first_non_null(series):
    for value in series:
        if pd.notna(value):
            return value
    return None


def load_data(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    df = pd.read_excel(input_path)
    # Normalize column names: strip spaces and lowercase for matching.
    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    return df


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["total price"] = pd.to_numeric(df["total price"], errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)

    grouped = (
        df.groupby("case number")
        .agg({
            "surgeon name": first_non_null,
            "surgeon score": first_non_null,
            "all_ procedures": first_non_null,
            "all_ procedures code": first_non_null,
            "total price": "sum",
            "quantity": "sum",
        })
        .reset_index()
    )

    grouped = grouped.rename(columns={
        "case number": "case number",
        "surgeon name": "surgeon name",
        "surgeon score": "surgeon score",
        "all_ procedures": "all procedures",
        "all_ procedures code": "all procedures code",
        "quantity": "total quantity",
        "total price": "total price",
    })

    # Reorder columns
    grouped = grouped[[
        "case number",
        "surgeon name",
        "surgeon score",
        "all procedures",
        "all procedures code",
        "total quantity",
        "total price",
    ]]
    return grouped


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)



def parse_args():
    parser = argparse.ArgumentParser(description="Calculate total surgery price and item counts per case")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT, help="Input Excel file path")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT, help="Output Excel file path")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        df = load_data(args.input)
        result = aggregate(df)
        write_output(result, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(result)} rows to {args.output}")


if __name__ == "__main__":
    main()
