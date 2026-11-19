import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from jobspy.model import ScraperInput
from jobspy.xing import Xing


@pytest.fixture
def graphql_payload() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "xing"
        / "graphql_page_last.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def scraper() -> Xing:
    return Xing()


def make_page(
    original: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    page = copy.deepcopy(original)
    page["data"]["jobSearchByQuery"]["collection"] = items
    return page


def test_single_graphql_page(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=10,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [graphql_payload],
    )

    assert len(jobs) == 3


def test_duplicate_graphql_pages(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=10,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [graphql_payload, graphql_payload],
    )

    assert len(jobs) == 3
    assert len({job.id for job in jobs}) == 3


def test_graphql_result_limit(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=2,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [graphql_payload],
    )

    assert len(jobs) == 2


def test_graphql_offset(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=1,
        results_wanted=2,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [graphql_payload],
    )

    assert len(jobs) == 2
    assert jobs[0].id == "xing-154535463"
    assert jobs[1].id == "xing-159116405"


def test_graphql_empty_pages(
    scraper: Xing,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=10,
    )

    assert (
        scraper.process_graphql_pages(
            scraper_input,
            [],
        )
        == []
    )


def test_graphql_stops_when_limit_reached(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    consumed = 0

    def pages():
        nonlocal consumed

        for _ in range(10):
            consumed += 1
            yield graphql_payload

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=2,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        pages(),
    )

    assert len(jobs) == 2
    assert consumed == 1


def test_graphql_distinct_pages(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    collection = graphql_payload["data"]["jobSearchByQuery"]["collection"]

    first_page = make_page(
        graphql_payload,
        collection[:1],
    )
    second_page = make_page(
        graphql_payload,
        collection[1:],
    )

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [first_page, second_page],
    )

    assert len(jobs) == 3
    assert [job.id for job in jobs] == [
        "xing-156968451",
        "xing-154535463",
        "xing-159116405",
    ]


def test_graphql_offset_across_pages(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    collection = graphql_payload["data"]["jobSearchByQuery"]["collection"]

    first_page = make_page(
        graphql_payload,
        collection[:1],
    )
    second_page = make_page(
        graphql_payload,
        collection[1:],
    )

    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=1,
        results_wanted=2,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [first_page, second_page],
    )

    assert [job.id for job in jobs] == [
        "xing-154535463",
        "xing-159116405",
    ]


def test_graphql_duplicates_across_pages(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    collection = graphql_payload["data"]["jobSearchByQuery"]["collection"]

    first_page = make_page(
        graphql_payload,
        collection[:2],
    )
    second_page = make_page(
        graphql_payload,
        collection[1:],
    )

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [first_page, second_page],
    )

    assert [job.id for job in jobs] == [
        "xing-156968451",
        "xing-154535463",
        "xing-159116405",
    ]


def test_graphql_detail_loader_failure(
    scraper: Xing,
    graphql_payload: dict[str, Any],
) -> None:
    loader = Mock(side_effect=RuntimeError("Detail unavailable"))

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=2,
        fetch_description=True,
    )

    jobs = scraper.process_graphql_pages(
        scraper_input,
        [graphql_payload],
        detail_loader=loader,
    )

    assert len(jobs) == 2
    assert loader.call_count == 2
    assert scraper.warnings
