"""Results.aspx HTML parser."""

import logging
import re

from bs4 import BeautifulSoup, Tag

from sumodata.models import BoutRecord

logger = logging.getLogger(__name__)

_RID_PATTERN = re.compile(r"Rikishi\.aspx\?r=(\d+)")


def parse_results_page(
    html: str,
    event_id: str,
    event_type: str,
    is_regular: str,
    basho: str,
    day: int,
    source_url: str,
    fetched_at: str,
) -> list[BoutRecord]:
    """Parse a Results page and return BoutRecords."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[BoutRecord] = []
    source_row_index = 0

    # Find all division tables
    for table in soup.find_all("table", class_="tk_table"):
        division = _extract_division(table)
        if not division:
            continue

        bout_no = 0
        # Each bout row has 5 cells: tk_kekka, tk_east, tk_kim, tk_west, tk_kekka
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) != 5:
                continue

            # Skip header rows (tk_kaku)
            if cells[0].get("class") and "tk_kaku" in cells[0].get("class", []):
                continue

            source_row_index += 1
            bout_no += 1

            try:
                record = _parse_bout_row(
                    cells, division, bout_no, source_row_index,
                    event_id, event_type, is_regular, basho, day,
                    source_url, fetched_at,
                )
                records.append(record)
                logger.debug(
                    "  bout %s #%d: %d vs %d -> %s by %s [%s]",
                    division, bout_no, record.east_rid, record.west_rid,
                    record.winner_side, record.kimarite, record.result_type,
                )
            except Exception as e:
                logger.warning(
                    "Failed to parse bout row %d in %s: %s",
                    source_row_index, division, e,
                )
                records.append(BoutRecord(
                    event_id=event_id, event_type=event_type,
                    is_regular=is_regular, basho=basho, day=day,
                    division=division, bout_no=bout_no,
                    east_rid=0, west_rid=0, winner_side="",
                    kimarite="", east_rank="", west_rank="",
                    result_type="unknown", note=str(e),
                    source_url=source_url,
                    source_row_index=source_row_index,
                    fetched_at=fetched_at,
                ))

    # Division-level and exception summary
    div_counts: dict[str, int] = {}
    exception_count = 0
    for r in records:
        div_counts[r.division] = div_counts.get(r.division, 0) + 1
        if r.result_type in ("fusen", "kyujo", "unknown"):
            exception_count += 1

    logger.info(
        "Parsed %d bouts from day %d (%s): %s, exceptions=%d",
        len(records), day, event_id,
        ", ".join(f"{d}={n}" for d, n in div_counts.items()),
        exception_count,
    )
    return records


def _extract_division(table: Tag) -> str | None:
    """Extract division name from a tk_table."""
    header = table.find("td", class_="tk_kaku")
    if not header:
        return None
    text = header.get_text(strip=True)
    # Division names in the header text
    for div_name in [
        "Makuuchi", "Juryo", "Makushita",
        "Sandanme", "Jonidan", "Jonokuchi",
    ]:
        if div_name in text:
            return div_name
    return text


def _parse_bout_row(
    cells: list[Tag],
    division: str,
    bout_no: int,
    source_row_index: int,
    event_id: str,
    event_type: str,
    is_regular: str,
    basho: str,
    day: int,
    source_url: str,
    fetched_at: str,
) -> BoutRecord:
    """Parse a single bout row (5 cells)."""
    east_kekka = cells[0]
    east_cell = cells[1]
    kim_cell = cells[2]
    west_cell = cells[3]
    west_kekka = cells[4]

    east_rid = _extract_rid(east_cell)
    west_rid = _extract_rid(west_cell)
    east_rank = _extract_rank(east_cell)
    west_rank = _extract_rank(west_cell)
    kimarite = _extract_kimarite(kim_cell)

    east_result = _detect_result(east_kekka)
    west_result = _detect_result(west_kekka)

    winner_side = ""
    if east_result in ("shiro", "fusensho"):
        winner_side = "E"
    elif west_result in ("shiro", "fusensho"):
        winner_side = "W"

    result_type = _determine_result_type(
        east_result, west_result, kimarite, east_rid, west_rid, day,
    )

    if result_type == "fusen":
        kimarite = "fusen"

    note = ""
    if result_type == "kyujo":
        kimarite = ""
        winner_side = ""

    return BoutRecord(
        event_id=event_id, event_type=event_type,
        is_regular=is_regular, basho=basho, day=day,
        division=division, bout_no=bout_no,
        east_rid=east_rid, west_rid=west_rid,
        winner_side=winner_side, kimarite=kimarite,
        east_rank=east_rank, west_rank=west_rank,
        result_type=result_type, note=note,
        source_url=source_url,
        source_row_index=source_row_index,
        fetched_at=fetched_at,
    )


def _extract_rid(cell: Tag) -> int:
    """Extract rikishi ID from a cell containing a Rikishi.aspx link."""
    link = cell.find("a", href=_RID_PATTERN)
    if link:
        m = _RID_PATTERN.search(link["href"])
        if m:
            return int(m.group(1))
    return 0


def _extract_rank(cell: Tag) -> str:
    """Extract rank from <font size='1'> in a rikishi cell."""
    font = cell.find("font", attrs={"size": "1"})
    if font:
        text = font.get_text(strip=True)
        if text:
            return text
    return ""


def _extract_kimarite(cell: Tag) -> str:
    """Extract kimarite from the tk_kim cell.

    Structure: <font size="1"><br/></font> kimarite <br/> ...
    The kimarite text is a NavigableString after the first <font> tag.
    """
    # Find all direct children and look for text after the first font/br
    font_tags = cell.find_all("font", attrs={"size": "1"})
    if font_tags:
        # Get the text node right after the first font tag
        first_font = font_tags[0]
        sibling = first_font.next_sibling
        while sibling:
            if isinstance(sibling, str):
                text = sibling.strip()
                if text:
                    return text
            elif isinstance(sibling, Tag) and sibling.name == "br":
                # Skip br tags, look at next sibling
                pass
            else:
                break
            sibling = sibling.next_sibling

    # Fallback: get all text and take first non-empty line
    text = cell.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        return lines[0]
    return ""


def _detect_result(kekka_cell: Tag) -> str:
    """Detect result from a tk_kekka cell's img src."""
    img = kekka_cell.find("img")
    if not img:
        return ""
    src = img.get("src", "")
    if "hoshi_shiro" in src:
        return "shiro"
    if "hoshi_kuro" in src:
        return "kuro"
    if "hoshi_fusensho" in src or "fusensho" in src:
        return "fusensho"
    if "hoshi_fusenpai" in src or "fusenpai" in src:
        return "fusenpai"
    return ""


def _determine_result_type(
    east_result: str,
    west_result: str,
    kimarite: str,
    east_rid: int,
    west_rid: int,
    day: int,
) -> str:
    """Determine the result_type for a bout."""
    # fusen detection
    if east_result in ("fusensho", "fusenpai") or west_result in ("fusensho", "fusenpai"):
        return "fusen"
    if kimarite.lower() == "fusen":
        return "fusen"

    # kyujo detection: no rikishi links
    if east_rid == 0 or west_rid == 0:
        return "kyujo"

    # playoff
    if day == 16:
        return "playoff"

    # normal
    if east_result or west_result:
        return "normal"

    return "unknown"


def detect_playoff(html: str, basho: str) -> bool:
    """Detect if a playoff exists by looking for d=16 link in daytable."""
    soup = BeautifulSoup(html, "html.parser")
    # Look for links containing d=16 in the sidebar
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if f"b={basho}" in href and "d=16" in href:
            text = link.get_text(strip=True)
            if "playoff" in text.lower() or "Playoffs" in text:
                logger.info("Playoff detected for basho %s", basho)
                return True
    return False
