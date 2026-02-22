"""CSV read/write with upsert and force replace."""

import csv
import logging
from dataclasses import asdict, fields
from pathlib import Path

from sumodata.models import BoutRecord, ShikonaRecord

logger = logging.getLogger(__name__)

FACT_COLUMNS = [
    "event_id", "event_type", "is_regular", "basho", "day", "division",
    "bout_no", "east_rid", "west_rid", "winner_side", "kimarite",
    "east_rank", "west_rank", "result_type", "note", "source_url",
    "source_row_index", "fetched_at",
]

DIM_SHIKONA_COLUMNS = [
    "basho", "rid", "shikona_at_basho", "source_url", "division", "rank",
]

FACT_KEY_COLUMNS = ["event_id", "day", "division", "bout_no"]
FACT_SORT_COLUMNS = ["event_id", "day", "division", "bout_no"]

DIM_KEY_COLUMNS = ["basho", "rid"]
DIM_SORT_COLUMNS = ["basho", "rid"]


def _records_to_dicts(records: list) -> list[dict]:
    """Convert dataclass records to list of dicts with string values."""
    result = []
    for r in records:
        d = asdict(r)
        # Ensure all values are strings for CSV
        result.append({k: str(v) for k, v in d.items()})
    return result


def _read_csv(path: Path, fieldnames: list[str]) -> list[dict]:
    """Read existing CSV file, return list of dicts. Empty list if missing."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write rows to CSV with LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _sort_rows(rows: list[dict], sort_columns: list[str]) -> list[dict]:
    """Sort rows by sort_columns. Numeric columns sorted as numbers."""
    numeric_cols = {"day", "bout_no", "rid", "source_row_index", "east_rid", "west_rid"}

    def sort_key(row: dict) -> tuple:
        parts = []
        for col in sort_columns:
            val = row.get(col, "")
            if col in numeric_cols:
                try:
                    parts.append(int(val))
                except (ValueError, TypeError):
                    parts.append(0)
            else:
                parts.append(val)
        return tuple(parts)

    return sorted(rows, key=sort_key)


def upsert(
    csv_path: Path,
    new_records: list[dict],
    key_columns: list[str],
    sort_columns: list[str],
    fieldnames: list[str],
) -> None:
    """Read existing CSV, upsert new records by key, write sorted output."""
    existing = _read_csv(csv_path, fieldnames)

    # Build dict keyed by key tuple
    indexed: dict[tuple, dict] = {}
    for row in existing:
        key = tuple(str(row.get(k, "")) for k in key_columns)
        indexed[key] = row

    # Upsert
    for row in new_records:
        key = tuple(str(row.get(k, "")) for k in key_columns)
        indexed[key] = row

    rows = list(indexed.values())
    rows = _sort_rows(rows, sort_columns)
    _write_csv(csv_path, rows, fieldnames)
    logger.info("Upserted %d new records -> %d total rows in %s",
                len(new_records), len(rows), csv_path)


def force_replace(
    csv_path: Path,
    new_records: list[dict],
    filter_column: str,
    filter_value: str,
    sort_columns: list[str],
    fieldnames: list[str],
) -> None:
    """Remove rows matching filter, add new records, write sorted output."""
    existing = _read_csv(csv_path, fieldnames)

    # Remove matching rows
    kept = [r for r in existing if str(r.get(filter_column, "")) != filter_value]
    removed = len(existing) - len(kept)

    # Add new
    kept.extend(new_records)
    kept = _sort_rows(kept, sort_columns)
    _write_csv(csv_path, kept, fieldnames)
    logger.info(
        "Force replaced: removed %d, added %d -> %d total rows in %s",
        removed, len(new_records), len(kept), csv_path,
    )


def write_fact_csv(records: list[BoutRecord], path: Path) -> None:
    """Write fact_bout_daily.csv from scratch."""
    rows = _records_to_dicts(records)
    rows = _sort_rows(rows, FACT_SORT_COLUMNS)
    _write_csv(path, rows, FACT_COLUMNS)
    logger.info("Wrote %d fact rows to %s", len(rows), path)


def write_dim_shikona_csv(records: list[ShikonaRecord], path: Path) -> None:
    """Write dim_shikona_by_basho.csv from scratch."""
    rows = _records_to_dicts(records)
    rows = _sort_rows(rows, DIM_SORT_COLUMNS)
    _write_csv(path, rows, DIM_SHIKONA_COLUMNS)
    logger.info("Wrote %d dim_shikona rows to %s", len(rows), path)


def update_fact_csv(
    new_records: list[BoutRecord],
    path: Path,
    force: bool,
    event_id: str,
) -> None:
    """Update fact CSV with upsert or force replace."""
    rows = _records_to_dicts(new_records)
    if force:
        force_replace(path, rows, "event_id", event_id, FACT_SORT_COLUMNS, FACT_COLUMNS)
    else:
        upsert(path, rows, FACT_KEY_COLUMNS, FACT_SORT_COLUMNS, FACT_COLUMNS)


def update_dim_shikona_csv(
    new_records: list[ShikonaRecord],
    path: Path,
    force: bool,
    basho: str,
) -> None:
    """Update dim_shikona CSV with upsert or force replace."""
    rows = _records_to_dicts(new_records)
    if force:
        force_replace(path, rows, "basho", basho, DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)
    else:
        upsert(path, rows, DIM_KEY_COLUMNS, DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)
