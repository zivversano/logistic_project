#!/usr/bin/env python3
"""
Compute outcome scores per case with categorical grouping.

Score logic (per unique case):
- Evaluate 13 parameters as booleans, each with a weight when true:
    ER addmission = 0.08
    revision = 0.08
    moving to other hospital = 0.08
    re-admission = 0.08
    blood in addmission = 0.06
    antibiotic in addmission = 0.06
    First VAS > 7 = 0.04
    surgery length (min) > Q75 of surgery length (min) = 0.16
    recovery length (min) > Q75 of recovery length (min) = 0.04
    calculate length of stay (hours) > Q75 of calculate length of stay (hours) = 0.12
    blood pressure diff % > 25 = 0.04
    HR diff % > 25 = 0.04
    SPO2 diff % > 10 = 0.04
- Score = (sum of weights for true parameters) / total weight (range 0-1)
- Outcome group (based on score):
    good outcome     : score < 3/13
    moderate outcome : 3/13 <= score <= 6/13
    bad outcome      : score > 6/13

Output columns:
- case number
- positive parameters
- score
- normalized score (0-100; lower raw score -> higher normalized)
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

WEIGHTS = {
    "er": 0.08,
    "revision": 0.08,
    "other_hosp": 0.08,
    "readm": 0.08,
    "blood_adm": 0.06,
    "abx_adm": 0.06,
    "first_vas": 0.04,
    "surg_len": 0.16,
    "recov_len": 0.04,
    "stay_hours": 0.12,
    "bp_diff": 0.04,
    "hr_diff": 0.04,
    "spo2_diff": 0.04,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())
GOOD_THRESHOLD = 3 / 13
MODERATE_THRESHOLD = 6 / 13
OPTIONAL_ACTIVITY_COLUMNS = ["actual activity", "actual activity code"]


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


def attach_activity_columns(case_df: pd.DataFrame, source_df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in OPTIONAL_ACTIVITY_COLUMNS if c in source_df.columns]
    if not cols:
        return case_df

    mapping = (
        source_df[[COLS["case"]] + cols]
        .groupby(COLS["case"], as_index=False)
        .agg({c: lambda s: s.dropna().iloc[0] if not s.dropna().empty else None for c in cols})
    )
    return case_df.merge(mapping, on=COLS["case"], how="left")


def evaluate_flags(row: pd.Series, thresholds: dict) -> dict:
    flags = {
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


def group_outcome(score: float) -> str:
    if score < GOOD_THRESHOLD:
        return "good outcome"
    if GOOD_THRESHOLD <= score <= MODERATE_THRESHOLD:
        return "moderate outcome"
    return "bad outcome"


def build_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)
    # Ensure optional activity columns exist so outputs are consistent.
    for col in OPTIONAL_ACTIVITY_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    ensure_columns(df)
    thresholds = compute_thresholds(df)
    cases = agg_case_level(df)
    cases = attach_activity_columns(cases, df)

    records = []
    for _, row in cases.iterrows():
        flags = evaluate_flags(row, thresholds)
        positives = sum(bool(v) for v in flags.values())
        weighted_sum = sum(WEIGHTS[k] for k, v in flags.items() if v)
        score = round(weighted_sum / TOTAL_WEIGHT, 4)
        normalized_score = round((1 - score) * 100, 2)
        records.append({
            "case number": row[COLS["case"]],
            "actual activity": row.get("actual activity", None),
            "actual activity code": row.get("actual activity code", None),
            "positive parameters": positives,
            "score": score,
            "normalized score (0-100)": normalized_score,
            "outcome group": group_outcome(score),
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
