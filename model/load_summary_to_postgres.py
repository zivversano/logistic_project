#!/usr/bin/env python3
"""
Load all Excel summaries from summary_files/ into Postgres tables.

- host: localhost
- port: 15432
- user: logistic
- password: logistic
- db: logistic

Each Excel file becomes a table named from the filename stem, lowercased and
non-alphanumeric chars replaced with underscores.

Usage examples:
    python model/load_summary_to_postgres.py
    python model/load_summary_to_postgres.py --summary-dir summary_files --db-url postgres://logistic:logistic@localhost:9090/logistic
"""

import argparse
import os
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

DEFAULT_SUMMARY_DIR = Path("summary_files")
DEFAULT_DB_URL = "postgresql+psycopg2://logistic:logistic@localhost:15432/logistic"


def slugify(name: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_")
    return slug.lower() or "table"


def load_file(file_path: Path, engine) -> None:
    df = pd.read_excel(file_path)
    table_name = slugify(file_path.stem)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into table '{table_name}'")


def load_all(summary_dir: Path, engine) -> None:
    files = sorted(p for p in summary_dir.glob("*.xlsx") if p.is_file())
    if not files:
        print(f"No .xlsx files found in {summary_dir}")
        return
    for f in files:
        load_file(f, engine)


def parse_args():
    parser = argparse.ArgumentParser(description="Load summary Excel files into Postgres")
    parser.add_argument("--summary-dir", type=Path, default=DEFAULT_SUMMARY_DIR, help="Directory with summary .xlsx files")
    parser.add_argument("--db-url", type=str, default=os.getenv("DATABASE_URL", DEFAULT_DB_URL), help="SQLAlchemy DB URL")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.summary_dir.exists():
        raise SystemExit(f"Summary directory not found: {args.summary_dir}")

    engine = create_engine(args.db_url)
    load_all(args.summary_dir, engine)


if __name__ == "__main__":
    main()
