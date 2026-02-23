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

    def test_fusen_kimarite_set_to_fusen(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[2].kimarite == "fusen"

    def test_fusen_winner_side(self, results_sample_html: str) -> None:
        """Fusensho on east side means east wins."""
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[2].winner_side == "E"

    def test_rank_extraction(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        assert records[0].east_rank == "O1e"
        assert records[0].west_rank == "S1w"

    def test_meta_fields_from_params(self, results_sample_html: str) -> None:
        records = parse_results_page(html=results_sample_html, **self._COMMON)
        r = records[0]
        assert r.event_id == "202501-01"
        assert r.event_type == "honbasho_regular"
        assert r.is_regular == "T"
        assert r.basho == "202501"
        assert r.day == 1
        assert r.source_url == "https://example.com"
        assert r.fetched_at == "2025-01-12T00:00:00"


class TestMultipleDivisions:
    """Tests for parsing pages with multiple divisions."""

    _COMMON = dict(
        event_id="test",
        event_type="honbasho_regular",
        is_regular="T",
        basho="202501",
        day=1,
        source_url="https://example.com",
        fetched_at="2025-01-12T00:00:00",
    )

    def test_both_divisions_parsed(self, results_multi_division_html: str) -> None:
        records = parse_results_page(html=results_multi_division_html, **self._COMMON)
        divisions = {r.division for r in records}
        assert divisions == {"Makuuchi", "Juryo"}

    def test_total_bout_count(self, results_multi_division_html: str) -> None:
        records = parse_results_page(html=results_multi_division_html, **self._COMMON)
        assert len(records) == 3  # 2 Makuuchi + 1 Juryo

    def test_bout_no_resets_at_division_boundary(self, results_multi_division_html: str) -> None:
        records = parse_results_page(html=results_multi_division_html, **self._COMMON)
        maku = [r for r in records if r.division == "Makuuchi"]
        juryo = [r for r in records if r.division == "Juryo"]
        assert [r.bout_no for r in maku] == [1, 2]
        assert [r.bout_no for r in juryo] == [1]

    def test_source_row_index_continues_across_divisions(self, results_multi_division_html: str) -> None:
        records = parse_results_page(html=results_multi_division_html, **self._COMMON)
        assert [r.source_row_index for r in records] == [1, 2, 3]

    def test_juryo_rid_extraction(self, results_multi_division_html: str) -> None:
        records = parse_results_page(html=results_multi_division_html, **self._COMMON)
        juryo = [r for r in records if r.division == "Juryo"][0]
        assert juryo.east_rid == 30001
        assert juryo.west_rid == 30002

    def test_juryo_kimarite(self, results_multi_division_html: str) -> None:
        records = parse_results_page(html=results_multi_division_html, **self._COMMON)
        juryo = [r for r in records if r.division == "Juryo"][0]
        assert juryo.kimarite == "uwatenage"


class TestKyujoHandling:
    """Tests for kyujo (absent) bout handling."""

    _COMMON = dict(
        event_id="test",
        event_type="honbasho_regular",
        is_regular="T",
        basho="202501",
        day=5,
        source_url="https://example.com",
        fetched_at="2025-01-12T00:00:00",
    )

    def test_kyujo_result_type(self, results_kyujo_html: str) -> None:
        records = parse_results_page(html=results_kyujo_html, **self._COMMON)
        assert records[1].result_type == "kyujo"

    def test_kyujo_winner_side_empty(self, results_kyujo_html: str) -> None:
        records = parse_results_page(html=results_kyujo_html, **self._COMMON)
        assert records[1].winner_side == ""

    def test_kyujo_kimarite_empty(self, results_kyujo_html: str) -> None:
        records = parse_results_page(html=results_kyujo_html, **self._COMMON)
        assert records[1].kimarite == ""

    def test_kyujo_missing_rid(self, results_kyujo_html: str) -> None:
        """Kyujo bout has rid=0 for the absent side."""
        records = parse_results_page(html=results_kyujo_html, **self._COMMON)
        assert records[1].west_rid == 0

    def test_normal_bout_still_parsed(self, results_kyujo_html: str) -> None:
        records = parse_results_page(html=results_kyujo_html, **self._COMMON)
        assert records[0].result_type == "normal"
        assert records[0].east_rid == 12270


class TestPlayoffResultType:
    """Test that day=16 bouts get result_type=playoff."""

    def test_day16_result_type_is_playoff(self, results_sample_html: str) -> None:
        records = parse_results_page(
            html=results_sample_html,
            event_id="honbasho-202501-playoff",
            event_type="honbasho_playoff",
            is_regular="F",
            basho="202501",
            day=16,
            source_url="https://example.com",
            fetched_at="2025-01-12T00:00:00",
        )
        # Normal bouts on day 16 should be classified as playoff
        # (fusen still takes priority over playoff)
        normal_bouts = [r for r in records if r.result_type != "fusen"]
        for r in normal_bouts:
            assert r.result_type == "playoff"

    def test_day16_fusen_still_fusen(self, results_sample_html: str) -> None:
        """Fusen detection takes priority even on day 16."""
        records = parse_results_page(
            html=results_sample_html,
            event_id="honbasho-202501-playoff",
            event_type="honbasho_playoff",
            is_regular="F",
            basho="202501",
            day=16,
            source_url="https://example.com",
            fetched_at="2025-01-12T00:00:00",
        )
        fusen_bouts = [r for r in records if r.result_type == "fusen"]
        assert len(fusen_bouts) == 1  # The third bout is still fusen


class TestDetectPlayoff:
    """Tests for detect_playoff()."""

    def test_playoff_detected(self, results_sample_html: str) -> None:
        assert detect_playoff(results_sample_html, "202501") is True

    def test_no_playoff(self, results_no_playoff_html: str) -> None:
        assert detect_playoff(results_no_playoff_html, "202501") is False

    def test_wrong_basho_no_match(self, results_sample_html: str) -> None:
        """Playoff link for different basho should not match."""
        assert detect_playoff(results_sample_html, "202503") is False
