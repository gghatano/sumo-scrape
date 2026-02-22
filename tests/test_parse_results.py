"""Tests for sumodata.parse_results."""

from sumodata.parse_results import detect_playoff, parse_results_page


class TestParseResultsPage:
    """Tests for parse_results_page()."""

    _COMMON = dict(
        event_id="202501-01",
        event_type="honbasho_regular",
        is_regular="T",
        basho="202501",
        day=1,
        source_url="https://example.com",
        fetched_at="2025-01-12T00:00:00",
    )

    def test_division_recognised(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        divisions = {r.division for r in records}
        assert "Makuuchi" in divisions

    def test_correct_number_of_bouts(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert len(records) == 3

    def test_rid_extraction(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        r0 = records[0]
        assert r0.east_rid == 12270
        assert r0.west_rid == 12451

    def test_winner_side_east(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[0].winner_side == "E"

    def test_winner_side_west(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[1].winner_side == "W"

    def test_kimarite_extraction(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[0].kimarite == "yorikiri"
        assert records[1].kimarite == "oshidashi"

    def test_bout_no_resets_per_division(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        bout_nos = [r.bout_no for r in records]
        assert bout_nos == [1, 2, 3]

    def test_source_row_index_page_wide(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        indices = [r.source_row_index for r in records]
        assert indices == [1, 2, 3]

    def test_result_type_normal(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[0].result_type == "normal"
        assert records[1].result_type == "normal"

    def test_result_type_fusen(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[2].result_type == "fusen"


class TestDetectPlayoff:
    """Tests for detect_playoff()."""

    def test_playoff_detected(self, results_sample_html: str) -> None:
        assert detect_playoff(results_sample_html, "202501") is True

    def test_no_playoff(self, results_no_playoff_html: str) -> None:
        assert detect_playoff(results_no_playoff_html, "202501") is False
