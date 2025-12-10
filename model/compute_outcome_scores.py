#!/usr/bin/env python3
"""
Compute outcome scores per case with categorical grouping.

Score logic (per unique case):
- Evaluate 14 parameters as booleans:
  1) patient age > 65
  2) ER addmission == 1
  3) revision == 1
  4) moving to other hospital == 1
  5) re-addmission == 1
  6) blood in addmission == 1
  7) antibiotic in addmission == 1
  8) First VAS > 7
  9) surgery length (min) > Q75 of surgery length (min)
 10) recovery length (min) > Q75 of recovery length (min)
 11) calculate length of stay (hours) > Q75 of calculate length of stay (hours)
 12) blood pressure diff % > 25
 13) HR diff % > 25
 14) SPO2 diff % > 10
- Score = (number of positive parameters) / 14 (range 0-1)
- Outcome group:
    good outcome     : positives < 3
    moderate outcome : 3 <= positives <= 6
    bad outcome      : positives > 6

Output columns:
- case number
- positive parameters
- score
- outcome group

Usage:
    python model/compute_outcome_scores.py
    python model/compute_outcome_scores.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/case_outcome_scores.xlsx
"""

import argparse
from pathlib import Path
import sys
import pandas as pd

DEFAULT_INPUT = Path("data/hernia both sides final copilot.xlsx")
DEFAULT_OUTPUT = Path("summary_files/case_outcome_scores.xlsx")

# Column keys normalized to lowercase/stripped
COLS = {
    "case": "case number",
    "age": "patient  age",
    "er": "er addmission",
    "revision": "revision",
    "other_hosp": "moving to other hospital",
    "readm": "re-addmission",
    "blood_adm": "blood in addmission",
    "abx_adm": "antibiotic in addmission",
    "first_vas": "first vas",
    "surg_len": "surgery length(min)",
    "recov_len": "recovery lentgh (min)",
    "stay_hours": "calculate length of stay (hours)",
    "bp_diff": "blood pressure diff %",
    "hr_diff": "hr diff %",
    "spo2_diff": "spo2 diff %",
}

PARAM_KEYS = [
    "age",
    "er",
    "revision",
    "other_hosp",
    "readm",
    "blood_adm",
    "abx_adm",
    "first_vas",
    "surg_len",
    "recov_len",
    "stay_hours",
    "bp_diff",
    "hr_diff",
    "spo2_diff",
]
TOTAL_PARAMS = len(PARAM_KEYS)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()
    return df


def ensure_columns(df: pd.DataFrame):
    missing = [COLS[k] for k in PARAM_KEYS + ["case"] if COLS[k] not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def compute_thresholds(df: pd.DataFrame):
    thresholds = {
        "surg_len": df[COLS["surg_len"]].dropna().quantile(0.75),
        "recov_len": df[COLS["recov_len"]].dropna().quantile(0.75),
        "stay_hours": df[COLS["stay_hours"]].dropna().quantile(0.75),
    }
    return thresholds


def agg_case_level(df: pd.DataFrame) -> pd.DataFrame:
    # Aggregate per case using max for numeric flags/values (worst-case) and first non-null for others
    agg_map = {COLS["case"]: "first"}
    numeric_cols = [COLS[k] for k in PARAM_KEYS if k != "case"]
    for col in numeric_cols:
        agg_map[col] = "max"
    grouped = df.groupby(COLS["case"], as_index=False).agg(agg_map)
    return grouped


def evaluate_flags(row: pd.Series, thresholds: dict) -> dict:
    flags = {
        "age": pd.to_numeric(row[COLS["age"]], errors="coerce") > 65,
        "er": pd.to_numeric(row[COLS["er"]], errors="coerce") == 1,
        "revision": pd.to_numeric(row[COLS["revision"]], errors="coerce") == 1,
        "other_hosp": pd.to_numeric(row[COLS["other_hosp"]], errors="coerce") == 1,
        "readm": pd.to_numeric(row[COLS["readm"]], errors="coerce") == 1,
        "blood_adm": pd.to_numeric(row[COLS["blood_adm"]], errors="coerce") == 1,
        "abx_adm": pd.to_numeric(row[COLS["abx_adm"]], errors="coerce") == 1,
        "first_vas": pd.to_numeric(row[COLS["first_vas"]], errors="coerce") > 7,
        "surg_len": pd.to_numeric(row[COLS["surg_len"]], errors="coerce") > thresholds["surg_len"],
        "recov_len": pd.to_numeric(row[COLS["recov_len"]], errors="coerce") > thresholds["recov_len"],
        "stay_hours": pd.to_numeric(row[COLS["stay_hours"]], errors="coerce") > thresholds["stay_hours"],
        "bp_diff": pd.to_numeric(row[COLS["bp_diff"]], errors="coerce") > 25,
        "hr_diff": pd.to_numeric(row[COLS["hr_diff"]], errors="coerce") > 25,
        "spo2_diff": pd.to_numeric(row[COLS["spo2_diff"]], errors="coerce") > 10,
    }
    return flags


def group_outcome(count: int) -> str:
    if count < 3:
        return "good outcome"
    if 3 <= count <= 6:
        return "moderate outcome"
    return "bad outcome"


def build_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)
    ensure_columns(df)
    thresholds = compute_thresholds(df)
    cases = agg_case_level(df)

    records = []
    for _, row in cases.iterrows():
        flags = evaluate_flags(row, thresholds)
        positives = sum(bool(v) for v in flags.values())
        score = round(positives / TOTAL_PARAMS, 4)
        records.append({
            "case number": row[COLS["case"]],
            "positive parameters": positives,
            "score": score,
            "outcome group": group_outcome(positives),
        })
    return pd.DataFrame(records)


def parse_args():
    parser = argparse.ArgumentParser(description="Compute outcome scores per case")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT, help="Input Excel file path")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT, help="Output Excel file path")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        df = pd.read_excel(args.input)
        scores = build_scores(df)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        scores.to_excel(args.output, index=False)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(scores)} rows to {args.output}")


if __name__ == "__main__":
    main()
