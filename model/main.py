#!/usr/bin/env python3
"""
Main entrypoint for data pipeline:
- extract: Extract archives from `data/` into `archive/`
- report: Generate case-level item report from files in `data/`
- all: Run extract then report

Usage:
    python3 model/main.py extract --src data --dest archive
    python3 model/main.py report --src data --out summary_files/case_item_report.xlsx
    python3 model/main.py all --src data --dest archive --out summary_files/case_item_report.xlsx
"""
import argparse
import sys
from pathlib import Path

# Ensure local imports work when run from repo root or other cwd
THIS_DIR = Path(__file__).parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

# Import script modules
import extract_data
import generate_case_item_report


def parse_args():
    p = argparse.ArgumentParser(description="Logistic Project Pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    # extract subcommand
    p_extract = sub.add_parser("extract", help="Extract archives from source to destination")
    p_extract.add_argument("--src", default=str(Path("data")), help="Source directory containing archives")
    p_extract.add_argument("--dest", default=str(Path("archive")), help="Destination directory for extracted contents")

    # report subcommand
    p_report = sub.add_parser("report", help="Generate case item report from data files")
    p_report.add_argument("--src", default=str(Path("data")), help="Source directory with input files")
    p_report.add_argument("--out", default=str(Path("summary_files") / "case_item_report.xlsx"), help="Output Excel path")

    # all subcommand
    p_all = sub.add_parser("all", help="Run extract then report")
    p_all.add_argument("--src", default=str(Path("data")), help="Source directory with input files and archives")
    p_all.add_argument("--dest", default=str(Path("archive")), help="Destination directory for extracted contents")
    p_all.add_argument("--out", default=str(Path("summary_files") / "case_item_report.xlsx"), help="Output Excel path")

    return p.parse_args()


def run_extract(src: str, dest: str):
    sys.argv = ["extract_data.py", "--src", src, "--dest", dest]
    extract_data.main()


def run_report(src: str, out: str):
    sys.argv = ["generate_case_item_report.py", "--src", src, "--out", out]
    generate_case_item_report.main()


def main():
    args = parse_args()
    if args.cmd == "extract":
        run_extract(args.src, args.dest)
    elif args.cmd == "report":
        run_report(args.src, args.out)
    elif args.cmd == "all":
        run_extract(args.src, args.dest)
        run_report(args.src, args.out)
    else:
        print(f"Unknown command: {args.cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
