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
python model/extract_data.py
python model/extract_data.py --src /path/to/data --dest /path/to/archive
```

## Notes
- If `data/` does not exist, the script exits with an error.
- Destination directories are created as needed.

## Surgery totals aggregator
- Script: `model/compute_surgery_totals.py`
- Purpose: group the hernia dataset by case number and sum total price and quantity; keeps first non-null surgeon name and score.
- Default input: `data/hernia both sides final copilot.xlsx`
- Default output: `summary_files/case_surgery_totals.xlsx`

### Usage
```bash
python model/compute_surgery_totals.py
python model/compute_surgery_totals.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/case_surgery_totals.xlsx
```

## Surgeon average price aggregator
- Script: `model/compute_surgeon_averages.py`
- Purpose: aggregate per-surgeon average surgery price, count of unique cases, and label surgeons as `cheap`/`expensive` based on average price.
- Default input: `data/hernia both sides final copilot.xlsx`
- Default output: `summary_files/surgeon_avg_prices.xlsx`

### Usage
```bash
python model/compute_surgeon_averages.py
python model/compute_surgeon_averages.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/surgeon_avg_prices.xlsx
# Optional: set a custom threshold for cheap/expensive (default is median of avg price)
python model/compute_surgeon_averages.py --threshold 3000
```

## Case item grouping
- Script: `model/compute_case_items.py`
- Purpose: group data per case, list items with quantities, total item count, surgeon info, price group, and total surgery price.
- Default input: `data/hernia both sides final copilot.xlsx`
- Default output: `summary_files/case_items_detail.xlsx`

### Usage
```bash
python model/compute_case_items.py
python model/compute_case_items.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/case_items_detail.xlsx
# Optional: custom threshold for cheap/expensive surgeon price groups
python model/compute_case_items.py --threshold 3000
```

## Item combinations summary
- Script: `model/compute_item_combinations.py`
- Purpose: summarize identical item combinations across cases with frequency, surgeons (with score), price groups, and average total price.
- Default input: `data/hernia both sides final copilot.xlsx`
- Default output: `summary_files/item_combinations.xlsx`

### Usage
```bash
python model/compute_item_combinations.py
python model/compute_item_combinations.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/item_combinations.xlsx
# Optional: threshold for cheap/expensive price groups
python model/compute_item_combinations.py --threshold 3000
```

## Data watcher
- Script: `model/watch_data.py`
- Purpose: poll `data/` for new Excel files and trigger `main.py` automatically. Since `main.py` moves processed files to `archive/`, each new file is handled once.

### Usage
```bash
python model/watch_data.py            # poll every 5s
python model/watch_data.py --interval 2
```

## Outcome scores per case
- Script: `model/compute_outcome_scores.py`
- Purpose: score each case (0-1) based on 14 clinical parameters; classify outcome into good/moderate/bad.
- Default input: `data/hernia both sides final copilot.xlsx`
- Default output: `summary_files/case_outcome_scores.xlsx`

### Usage
```bash
python model/compute_outcome_scores.py
python model/compute_outcome_scores.py --input "data/hernia both sides final copilot.xlsx" --output summary_files/case_outcome_scores.xlsx
```
