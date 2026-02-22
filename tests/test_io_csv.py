"""Tests for sumodata.io_csv."""

import csv
from pathlib import Path

from sumodata.io_csv import (
    DIM_SHIKONA_COLUMNS,
    DIM_SORT_COLUMNS,
    DIM_KEY_COLUMNS,
    FACT_COLUMNS,
    FACT_KEY_COLUMNS,
    FACT_SORT_COLUMNS,
    force_replace,
    upsert,
    write_dim_shikona_csv,
    write_fact_csv,
)
from sumodata.models import BoutRecord, ShikonaRecord


def _read_csv_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _make_bout(**overrides) -> BoutRecord:
    defaults = dict(
        event_id="202501-01",
        event_type="honbasho_regular",
        is_regular="T",
        basho="202501",
        day=1,
        division="Makuuchi",
        bout_no=1,
        east_rid=100,
        west_rid=200,
        winner_side="E",
        kimarite="yorikiri",
        east_rank="O1e",
        west_rank="S1w",
        result_type="normal",
        note="",
        source_url="https://example.com",
        source_row_index=1,
        fetched_at="2025-01-12T00:00:00",
    )
    defaults.update(overrides)
    return BoutRecord(**defaults)


def _make_shikona(**overrides) -> ShikonaRecord:
    defaults = dict(
        basho="202501",
        rid=12270,
        shikona_at_basho="琴櫻",
        source_url="https://example.com",
        division="Makuuchi",
        rank="Ye",
    )
    defaults.update(overrides)
    return ShikonaRecord(**defaults)


class TestWriteFactCsv:
    def test_writes_headers_and_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "fact.csv"
        records = [_make_bout(bout_no=1), _make_bout(bout_no=2)]
        write_fact_csv(records, path)
        rows = _read_csv_rows(path)
        assert len(rows) == 2
        assert list(rows[0].keys()) == FACT_COLUMNS

    def test_empty_records_header_only(self, tmp_path: Path) -> None:
        path = tmp_path / "fact_empty.csv"
        write_fact_csv([], path)
        with open(path, encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        assert len(lines) == 1  # header only
        assert lines[0] == ",".join(FACT_COLUMNS)


class TestWriteDimShikonaCsv:
    def test_writes_headers_and_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "dim.csv"
        records = [_make_shikona(rid=1), _make_shikona(rid=2)]
        write_dim_shikona_csv(records, path)
        rows = _read_csv_rows(path)
        assert len(rows) == 2
        assert list(rows[0].keys()) == DIM_SHIKONA_COLUMNS


class TestUpsert:
    def test_merges_existing_and_new(self, tmp_path: Path) -> None:
        path = tmp_path / "upsert.csv"
        # Write initial
        existing = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
            {"basho": "202501", "rid": "2", "shikona_at_basho": "B",
             "source_url": "u", "division": "Makuuchi", "rank": "Yw"},
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DIM_SHIKONA_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(existing)

        new = [
            {"basho": "202501", "rid": "2", "shikona_at_basho": "B-updated",
             "source_url": "u2", "division": "Makuuchi", "rank": "Yw"},
            {"basho": "202501", "rid": "3", "shikona_at_basho": "C",
             "source_url": "u2", "division": "Makuuchi", "rank": "Se"},
        ]
        upsert(path, new, DIM_KEY_COLUMNS, DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)

        rows = _read_csv_rows(path)
        assert len(rows) == 3  # rid 1, 2 (updated), 3
        by_rid = {r["rid"]: r for r in rows}
        assert by_rid["2"]["shikona_at_basho"] == "B-updated"
        assert "3" in by_rid


class TestForceReplace:
    def test_replaces_matching_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "force.csv"
        existing = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
            {"basho": "202503", "rid": "10", "shikona_at_basho": "X",
             "source_url": "u", "division": "Juryo", "rank": "J1e"},
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DIM_SHIKONA_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(existing)

        new = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A-new",
             "source_url": "u2", "division": "Makuuchi", "rank": "Ye"},
            {"basho": "202501", "rid": "5", "shikona_at_basho": "E",
             "source_url": "u2", "division": "Makuuchi", "rank": "Yw"},
        ]
        force_replace(
            path, new, "basho", "202501",
            DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS,
        )

        rows = _read_csv_rows(path)
        # Old 202501 rid=1 removed, new rid=1 and rid=5 added, 202503 rid=10 kept
        assert len(rows) == 3
        bashos = [r["basho"] for r in rows]
        assert "202503" in bashos
        by_rid = {r["rid"]: r for r in rows}
        assert by_rid["1"]["shikona_at_basho"] == "A-new"
        assert "5" in by_rid
