"""Tests for sumodata.fetch URL builders (no HTTP)."""

from sumodata.fetch import banzuke_url, results_url, rikishi_url


class TestUrlBuilders:
    def test_results_url(self) -> None:
        assert results_url("202501", 1) == (
            "https://sumodb.sumogames.de/Results.aspx?b=202501&d=1"
        )

    def test_banzuke_url(self) -> None:
        assert banzuke_url("202501") == (
            "https://sumodb.sumogames.de/Banzuke.aspx?b=202501"
        )

    def test_rikishi_url(self) -> None:
        assert rikishi_url(12270) == (
            "https://sumodb.sumogames.de/Rikishi.aspx?r=12270"
        )
