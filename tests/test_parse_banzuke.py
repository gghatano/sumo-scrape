"""Tests for sumodata.parse_banzuke."""

from sumodata.parse_banzuke import parse_banzuke_page


class TestParseBanzukePage:
    """Tests for parse_banzuke_page()."""

    _COMMON = dict(
        basho="202501",
        source_url="https://example.com/banzuke",
    )

    def test_correct_number_of_records(self, banzuke_sample_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        assert len(records) == 3

    def test_rid_extraction(self, banzuke_sample_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        rids = [r.rid for r in records]
        assert 12270 in rids
        assert 12451 in rids
        assert 11980 in rids

    def test_shikona_from_title(self, banzuke_sample_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        by_rid = {r.rid: r for r in records}
        assert by_rid[12270].shikona_at_basho == "琴櫻"
        assert by_rid[12451].shikona_at_basho == "豊昇龍"
        assert by_rid[11980].shikona_at_basho == "若元春"

    def test_rank_construction(self, banzuke_sample_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        by_rid = {r.rid: r for r in records}
        assert by_rid[12270].rank == "Ye"
        assert by_rid[12451].rank == "Yw"
        assert by_rid[11980].rank == "Se"

    def test_emptycell_skipped(self, banzuke_sample_html: str) -> None:
        """West side of row 2 is emptycell -- should not produce a record."""
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        # Only 3 records: 2 from row 1, 1 from row 2
        assert len(records) == 3

    def test_maezumo_skipped(self, banzuke_sample_html: str) -> None:
        """Mae-zumo table should be skipped entirely."""
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        divisions = {r.division for r in records}
        assert "Mae-zumo" not in divisions

    def test_division_field(self, banzuke_sample_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        assert all(r.division == "Makuuchi" for r in records)

    def test_source_url_passed_through(self, banzuke_sample_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_sample_html, **self._COMMON)
        assert all(r.source_url == "https://example.com/banzuke" for r in records)


class TestMultipleDivisionsBanzuke:
    """Tests for banzuke pages with multiple divisions."""

    _COMMON = dict(
        basho="202501",
        source_url="https://example.com/banzuke",
    )

    def test_all_divisions_parsed(self, banzuke_multi_division_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        divisions = {r.division for r in records}
        assert divisions == {"Makuuchi", "Juryo", "Makushita"}

    def test_total_record_count(self, banzuke_multi_division_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        # Makuuchi: 2, Juryo: 2, Makushita: 2
        assert len(records) == 6

    def test_banzukegai_skipped(self, banzuke_multi_division_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        divisions = {r.division for r in records}
        assert "Banzuke-gai" not in divisions

    def test_juryo_rank_construction(self, banzuke_multi_division_html: str) -> None:
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        juryo = {r.rid: r for r in records if r.division == "Juryo"}
        assert juryo[30001].rank == "J1e"
        assert juryo[30002].rank == "J1w"


class TestShikonaFallback:
    """Tests for shikona extraction fallback behavior."""

    _COMMON = dict(
        basho="202501",
        source_url="https://example.com/banzuke",
    )

    def test_no_title_falls_back_to_romaji(self, banzuke_multi_division_html: str) -> None:
        """When title attribute is missing, use link text (romaji)."""
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        by_rid = {r.rid: r for r in records}
        assert by_rid[40001].shikona_at_basho == "NoTitleRikishi"

    def test_empty_title_falls_back_to_romaji(self, banzuke_multi_division_html: str) -> None:
        """When title attribute is empty string, use link text (romaji)."""
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        by_rid = {r.rid: r for r in records}
        assert by_rid[40002].shikona_at_basho == "EmptyTitleRikishi"

    def test_title_present_uses_japanese(self, banzuke_multi_division_html: str) -> None:
        """When title is present, first field (Japanese name) is used."""
        records = parse_banzuke_page(html=banzuke_multi_division_html, **self._COMMON)
        by_rid = {r.rid: r for r in records}
        assert by_rid[12270].shikona_at_basho == "琴櫻"
        assert by_rid[30001].shikona_at_basho == "力士A"
