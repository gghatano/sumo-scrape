"""Data models."""

from dataclasses import dataclass


@dataclass
class BoutRecord:
    event_id: str
    event_type: str  # honbasho_regular / honbasho_playoff
    is_regular: str  # "T" / "F"
    basho: str  # YYYYMM
    day: int
    division: str
    bout_no: int
    east_rid: int
    west_rid: int
    winner_side: str  # "E" / "W" / ""
    kimarite: str
    east_rank: str
    west_rank: str
    result_type: str  # normal / fusen / kyujo / playoff / unknown
    note: str
    source_url: str
    source_row_index: int
    fetched_at: str  # ISO format


@dataclass
class ShikonaRecord:
    basho: str
    rid: int
    shikona_at_basho: str
    source_url: str
    division: str
    rank: str


@dataclass
class RikishiRecord:
    rid: int
    current_shikona: str
    updated_at: str
    source_url: str
