"""HTTP fetch with retry, backoff, sleep, and caching."""

import logging
import random
import time
from pathlib import Path

import requests

from sumodata.util import FetchError

logger = logging.getLogger(__name__)

BASE_URL = "https://sumodb.sumogames.de"
HEADERS = {
    "User-Agent": "sumodata/0.1 (+https://github.com/owner/sumo_scrape)"
}
MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds: 1, 2, 4
SLEEP_MIN = 0.5
SLEEP_MAX = 1.5


def results_url(basho: str, day: int) -> str:
    return f"{BASE_URL}/Results.aspx?b={basho}&d={day}"


def banzuke_url(basho: str) -> str:
    return f"{BASE_URL}/Banzuke.aspx?b={basho}"


def rikishi_url(rid: int) -> str:
    return f"{BASE_URL}/Rikishi.aspx?r={rid}"


def fetch_page(url: str) -> str:
    """Fetch a page with retry and exponential backoff."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug("Fetching %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                logger.debug("OK %s", url)
                return resp.text
            logger.warning(
                "HTTP %d for %s (attempt %d/%d)",
                resp.status_code, url, attempt, MAX_RETRIES,
            )
            last_error = FetchError(
                f"HTTP {resp.status_code} for {url}"
            )
        except requests.RequestException as e:
            logger.warning(
                "Connection error for %s (attempt %d/%d): %s",
                url, attempt, MAX_RETRIES, e,
            )
            last_error = FetchError(f"Connection error for {url}: {e}")

        if attempt < MAX_RETRIES:
            backoff = BACKOFF_BASE * (2 ** (attempt - 1))
            logger.debug("Backoff %ds before retry", backoff)
            time.sleep(backoff)

    raise last_error  # type: ignore[misc]


def _page_sleep() -> None:
    """Random sleep between page fetches."""
    delay = random.uniform(SLEEP_MIN, SLEEP_MAX)
    time.sleep(delay)


def fetch_with_cache(
    url: str,
    cache_path: Path | None,
    use_cache: bool,
) -> str:
    """Fetch a page, optionally using/saving cache."""
    if use_cache and cache_path and cache_path.exists():
        logger.info("Cache hit: %s", cache_path)
        return cache_path.read_text(encoding="utf-8")

    html = fetch_page(url)
    _page_sleep()

    if use_cache and cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")
        logger.debug("Cached to %s", cache_path)

    return html
