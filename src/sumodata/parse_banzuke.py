"""Banzuke.aspx HTML parser."""

import logging
import re

from bs4 import BeautifulSoup, Tag

from sumodata.models import ShikonaRecord

logger = logging.getLogger(__name__)

_RID_PATTERN = re.compile(r"Rikishi\.aspx\?r=(\d+)")

# Caption text -> division name
_CAPTION_MAP = {
    "Makuuchi Banzuke": "Makuuchi",
    "Juryo Banzuke": "Juryo",
    "Makushita Banzuke": "Makushita",
    "Sandanme Banzuke": "Sandanme",
    "Jonidan Banzuke": "Jonidan",
    "Jonokuchi Banzuke": "Jonokuchi",
}

# Skip these divisions
_SKIP_DIVISIONS = {"Mae-zumo", "Banzuke-gai"}


def parse_banzuke_page(
    html: str,
    basho: str,
    source_url: str,
) -> list[ShikonaRecord]:
    """Parse a Banzuke page and return ShikonaRecords."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[ShikonaRecord] = []

    for table in soup.find_all("table", class_="banzuke"):
        caption = table.find("caption")
        if not caption:
            continue
        caption_text = caption.get_text(strip=True)

        # Skip non-standard divisions
        if any(skip in caption_text for skip in _SKIP_DIVISIONS):
            continue

        division = _CAPTION_MAP.get(caption_text, "")
        if not division:
            # Try partial match
            for key, val in _CAPTION_MAP.items():
                if val in caption_text:
                    division = val
                    break
            if not division:
                logger.debug("Skipping unknown banzuke table: %s", caption_text)
                continue

        tbody = table.find("tbody")
        if not tbody:
            continue

        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) != 5:
                continue

            # cells: [Result, East shikona, Rank, West shikona, Result]
            rank_cell = cells[2]
            rank_text = rank_cell.get_text(strip=True)

            # East side (cells[1])
            east_record = _extract_rikishi(
                cells[1], "e", rank_text, division, basho, source_url,
            )
            if east_record:
                records.append(east_record)

            # West side (cells[3])
            west_record = _extract_rikishi(
                cells[3], "w", rank_text, division, basho, source_url,
            )
            if west_record:
                records.append(west_record)

    logger.info("Parsed %d rikishi from banzuke (%s)", len(records), basho)
    return records


def _extract_rikishi(
    cell: Tag,
    side: str,  # "e" or "w"
    rank_text: str,
    division: str,
    basho: str,
    source_url: str,
) -> ShikonaRecord | None:
    """Extract a rikishi from a shikona cell."""
    # Skip empty cells
    if "emptycell" in cell.get("class", []):
        return None

    link = cell.find("a", href=_RID_PATTERN)
    if not link:
        return None

    # Extract rid
    m = _RID_PATTERN.search(link["href"])
    if not m:
        return None
    rid = int(m.group(1))

    # Extract shikona: title attribute first field (Japanese name), fallback to link text
    shikona = ""
    title = link.get("title", "")
    if title:
        shikona = title.split(",")[0].strip()
    if not shikona:
        shikona = link.get_text(strip=True)

    # Construct full rank
    rank = f"{rank_text}{side}" if rank_text else ""

    return ShikonaRecord(
        basho=basho,
        rid=rid,
        shikona_at_basho=shikona,
        source_url=source_url,
        division=division,
        rank=rank,
    )
