#!/usr/bin/env python3
"""
Generate a case-level report from all new files in the `data/` folder.

For each input file (CSV/Excel), sum item-level prices and quantities per
unique case number and produce a single Excel report named
`summary_files/case_item_report.xlsx`.

Output columns:
- case number
- surgen name
- surgeon score
- total price of the surgery
- total quantity of items used in this suregery

Usage:
    python3 model/generate_case_item_report.py
    python3 model/generate_case_item_report.py --src data --out summary_files/case_item_report.xlsx

Notes:
- Column names are matched case-insensitively with common variations.
- Files considered: *.csv, *.xlsx, *.xls in the source directory.
"""
import argparse
import sys
from pathlib import Path
import re
import unicodedata

try:
    import pandas as pd
except ImportError:
    print("Missing dependency: pandas. Install with 'python3 -m pip install -r requirements.txt'", file=sys.stderr)
    sys.exit(1)

COLUMN_ALIASES = {
    "case number": "case number",
    "case_number": "case number",
    "case": "case number",
    "case no": "case number",
    "case_no": "case number",
    "case id": "case number",
    "case_id": "case number",
    "or items-case number": "case number",

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
    "total item price": "item price",
    "surgery total price": "item price",
    "total cost": "item price",
    "cost": "item price",
    "effective price": "item price",

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
    "qutitem": "total quantity",
}

REQUIRED_CANONICAL = [
    "case number",
    "surgen name",
    "surgeon score",
    "item price",
    "total quantity",
]

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls"}


def parse_args():
    p = argparse.ArgumentParser(description="Generate case-level report from data files")
    p.add_argument("--src", default=str(Path("data")), help="Source directory with input files (.csv/.xlsx/.xls)")
    p.add_argument("--out", default=str(Path("summary_files") / "case_item_report.xlsx"), help="Output Excel path")
    return p.parse_args()


def read_input(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    elif ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported input extension: {ext}")


def _norm_key(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u00A0", " ")  # non-breaking space
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = {}
    for c in df.columns:
        key = _norm_key(c)
        canonical = COLUMN_ALIASES.get(key)
        new_cols[c] = canonical if canonical else c
    # Debug: show column normalization mapping
    try:
        mappings = {str(k): v for k, v in new_cols.items()}
        print(f"Column mappings: {mappings}")
    except Exception:
        pass
    df = df.rename(columns=new_cols)

    missing = [col for col in REQUIRED_CANONICAL if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns after normalization: {missing}")

    # Collapse duplicate canonical columns by taking the first non-null across them
    for col in REQUIRED_CANONICAL:
        same = [c for c in df.columns if c == col]
        if len(same) > 1:
            combined = df[same].bfill(axis=1).iloc[:, 0]
            df[col] = combined
            # Drop extra duplicates, keep only the canonical one
            extras = same[1:]
            df = df.drop(columns=extras)
    return df


def clean_and_cast(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["case number", "surgen name"]:
        df[col] = df[col].astype(str).str.strip()
    for col in ["surgeon score", "item price", "total quantity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("case number", dropna=False).agg({
        "surgen name": lambda s: s.dropna().iloc[0] if len(s.dropna()) > 0 else "",
        "surgeon score": "max",
        "item price": "sum",
        "total quantity": "sum",
    }).reset_index()

    grouped = grouped.rename(columns={
        "item price": "total price of the surgery",
        "total quantity": "total quantity of items used in this suregery",
    })
    return grouped


def gather_files(src_dir: Path):
    for p in src_dir.iterdir():
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            yield p


def main():
    args = parse_args()
    src_dir = Path(args.src).resolve()
    out_path = Path(args.out).resolve()

    if not src_dir.exists() or not src_dir.is_dir():
        print(f"Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    files = list(gather_files(src_dir))
    if not files:
        print(f"No input files found in {src_dir}")
        sys.exit(0)

    summaries = []
    for f in files:
        try:
            raw_df = read_input(f)
            # Proactively add 'case number' if identifiable from raw columns
            try:
                case_cols = [c for c in raw_df.columns if _norm_key(c) in {"case number", "or items-case number"}]
                if case_cols and "case number" not in raw_df.columns:
                    raw_df["case number"] = raw_df[case_cols].bfill(axis=1).iloc[:, 0]
            except Exception:
                pass

            df = canonicalize_columns(raw_df)
            df = clean_and_cast(df)
            try:
                s = summarize(df)
            except Exception as e:
                print(f"Summarize error for {f.name}: {e}. Columns after canonicalization: {list(df.columns)}", file=sys.stderr)
                raise
            summaries.append(s)
            print(f"Processed: {f.name}")
        except KeyError as e:
            cols = [str(c) for c in getattr(raw_df, 'columns', [])]
            print(f"Skipping {f.name}: {e}. Found columns: {cols}", file=sys.stderr)
        except Exception as e:
            print(f"Skipping {f.name}: {e}", file=sys.stderr)

    if not summaries:
        print("No valid input files processed.", file=sys.stderr)
        sys.exit(1)

    report = pd.concat(summaries, axis=0, ignore_index=True)
    # Optional: deduplicate case numbers by aggregating again across files
    report = report.groupby("case number", dropna=False).agg({
        "surgen name": lambda s: s.dropna().iloc[0] if len(s.dropna()) > 0 else "",
        "surgeon score": "max",
        "total price of the surgery": "sum",
        "total quantity of items used in this suregery": "sum",
    }).reset_index()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        report.to_excel(writer, index=False, sheet_name="case_item_report")

    print(f"Wrote report to {out_path}")


if __name__ == "__main__":
    main()
