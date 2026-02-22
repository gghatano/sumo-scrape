"""CLI entry point and main processing flow."""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sumodata.fetch import (
    banzuke_url,
    fetch_with_cache,
    results_url,
)
from sumodata.io_csv import update_dim_shikona_csv, update_fact_csv
from sumodata.models import BoutRecord, ShikonaRecord
from sumodata.parse_banzuke import parse_banzuke_page
from sumodata.parse_results import detect_playoff, parse_results_page
from sumodata.util import SumodataError

logger = logging.getLogger("sumodata")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sumodata",
        description="Fetch sumo bout data from SumoDB and generate CSVs.",
    )
    parser.add_argument(
        "--basho", required=True,
        help="Target basho in YYYYMM format (e.g. 202601)",
    )
    parser.add_argument(
        "--force", action="store_true", default=False,
        help="Force replace rows for the target event (default: upsert)",
    )
    parser.add_argument(
        "--raw-cache", choices=["on", "off"], default="on",
        help="HTML cache mode (default: on)",
    )
    parser.add_argument(
        "--playoff", choices=["on", "off"], default="on",
        help="Playoff detection and fetch (default: on)",
    )
    parser.add_argument(
        "--log-level", choices=["INFO", "DEBUG"], default="INFO",
        help="Logging level (default: INFO)",
    )
    return parser


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )


def _project_root() -> Path:
    """Find project root (directory containing pyproject.toml or data/)."""
    # Walk up from CWD looking for pyproject.toml
    p = Path.cwd()
    for _ in range(10):
        if (p / "pyproject.toml").exists():
            return p
        if (p / "data").is_dir():
            return p
        parent = p.parent
        if parent == p:
            break
        p = parent
    return Path.cwd()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(args.log_level)

    basho = args.basho
    use_cache = args.raw_cache == "on"
    do_playoff = args.playoff == "on"
    force = args.force

    event_id = f"honbasho-{basho}"
    root = _project_root()
    fact_path = root / "data" / "fact" / "fact_bout_daily.csv"
    dim_path = root / "data" / "dim" / "dim_shikona_by_basho.csv"
    cache_dir = root / "data" / "raw" / event_id

    logger.info("Starting sumodata for basho=%s event_id=%s", basho, event_id)
    logger.info("Options: force=%s cache=%s playoff=%s", force, use_cache, do_playoff)

    start_time = time.time()

    try:
        all_bout_records: list[BoutRecord] = []
        last_day_html: str = ""

        # 1. Fetch & parse Results (d=1..15)
        for day in range(1, 16):
            url = results_url(basho, day)
            cache_path = cache_dir / f"results_d{day:02d}.html" if use_cache else None
            fetched_at = datetime.now(timezone.utc).isoformat()

            html = fetch_with_cache(url, cache_path, use_cache)
            if day == 15:
                last_day_html = html

            records = parse_results_page(
                html=html,
                event_id=event_id,
                event_type="honbasho_regular",
                is_regular="T",
                basho=basho,
                day=day,
                source_url=url,
                fetched_at=fetched_at,
            )
            all_bout_records.extend(records)
            logger.info("Day %d: %d bouts", day, len(records))

        # 2. Fetch & parse Banzuke
        banz_url = banzuke_url(basho)
        banz_cache = cache_dir / "banzuke.html" if use_cache else None
        banz_html = fetch_with_cache(banz_url, banz_cache, use_cache)
        shikona_records: list[ShikonaRecord] = parse_banzuke_page(
            banz_html, basho, banz_url,
        )

        # 3. Playoff detection & fetch
        if do_playoff and last_day_html:
            has_playoff = detect_playoff(last_day_html, basho)
            if has_playoff:
                playoff_event_id = f"honbasho-{basho}-playoff"
                playoff_url = results_url(basho, 16)
                playoff_cache = cache_dir / "playoff.html" if use_cache else None
                fetched_at = datetime.now(timezone.utc).isoformat()
                playoff_html = fetch_with_cache(
                    playoff_url, playoff_cache, use_cache,
                )
                playoff_records = parse_results_page(
                    html=playoff_html,
                    event_id=playoff_event_id,
                    event_type="honbasho_playoff",
                    is_regular="F",
                    basho=basho,
                    day=16,
                    source_url=playoff_url,
                    fetched_at=fetched_at,
                )
                all_bout_records.extend(playoff_records)
                logger.info("Playoff: %d bouts", len(playoff_records))
            else:
                logger.info("No playoff detected for basho %s", basho)

        # 4. CSV output — group by event_id and write each
        events: dict[str, list[BoutRecord]] = {}
        for r in all_bout_records:
            events.setdefault(r.event_id, []).append(r)

        for eid, records in events.items():
            update_fact_csv(records, fact_path, force, eid)

        update_dim_shikona_csv(shikona_records, dim_path, force, basho)

        # 5. Summary
        elapsed = time.time() - start_time
        logger.info("=== Summary ===")
        logger.info("Event: %s", event_id)
        logger.info("Fact rows: %d", len(all_bout_records))
        logger.info("Dim shikona rows: %d", len(shikona_records))
        logger.info("Elapsed: %.1fs", elapsed)

    except SumodataError as e:
        logger.error("Fatal error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)
