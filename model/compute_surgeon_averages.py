#!/usr/bin/env python3
"""
Compute per-surgeon average surgery price based on unique case totals.

Process:
1) Read the hernia Excel (default: data/hernia both sides final copilot.xlsx).
2) Normalize columns (strip/lower) and ensure required fields exist.
3) First aggregate by case number to get one row per case (summing total price and quantity).
4) Then aggregate by surgeon name to compute average price per surgery and count unique cases.
5) Keep first non-null surgeon score and hospital per surgeon.
6) Label surgeons as "cheap" or "expensive" based on a threshold (default: median of average price).
7) Write the result to Excel (default: summary_files/surgeon_avg_prices.xlsx).

Usage:
    python model/compute_surgeon_averages.py
    python model/compute_surgeon_averages.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/surgeon_avg_prices.xlsx
"""

import argparse
from pathlib import Path
import sys
import pandas as pd

DEFAULT_INPUT = Path("data/hernia both sides final copilot.xlsx")
DEFAULT_OUTPUT = Path("summary_files/surgeon_avg_prices.xlsx")
REQUIRED_COLUMNS = {
    "case number",
    "surgeon name",
    "surgeon score",
    "total price",
    "hospital",
    "quantity",
    "all_ procedures",
    "all_ procedures code",
}

OPTIONAL_ACTIVITY_COLUMNS = ["actual activity", "actual activity code"]


def first_non_null(series):
    for value in series:
        if pd.notna(value):
            return value
    return None


def load_data(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    df = pd.read_excel(input_path)
    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    # Ensure optional columns exist so outputs are consistent.
    for col in OPTIONAL_ACTIVITY_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def aggregate_per_case(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["total price"] = pd.to_numeric(df["total price"], errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)

    per_case = (
        df.groupby("case number")
        .agg({
            "surgeon name": first_non_null,
            "surgeon score": first_non_null,
            "hospital": first_non_null,
            "all_ procedures": first_non_null,
            "all_ procedures code": first_non_null,
            "actual activity": first_non_null,
            "actual activity code": first_non_null,
            "total price": "sum",
            "quantity": "sum",
        })
        .reset_index()
    )
    return per_case


def aggregate_per_surgeon(per_case: pd.DataFrame) -> pd.DataFrame:
    per_surgeon = (
        per_case.groupby("surgeon name")
        .agg({
            "total price": "mean",  # avg price per surgery (cases already aggregated)
            "case number": pd.Series.nunique,  # number of unique cases
            "surgeon score": first_non_null,
            "hospital": first_non_null,
            "all_ procedures": lambda s: ", ".join(sorted({str(v) for v in s if pd.notna(v)})),
            "all_ procedures code": lambda s: ", ".join(sorted({str(v) for v in s if pd.notna(v)})),
            "actual activity": lambda s: ", ".join(sorted({str(v) for v in s if pd.notna(v)})),
            "actual activity code": lambda s: ", ".join(sorted({str(v) for v in s if pd.notna(v)})),
        })
        .reset_index()
    )

    per_surgeon = per_surgeon.rename(columns={
        "total price": "avg price for surgery",
        "case number": "number of surgeries",
        "all_ procedures": "all procedures",
        "all_ procedures code": "all procedures code",
    })

    per_surgeon = per_surgeon[[
        "surgeon name",
        "avg price for surgery",
        "number of surgeries",
        "surgeon score",
        "hospital",
        "all procedures",
        "all procedures code",
        "actual activity",
        "actual activity code",
    ]]
    return per_surgeon


def label_cost_group(per_surgeon: pd.DataFrame, threshold: float | None) -> pd.DataFrame:
    """Add cost group column based on avg price threshold.

    If threshold is None, use the median of avg price for surgery. Values <= threshold are
    labeled "cheap", otherwise "expensive". If the dataset is empty, threshold defaults to 0.
    """
    if per_surgeon.empty:
        per_surgeon["cost group"] = []
        return per_surgeon

    if threshold is None:
        threshold = per_surgeon["avg price for surgery"].median()

    per_surgeon = per_surgeon.copy()
    per_surgeon["cost group"] = per_surgeon["avg price for surgery"].apply(
        lambda v: "cheap" if v <= threshold else "expensive"
    )
    per_surgeon.attrs["threshold_used"] = threshold
    return per_surgeon


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Compute per-surgeon average surgery price and counts")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT, help="Input Excel file path")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT, help="Output Excel file path")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Avg price threshold to label cheap vs expensive (default: median of avg price)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        df = load_data(args.input)
        per_case = aggregate_per_case(df)
        per_surgeon = aggregate_per_surgeon(per_case)
        per_surgeon = label_cost_group(per_surgeon, args.threshold)
        write_output(per_surgeon, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    threshold_used = per_surgeon.attrs.get("threshold_used", args.threshold)
    print(f"Wrote {len(per_surgeon)} rows to {args.output} (threshold={threshold_used})")


if __name__ == "__main__":
    main()
