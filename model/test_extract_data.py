#!/usr/bin/env python3
"""Minimal self-check for extract_data.py using temporary files.

This does NOT use the workspace `data/` or `archive/` directories; it operates
in a temp sandbox and validates extraction for zip and tar.gz.
"""
import os
import tempfile
import shutil
from pathlib import Path
import tarfile
import zipfile

from extract_data import main as extractor_main, parse_args as extractor_parse_args


def create_sample_files(base: Path):
    (base / "dirA").mkdir()
    (base / "dirA" / "file1.txt").write_text("hello zip")
    (base / "file2.txt").write_text("hello tar")


def make_zip(src_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w") as zf:
        for p in src_dir.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(src_dir).as_posix())


def make_tar_gz(src_dir: Path, tar_gz_path: Path):
    with tarfile.open(tar_gz_path, "w:gz") as tf:
        tf.add(src_dir, arcname=".")


def run_test():
    tmp = Path(tempfile.mkdtemp(prefix="extract_test_"))
    try:
        src = tmp / "data"
        dest = tmp / "archive"
        src.mkdir()
        dest.mkdir()

        # Create content and archives
        work = tmp / "work"
        work.mkdir()
        create_sample_files(work)

        zip_path = src / "sample.zip"
        make_zip(work, zip_path)

        tar_path = src / "sample.tar.gz"
        make_tar_gz(work, tar_path)

        # Run extractor
        import sys
        sys.argv = ["extract_data.py", "--src", str(src), "--dest", str(dest)]
        extractor_main()

        # Validate outputs exist
        zip_out = dest / "sample"
        tar_out = dest / "sample"
        assert zip_out.exists() and any(zip_out.rglob("file1.txt")), "Zip contents missing"
        assert tar_out.exists() and any(tar_out.rglob("file2.txt")), "Tar contents missing"
        print("Self-check passed: zip and tar.gz extracted correctly.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    run_test()
