#!/usr/bin/env python3
"""
Extract compressed files from a source directory.

Default behavior:
- Reads files from `data/` (relative to project root)
- Extracts archives into `archive/` (relative to project root)

Supported formats:
- .zip
- .tar, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .txz
- Single-file .gz and .bz2 (decompress to a file)

Usage:
    python model/extract_data.py [--src DIR] [--dest DIR]

Examples:
    python model/extract_data.py
    python model/extract_data.py --src /path/to/data --dest /path/to/archive
"""

import argparse
import os
import sys
import shutil
import tarfile
import zipfile
import gzip
import bz2
from pathlib import Path

SUPPORTED_ARCHIVE_EXTS = {
    "+zip": {".zip"},
    "+tar": {".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"},
    "+gz": {".gz"},
    "+bz2": {".bz2"},
}

# Flatten set of all supported extensions
ALL_EXTS = set().union(*SUPPORTED_ARCHIVE_EXTS.values())


def is_supported_archive(file_path: Path) -> bool:
    """Return True if the file has a supported archive/compression extension."""
    name = file_path.name.lower()
    # handle multi-part extensions like .tar.gz, .tar.bz2
    multi_part_exts = [
        ".tar.gz", ".tar.bz2", ".tar.xz", ".tbz2", ".tgz", ".txz"
    ]
    for ext in multi_part_exts:
        if name.endswith(ext):
            return True
    # fallback to single suffix
    return file_path.suffix.lower() in ALL_EXTS


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def extract_zip(src: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dest_dir)


def extract_tar(src: Path, dest_dir: Path) -> None:
    with tarfile.open(src, "r:*") as tf:
        tf.extractall(dest_dir)


def decompress_gz(src: Path, dest_dir: Path) -> None:
    # Decompress single-file .gz to its original name without .gz
    out_name = src.name[:-3] if src.name.lower().endswith(".gz") else src.stem
    out_path = dest_dir / out_name
    with gzip.open(src, "rb") as f_in, open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def decompress_bz2_file(src: Path, dest_dir: Path) -> None:
    out_name = src.name[:-4] if src.name.lower().endswith(".bz2") else src.stem
    out_path = dest_dir / out_name
    with bz2.open(src, "rb") as f_in, open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def extract_file(src: Path, dest_root: Path) -> None:
    """Extract or decompress `src` into a subdirectory of `dest_root` named after the archive."""
    # Create per-archive subdir to avoid file collisions
    safe_name = src.name
    # For multi-part extension, strip appropriately for folder name
    base = safe_name
    for ext in [
        ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz",
        ".zip", ".tar", ".gz", ".bz2"
    ]:
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
            break
    out_dir = dest_root / base
    ensure_dir(out_dir)

    lower_name = src.name.lower()
    try:
        if lower_name.endswith(".zip"):
            extract_zip(src, out_dir)
        elif lower_name.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
            extract_tar(src, out_dir)
        elif lower_name.endswith(".gz") and not lower_name.endswith((".tar.gz", ".tgz")):
            decompress_gz(src, out_dir)
        elif lower_name.endswith(".bz2") and not lower_name.endswith(".tar.bz2"):
            decompress_bz2_file(src, out_dir)
        else:
            raise ValueError(f"Unsupported archive type for {src}")
    except Exception as e:
        # Clean up empty dir on failure
        try:
            if out_dir.exists() and not any(out_dir.iterdir()):
                out_dir.rmdir()
        except Exception:
            pass
        raise RuntimeError(f"Failed to extract {src}: {e}") from e


def find_archives(src_dir: Path):
    for p in src_dir.iterdir():
        if p.is_file() and is_supported_archive(p):
            yield p


def parse_args():
    parser = argparse.ArgumentParser(description="Extract archives from a directory")
    parser.add_argument("--src", default=str(Path("data")), help="Source directory containing archives")
    parser.add_argument("--dest", default=str(Path("archive")), help="Destination directory for extracted contents")
    return parser.parse_args()


def main():
    args = parse_args()
    src_dir = Path(args.src).resolve()
    dest_dir = Path(args.dest).resolve()

    if not src_dir.exists() or not src_dir.is_dir():
        print(f"Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    ensure_dir(dest_dir)

    archives = list(find_archives(src_dir))
    if not archives:
        print(f"No supported archives found in {src_dir}")
        return

    print(f"Found {len(archives)} archive(s) in {src_dir}.")
    for i, arc in enumerate(archives, start=1):
        print(f"[{i}/{len(archives)}] Extracting {arc.name}...")
        extract_file(arc, dest_dir)
    print(f"All done. Extracted to {dest_dir}.")


if __name__ == "__main__":
    main()
