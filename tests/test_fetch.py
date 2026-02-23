"""Tests for sumodata.fetch."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sumodata.fetch import (
    banzuke_url,
    fetch_page,
    fetch_with_cache,
    results_url,
    rikishi_url,
)
from sumodata.util import FetchError


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


class TestFetchPage:
    """Tests for fetch_page with mocked HTTP."""

    @patch("sumodata.fetch.time.sleep")
    @patch("sumodata.fetch.requests.get")
    def test_success_returns_html(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>OK</html>"
        mock_get.return_value = mock_resp

        result = fetch_page("https://example.com")
        assert result == "<html>OK</html>"
        mock_get.assert_called_once()

    @patch("sumodata.fetch.time.sleep")
    @patch("sumodata.fetch.requests.get")
    def test_retries_on_500(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.text = "<html>OK</html>"
        mock_get.side_effect = [fail_resp, ok_resp]

        result = fetch_page("https://example.com")
        assert result == "<html>OK</html>"
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once()  # backoff between retries

    @patch("sumodata.fetch.time.sleep")
    @patch("sumodata.fetch.requests.get")
    def test_raises_after_max_retries(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        mock_get.return_value = fail_resp

        with pytest.raises(FetchError, match="HTTP 503"):
            fetch_page("https://example.com")
        assert mock_get.call_count == 3  # MAX_RETRIES

    @patch("sumodata.fetch.time.sleep")
    @patch("sumodata.fetch.requests.get")
    def test_retries_on_connection_error(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        import requests
        mock_get.side_effect = [
            requests.ConnectionError("timeout"),
            MagicMock(status_code=200, text="<html>OK</html>"),
        ]

        result = fetch_page("https://example.com")
        assert result == "<html>OK</html>"
        assert mock_get.call_count == 2

    @patch("sumodata.fetch.time.sleep")
    @patch("sumodata.fetch.requests.get")
    def test_exponential_backoff(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        mock_get.return_value = fail_resp

        with pytest.raises(FetchError):
            fetch_page("https://example.com")

        # Backoff: 1s after attempt 1, 2s after attempt 2
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)


class TestFetchWithCache:
    """Tests for fetch_with_cache."""

    @patch("sumodata.fetch.fetch_page")
    @patch("sumodata.fetch._page_sleep")
    def test_cache_hit_skips_fetch(self, mock_sleep: MagicMock, mock_fetch: MagicMock, tmp_path: Path) -> None:
        cache_path = tmp_path / "cached.html"
        cache_path.write_text("<html>cached</html>", encoding="utf-8")

        result = fetch_with_cache("https://example.com", cache_path, use_cache=True)
        assert result == "<html>cached</html>"
        mock_fetch.assert_not_called()

    @patch("sumodata.fetch.fetch_page", return_value="<html>fetched</html>")
    @patch("sumodata.fetch._page_sleep")
    def test_cache_miss_fetches_and_saves(self, mock_sleep: MagicMock, mock_fetch: MagicMock, tmp_path: Path) -> None:
        cache_path = tmp_path / "sub" / "cached.html"
        assert not cache_path.exists()

        result = fetch_with_cache("https://example.com", cache_path, use_cache=True)
        assert result == "<html>fetched</html>"
        assert cache_path.read_text(encoding="utf-8") == "<html>fetched</html>"

    @patch("sumodata.fetch.fetch_page", return_value="<html>fetched</html>")
    @patch("sumodata.fetch._page_sleep")
    def test_cache_off_does_not_save(self, mock_sleep: MagicMock, mock_fetch: MagicMock, tmp_path: Path) -> None:
        cache_path = tmp_path / "cached.html"

        result = fetch_with_cache("https://example.com", cache_path, use_cache=False)
        assert result == "<html>fetched</html>"
        assert not cache_path.exists()

    @patch("sumodata.fetch.fetch_page", return_value="<html>fetched</html>")
    @patch("sumodata.fetch._page_sleep")
    def test_cache_path_none(self, mock_sleep: MagicMock, mock_fetch: MagicMock) -> None:
        result = fetch_with_cache("https://example.com", None, use_cache=True)
        assert result == "<html>fetched</html>"
