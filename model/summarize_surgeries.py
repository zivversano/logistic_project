#!/usr/bin/env python3
"""
Summarize total surgery price and quantities per unique case number.

Input: a merged file (CSV/Excel) with at least these columns:
- case number (string/int)
- surgen name (string)
- surgeon score (numeric)
- item price (numeric)
- total quantity (numeric)

Output: Excel file with columns:
- case number
- surgen name
- surgeon score
- total price of the surgery
- total quantity of items used in this suregery

Usage:
    python3 model/summarize_surgeries.py --input data/merged.csv --output summary_files/surgery_summary.xlsx

The script auto-detects input type by extension (.csv, .xlsx, .xls).
Column names are matched case-insensitively and with common variations.
"""
import argparse
import sys
from pathlib import Path
try:
    import pandas as pd
except ImportError:
    print("Missing dependency: pandas. Install with 'python3 -m pip install -r requirements.txt'", file=sys.stderr)
    sys.exit(1)

# Common column name variants (lowercased) mapped to canonical names
COLUMN_ALIASES = {
    "case number": "case number",
    "case_number": "case number",
    "case": "case number",
    "case_no": "case number",
    "case id": "case number",
    "case_id": "case number",

    "surgen name": "surgen name",
    "surgeon name": "surgen name",
    "surgen": "surgen name",
    "surgeon": "surgen name",

    "surgeon score": "surgeon score",
    "surgen score": "surgeon score",
    "score": "surgeon score",

    "item price": "item price",
    "price": "item price",
    "unit price": "item price",
    "unit_price": "item price",
    "total price": "item price",
    "price total": "item price",
    "item total price": "item price",
    "items total price": "item price",
    "surgery total price": "item price",
    "total cost": "item price",
    "cost": "item price",

    "total quantity": "total quantity",
    "quantity": "total quantity",
    "qty": "total quantity",
    "total qty": "total quantity",
    "items quantity": "total quantity",
    "total items quantity": "total quantity",
    "total items used": "total quantity",
    "items used": "total quantity",
    "used quantity": "total quantity",
    "item count": "total quantity",
    "count": "total quantity",
}

REQUIRED_CANONICAL = [
    "case number",
    "surgen name",
    "surgeon score",
    "item price",
    "total quantity",
]


def parse_args():
    p = argparse.ArgumentParser(description="Summarize surgeries per case number")
    p.add_argument("--input", default=str(Path("data") / "merged.csv"), help="Path to merged input file (.csv/.xlsx/.xls)")
    p.add_argument("--output", default=str(Path("summary_files") / "surgery_summary.xlsx"), help="Path to output Excel file")
    return p.parse_args()


def read_input(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    elif ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported input extension: {ext}. Use .csv or .xlsx/.xls")


def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Map columns to canonical names using aliases
    new_cols = {}
    for c in df.columns:
        key = str(c).strip().lower()
        canonical = COLUMN_ALIASES.get(key, None)
        if canonical:
            new_cols[c] = canonical
        else:
            new_cols[c] = c  # keep original
    df = df.rename(columns=new_cols)

    # Check required columns
    missing = [col for col in REQUIRED_CANONICAL if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns after normalization: {missing}")

    return df


def clean_and_cast(df: pd.DataFrame) -> pd.DataFrame:
    # Trim strings
    for col in ["case number", "surgen name"]:
        df[col] = df[col].astype(str).str.strip()

    # Cast numerics safely
    for col in ["surgeon score", "item price", "total quantity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    # Aggregate per case number
    grouped = df.groupby("case number", dropna=False).agg({
        "surgen name": lambda s: s.dropna().iloc[0] if len(s.dropna()) > 0 else "",
        "surgeon score": "max",  # if multiple rows per case, keep max score (or could use first)
        "item price": "sum",      # total price of all items in the case
        "total quantity": "sum",  # total quantity across items
    }).reset_index()

    # Rename to match requested output wording
    grouped = grouped.rename(columns={
        "case number": "case number",
        "surgen name": "surgen name",
        "surgeon score": "surgeon score",
        "item price": "total price of the surgery",
        "total quantity": "total quantity of items used in this suregery",
    })

    # Optional: sort by case number
    try:
        grouped = grouped.sort_values(by=["case number"])
    except Exception:
        pass

    return grouped


def write_excel(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="summary")


def main():
    args = parse_args()
    in_path = Path(args.input).resolve()
    out_path = Path(args.output).resolve()

    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    df = read_input(in_path)
    df = canonicalize_columns(df)
    df = clean_and_cast(df)
    summary = summarize(df)
    write_excel(summary, out_path)
    print(f"Wrote summary to {out_path}")


if __name__ == "__main__":
    main()
