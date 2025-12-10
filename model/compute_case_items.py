#!/usr/bin/env python3
"""
Group data by case number, list items with quantities, count total items, and attach surgeon info.

Output columns:
- case number
- surgeon name
- surgeon score
- surgeon price group (cheap/expensive, threshold is median of per-surgeon average price unless overridden)
- items (comma-separated 'item name x qty')
- total item quantity
- total price (sum of total price in the case)

Usage:
    python model/compute_case_items.py
    python model/compute_case_items.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/case_items_detail.xlsx
    python model/compute_case_items.py --threshold 3000
"""

import argparse
from pathlib import Path
import sys
import pandas as pd

DEFAULT_INPUT = Path("data/hernia both sides final copilot.xlsx")
DEFAULT_OUTPUT = Path("summary_files/case_items_detail.xlsx")
REQUIRED_COLUMNS = {
    "case number",
    "surgeon name",
    "surgeon score",
    "item name",
    "quantity",
    "total price",
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
    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    return df


def build_case_level(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["total price"] = pd.to_numeric(df["total price"], errors="coerce").fillna(0)

    def concat_items(group: pd.DataFrame) -> str:
        parts = []
        for _, row in group.iterrows():
            name = str(row.get("item name", "")).strip()
            qty = row.get("quantity", 0)
            qty_fmt = int(qty) if float(qty).is_integer() else qty
            parts.append(f"{name} ({qty_fmt})")
        return ", ".join(parts)

    grouped = []
    for case_number, g in df.groupby("case number"):
        record = {
            "case number": case_number,
            "surgeon name": first_non_null(g["surgeon name"]),
            "surgeon score": first_non_null(g["surgeon score"]),
            "total price": g["total price"].sum(),
            "total item quantity": g["quantity"].sum(),
            "items": concat_items(g),
        }
        grouped.append(record)

    case_df = pd.DataFrame(grouped)
    return case_df


def compute_surgeon_groups(case_df: pd.DataFrame, threshold: float | None) -> tuple[pd.DataFrame, float]:
    """Compute per-surgeon average price and label cheap/expensive."""
    per_surgeon = (
        case_df.groupby("surgeon name")
        .agg({
            "total price": "mean",
            "case number": pd.Series.nunique,
            "surgeon score": first_non_null,
        })
        .reset_index()
    )
    per_surgeon = per_surgeon.rename(columns={"total price": "avg price for surgery"})

    if threshold is None:
        threshold = per_surgeon["avg price for surgery"].median() if not per_surgeon.empty else 0

    per_surgeon["surgeon price group"] = per_surgeon["avg price for surgery"].apply(
        lambda v: "cheap" if v <= threshold else "expensive"
    )
    return per_surgeon, threshold


def attach_price_group(case_df: pd.DataFrame, per_surgeon: pd.DataFrame) -> pd.DataFrame:
    enriched = case_df.merge(
        per_surgeon[["surgeon name", "surgeon price group"]],
        on="surgeon name",
        how="left",
    )
    return enriched


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Group items per case with surgeon info and cost grouping")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT, help="Input Excel file path")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT, help="Output Excel file path")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Threshold for surgeon price group (median of avg surgery price if omitted)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        df = load_data(args.input)
        case_df = build_case_level(df)
        per_surgeon, threshold_used = compute_surgeon_groups(case_df, args.threshold)
        enriched = attach_price_group(case_df, per_surgeon)
        write_output(enriched, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(enriched)} rows to {args.output} (threshold={threshold_used})")


if __name__ == "__main__":
    main()
