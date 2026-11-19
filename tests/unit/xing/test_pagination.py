from pathlib import Path

import pytest

from jobspy.model import ScraperInput
from jobspy.xing import Xing
from jobspy.xing.util import parse_search_results


@pytest.fixture
def search_html() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "xing"
        / "search_results_full.html"
    )
    return path.read_text(encoding="utf-8")


@pytest.fixture
def scraper() -> Xing:
    return Xing()


def test_multiple_pages(
    scraper: Xing,
    search_html: str,
) -> None:
    jobs = parse_search_results(search_html)

    first_page = search_html
    second_page = search_html

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=30,
    )

    results = scraper.process_pages(
        scraper_input,
        [first_page, second_page],
    )

    assert len(results) == len(jobs)
    assert len({job.id for job in results}) == len(results)


def test_duplicate_pages(
    scraper: Xing,
    search_html: str,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=40,
    )

    results = scraper.process_pages(
        scraper_input,
        [search_html, search_html, search_html],
    )

    assert len(results) == 20


def test_offset_across_pages(
    scraper: Xing,
    search_html: str,
) -> None:
    expected = parse_search_results(search_html)

    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=15,
        results_wanted=5,
    )

    results = scraper.process_pages(
        scraper_input,
        [search_html, search_html],
    )

    assert [job.id for job in results] == [job.id for job in expected[15:20]]


def test_stops_loading_when_limit_reached(
    scraper: Xing,
    search_html: str,
) -> None:
    consumed = 0

    def pages():
        nonlocal consumed

        for _ in range(10):
            consumed += 1
            yield search_html

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=5,
    )

    results = scraper.process_pages(
        scraper_input,
        pages(),
    )

    assert len(results) == 5
    assert consumed == 1


def test_empty_pages(
    scraper: Xing,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=10,
    )

    results = scraper.process_pages(
        scraper_input,
        ["<html></html>", "<html></html>"],
    )

    assert results == []


def test_offset_beyond_available_results(
    scraper: Xing,
    search_html: str,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=25,
        results_wanted=5,
    )

    results = scraper.process_pages(
        scraper_input,
        [search_html],
    )

    assert results == []


def test_combines_distinct_pages(
    scraper: Xing,
    search_html: str,
) -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(search_html, "html.parser")

    cards = soup.select('article[data-testid="job-search-result"]')

    assert len(cards) == 20

    first_page = "".join(str(card) for card in cards[:10])

    second_page = "".join(str(card) for card in cards[10:])

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=20,
    )

    results = scraper.process_pages(
        scraper_input,
        [first_page, second_page],
    )

    expected = parse_search_results(search_html)

    assert len(results) == 20
    assert [job.id for job in results] == [job.id for job in expected]


def test_offset_crosses_page_boundary(
    scraper: Xing,
    search_html: str,
) -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(search_html, "html.parser")

    cards = soup.select('article[data-testid="job-search-result"]')

    first_page = "".join(str(card) for card in cards[:10])

    second_page = "".join(str(card) for card in cards[10:])

    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=8,
        results_wanted=5,
    )

    results = scraper.process_pages(
        scraper_input,
        [first_page, second_page],
    )

    expected = parse_search_results(search_html)[8:13]

    assert [job.id for job in results] == [job.id for job in expected]
