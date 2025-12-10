#!/usr/bin/env python3
"""
Simple watcher: when new Excel files appear in data/, run main.py to process them.

- Polls the data directory every N seconds (default 5).
- Detects new .xlsx/.xls files that were not seen before and triggers main.py.
- Since main.py moves processed files to archive/, reruns will process fresh arrivals only.

Usage:
    python model/watch_data.py
    python model/watch_data.py --interval 3
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PYTHON = sys.executable
MAIN = ROOT / "main.py"


def list_excel_files() -> set[Path]:
    if not DATA_DIR.exists():
        return set()
    return {p for p in DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".xlsx", ".xls"}}


def run_main():
    print("\nDetected new file(s). Running main.py ...", flush=True)
    result = subprocess.run([PYTHON, str(MAIN)], cwd=ROOT)
    if result.returncode != 0:
        print(f"main.py exited with code {result.returncode}", file=sys.stderr)
    else:
        print("main.py completed.", flush=True)


def watch(interval: float):
    seen = list_excel_files()
    if seen:
        print(f"Initial files present; running main.py once to process them ({len(seen)} file(s))...")
        run_main()
        seen = list_excel_files()

    print(f"Watching {DATA_DIR} for new Excel files. Poll interval: {interval}s")
    try:
        while True:
            time.sleep(interval)
            current = list_excel_files()
            new_files = current - seen
            if new_files:
                print(f"Detected {len(new_files)} new file(s): {[p.name for p in new_files]}")
                run_main()
                # After main, files should be moved; refresh seen to what's left
                seen = list_excel_files()
            else:
                seen = current
    except KeyboardInterrupt:
        print("Watcher stopped by user.")


def parse_args():
    parser = argparse.ArgumentParser(description="Watch data/ for new Excel files and trigger main.py")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    return parser.parse_args()


def main():
    args = parse_args()
    watch(args.interval)


if __name__ == "__main__":
    main()
