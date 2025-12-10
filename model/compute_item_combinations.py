#!/usr/bin/env python3
"""
Summarize item combinations across cases and surgeons.

For each unique combination of items (as they appear in a case), compute:
- frequency (number of cases with this combination)
- surgeons that used it ("Name (Score)"; unique, comma-separated)
- surgeon price groups involved (cheap/expensive)
- average total surgery price for the combination

Item formatting matches `compute_case_items.py`: "item name (qty)" joined by commas per case.

Usage:
    python model/compute_item_combinations.py
    python model/compute_item_combinations.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/item_combinations.xlsx
    python model/compute_item_combinations.py --threshold 3000
"""

import argparse
from pathlib import Path
import sys
import pandas as pd

from compute_outcome_scores import build_scores

DEFAULT_INPUT = Path("data/hernia both sides final copilot.xlsx")
DEFAULT_OUTPUT = Path("summary_files/item_combinations.xlsx")
REQUIRED_COLUMNS = {
    "case number",
    "surgeon name",
    "surgeon score",
    "item name",
    "quantity",
    "total price",
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
        # Sort for canonical combination key so ordering differences don't create separate combos
        parts_sorted = sorted(parts)
        return ", ".join(parts_sorted)

    grouped = []
    for case_number, g in df.groupby("case number"):
        record = {
            "case number": case_number,
            "surgeon name": first_non_null(g["surgeon name"]),
            "surgeon score": first_non_null(g["surgeon score"]),
            "all_ procedures": first_non_null(g["all_ procedures"]),
            "all_ procedures code": first_non_null(g["all_ procedures code"]),
            "total price": g["total price"].sum(),
            "items": concat_items(g),
        }
        grouped.append(record)

    return pd.DataFrame(grouped)


def attach_outcomes(case_df: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    if outcomes is None or outcomes.empty:
        case_df["outcome group"] = None
        return case_df
    return case_df.merge(outcomes[["case number", "outcome group"]], on="case number", how="left")


def compute_surgeon_groups(case_df: pd.DataFrame, threshold: float | None) -> tuple[pd.DataFrame, float]:
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
    return case_df.merge(
        per_surgeon[["surgeon name", "surgeon price group"]],
        on="surgeon name",
        how="left",
    )


def aggregate_combinations(case_df: pd.DataFrame) -> pd.DataFrame:
    def surgeons_list(series):
        seen = []
        for name, score in series:
            label = f"{name} ({score})"
            if label not in seen:
                seen.append(label)
        return ", ".join(seen)

    def groups_list(series):
        seen = []
        for val in series:
            if pd.notna(val) and val not in seen:
                seen.append(val)
        return ", ".join(seen)

    def outcomes_list(series):
        seen = []
        for val in series:
            if pd.notna(val) and val not in seen:
                seen.append(val)
        return ", ".join(seen)

    combo_df = (
        case_df.groupby("items")
        .agg({
            "case number": pd.Series.nunique,
            "surgeon name": lambda s: surgeons_list(zip(s, case_df.loc[s.index, "surgeon score"])),
            "surgeon price group": groups_list,
            "total price": "mean",
            "all_ procedures": lambda s: ", ".join(sorted({str(v) for v in case_df.loc[s.index, "all_ procedures"] if pd.notna(v)})),
            "all_ procedures code": lambda s: ", ".join(sorted({str(v) for v in case_df.loc[s.index, "all_ procedures code"] if pd.notna(v)})),
            "outcome group": outcomes_list,
        })
        .reset_index()
    )

    combo_df = combo_df.rename(columns={
        "items": "combination",
        "case number": "frequency",
        "surgeon name": "surgeons (score)",
        "surgeon price group": "surgeon price group",
        "total price": "avg total price",
        "all_ procedures": "all procedures",
        "all_ procedures code": "all procedures code",
        "outcome group": "outcome group",
    })

    # Reorder columns
    combo_df = combo_df[[
        "combination",
        "frequency",
        "surgeons (score)",
        "surgeon price group",
        "avg total price",
        "all procedures",
        "all procedures code",
        "outcome group",
    ]]

    return combo_df


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)


def parse_args():
    parser = argparse.ArgumentParser(description="Summarize item combinations across cases")
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
        outcomes = build_scores(df)
        case_df = attach_outcomes(case_df, outcomes)
        per_surgeon, threshold_used = compute_surgeon_groups(case_df, args.threshold)
        case_df = attach_price_group(case_df, per_surgeon)
        combo_df = aggregate_combinations(case_df)
        write_output(combo_df, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(combo_df)} rows to {args.output} (threshold={threshold_used})")


if __name__ == "__main__":
    main()
