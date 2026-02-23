"""Tests for sumodata.io_csv."""

import csv
from pathlib import Path

from sumodata.io_csv import (
    DIM_KEY_COLUMNS,
    DIM_SHIKONA_COLUMNS,
    DIM_SORT_COLUMNS,
    FACT_COLUMNS,
    FACT_KEY_COLUMNS,
    FACT_SORT_COLUMNS,
    force_replace,
    update_dim_shikona_csv,
    update_fact_csv,
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
        event_id="honbasho-202501",
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

    def test_column_order_matches_spec(self, tmp_path: Path) -> None:
        path = tmp_path / "fact.csv"
        write_fact_csv([_make_bout()], path)
        with open(path, encoding="utf-8") as f:
            header = f.readline().strip()
        assert header == ",".join(FACT_COLUMNS)

    def test_lf_line_endings(self, tmp_path: Path) -> None:
        path = tmp_path / "fact.csv"
        write_fact_csv([_make_bout()], path)
        raw = path.read_bytes()
        assert b"\r\n" not in raw
        assert b"\n" in raw


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

    def test_upsert_on_nonexistent_file(self, tmp_path: Path) -> None:
        """Upsert on a file that doesn't exist yet should create it."""
        path = tmp_path / "new_file.csv"
        assert not path.exists()
        new = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
        ]
        upsert(path, new, DIM_KEY_COLUMNS, DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)
        rows = _read_csv_rows(path)
        assert len(rows) == 1

    def test_upsert_preserves_unrelated_rows(self, tmp_path: Path) -> None:
        """Upsert should not remove rows with different keys."""
        path = tmp_path / "upsert.csv"
        existing = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
            {"basho": "202503", "rid": "1", "shikona_at_basho": "A2",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DIM_SHIKONA_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(existing)

        new = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A-updated",
             "source_url": "u2", "division": "Makuuchi", "rank": "Ye"},
        ]
        upsert(path, new, DIM_KEY_COLUMNS, DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)
        rows = _read_csv_rows(path)
        assert len(rows) == 2
        by_key = {(r["basho"], r["rid"]): r for r in rows}
        assert by_key[("202501", "1")]["shikona_at_basho"] == "A-updated"
        assert by_key[("202503", "1")]["shikona_at_basho"] == "A2"


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

    def test_force_replace_on_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / "new_force.csv"
        new = [
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
        ]
        force_replace(path, new, "basho", "202501",
                       DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)
        rows = _read_csv_rows(path)
        assert len(rows) == 1


class TestNumericSortOrder:
    """Verify that numeric columns sort as numbers, not strings."""

    def test_fact_day_sorts_numerically(self, tmp_path: Path) -> None:
        """Days 1, 2, 10 should sort as 1, 2, 10 (not 1, 10, 2)."""
        path = tmp_path / "fact.csv"
        records = [
            _make_bout(day=10, bout_no=1, source_row_index=3),
            _make_bout(day=1, bout_no=1, source_row_index=1),
            _make_bout(day=2, bout_no=1, source_row_index=2),
        ]
        write_fact_csv(records, path)
        rows = _read_csv_rows(path)
        days = [int(r["day"]) for r in rows]
        assert days == [1, 2, 10]

    def test_fact_bout_no_sorts_numerically(self, tmp_path: Path) -> None:
        """Bout numbers 1, 2, 10 in same division should sort correctly."""
        path = tmp_path / "fact.csv"
        records = [
            _make_bout(bout_no=10, source_row_index=3),
            _make_bout(bout_no=1, source_row_index=1),
            _make_bout(bout_no=2, source_row_index=2),
        ]
        write_fact_csv(records, path)
        rows = _read_csv_rows(path)
        bout_nos = [int(r["bout_no"]) for r in rows]
        assert bout_nos == [1, 2, 10]

    def test_dim_rid_sorts_numerically(self, tmp_path: Path) -> None:
        """RIDs 1, 2, 10 should sort as 1, 2, 10 (not 1, 10, 2)."""
        path = tmp_path / "dim.csv"
        records = [
            _make_shikona(rid=10),
            _make_shikona(rid=1),
            _make_shikona(rid=2),
        ]
        write_dim_shikona_csv(records, path)
        rows = _read_csv_rows(path)
        rids = [int(r["rid"]) for r in rows]
        assert rids == [1, 2, 10]

    def test_upsert_maintains_sort_order(self, tmp_path: Path) -> None:
        """After upsert, rows should still be sorted correctly."""
        path = tmp_path / "sort.csv"
        # Start with rid=5
        initial = [
            {"basho": "202501", "rid": "5", "shikona_at_basho": "E",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DIM_SHIKONA_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(initial)

        # Add rid=1 and rid=10
        new = [
            {"basho": "202501", "rid": "10", "shikona_at_basho": "J",
             "source_url": "u", "division": "Juryo", "rank": "J1e"},
            {"basho": "202501", "rid": "1", "shikona_at_basho": "A",
             "source_url": "u", "division": "Makuuchi", "rank": "Ye"},
        ]
        upsert(path, new, DIM_KEY_COLUMNS, DIM_SORT_COLUMNS, DIM_SHIKONA_COLUMNS)
        rows = _read_csv_rows(path)
        rids = [int(r["rid"]) for r in rows]
        assert rids == [1, 5, 10]


class TestUpdateFactCsv:
    """Tests for the high-level update_fact_csv function."""

    def test_upsert_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "fact.csv"
        records = [_make_bout(bout_no=1), _make_bout(bout_no=2)]
        update_fact_csv(records, path, force=False, event_id="honbasho-202501")
        rows = _read_csv_rows(path)
        assert len(rows) == 2

        # Upsert with updated bout and new bout
        records2 = [_make_bout(bout_no=2, kimarite="oshidashi"), _make_bout(bout_no=3)]
        update_fact_csv(records2, path, force=False, event_id="honbasho-202501")
        rows = _read_csv_rows(path)
        assert len(rows) == 3

    def test_force_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "fact.csv"
        records = [_make_bout(bout_no=1), _make_bout(bout_no=2)]
        update_fact_csv(records, path, force=False, event_id="honbasho-202501")

        # Force with only 1 record replaces all for that event_id
        records2 = [_make_bout(bout_no=1)]
        update_fact_csv(records2, path, force=True, event_id="honbasho-202501")
        rows = _read_csv_rows(path)
        assert len(rows) == 1


class TestUpdateDimShikonaCsv:
    """Tests for the high-level update_dim_shikona_csv function."""

    def test_upsert_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "dim.csv"
        records = [_make_shikona(rid=1), _make_shikona(rid=2)]
        update_dim_shikona_csv(records, path, force=False, basho="202501")
        rows = _read_csv_rows(path)
        assert len(rows) == 2

    def test_force_mode_preserves_other_basho(self, tmp_path: Path) -> None:
        path = tmp_path / "dim.csv"
        # Write 202501 and 202503
        r1 = [_make_shikona(rid=1, basho="202501")]
        r2 = [_make_shikona(rid=2, basho="202503")]
        update_dim_shikona_csv(r1, path, force=False, basho="202501")
        update_dim_shikona_csv(r2, path, force=False, basho="202503")

        # Force replace 202501 only
        r3 = [_make_shikona(rid=10, basho="202501")]
        update_dim_shikona_csv(r3, path, force=True, basho="202501")
        rows = _read_csv_rows(path)
        rids = {r["rid"] for r in rows}
        assert "10" in rids  # new
        assert "2" in rids   # 202503 preserved
        assert "1" not in rids  # old 202501 removed
