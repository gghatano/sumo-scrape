"""Shared pytest fixtures for loading HTML test fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def results_sample_html() -> str:
    return (FIXTURES_DIR / "results_sample.html").read_text(encoding="utf-8")


@pytest.fixture()
def results_no_playoff_html() -> str:
    return (FIXTURES_DIR / "results_no_playoff.html").read_text(encoding="utf-8")


@pytest.fixture()
def banzuke_sample_html() -> str:
    return (FIXTURES_DIR / "banzuke_sample.html").read_text(encoding="utf-8")
