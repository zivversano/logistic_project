# Data Extraction Script

This directory contains `extract_data.py`, a utility to extract archives from a source directory into a destination directory.

## Supported Formats
- `.zip`
- `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`, `.tar.xz`, `.txz`
- Single-file `.gz`, `.bz2` (decompressed to files)

## Default Behavior
- Source: `data/`
- Destination: `archive/`
- Each archive is extracted into its own subfolder named after the archive file (without compression extension).

## Usage
```bash
python3 model/extract_data.py
python3 model/extract_data.py --src /path/to/data --dest /path/to/archive
```

Or run directly (executable script):
```bash
chmod +x model/extract_data.py
./model/extract_data.py --src data --dest archive
```

## Notes
- If `data/` does not exist, the script exits with an error.
- Destination directories are created as needed.
