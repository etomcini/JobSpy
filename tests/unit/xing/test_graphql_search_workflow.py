import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from jobspy.model import ScraperInput
from jobspy.xing import Xing


def load_fixture() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "xing"
        / "graphql_page_last.json"
    )

    return json.loads(path.read_text(encoding="utf-8"))


def make_page(
    payload: dict[str, Any],
    start: int,
    end: int,
) -> dict[str, Any]:
    result = copy.deepcopy(payload)

    collection = payload["data"]["jobSearchByQuery"]["collection"]

    result["data"]["jobSearchByQuery"]["collection"] = collection[start:end]

    return result


def test_complete_graphql_workflow() -> None:
    payload = load_fixture()

    loader = Mock(
        side_effect=[
            make_page(payload, 0, 2),
            make_page(payload, 2, 3),
        ]
    )

    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
    )

    jobs = scraper.process_graphql_search(
        scraper_input,
        loader,
        page_size=2,
    )

    assert len(jobs) == 3

    assert [job.id for job in jobs] == [
        "xing-156968451",
        "xing-154535463",
        "xing-159116405",
    ]

    assert loader.call_count == 2


def test_graphql_workflow_with_offset() -> None:
    payload = load_fixture()

    loader = Mock(
        side_effect=[
            make_page(payload, 0, 2),
            make_page(payload, 2, 3),
        ]
    )

    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=1,
        results_wanted=2,
    )

    jobs = scraper.process_graphql_search(
        scraper_input,
        loader,
        page_size=2,
    )

    assert [job.id for job in jobs] == [
        "xing-154535463",
        "xing-159116405",
    ]


def test_workflow_collects_unique_jobs_across_pages() -> None:
    payload = load_fixture()

    first = make_page(payload, 0, 2)
    second = make_page(payload, 0, 2)
    third = make_page(payload, 2, 3)

    # The first two pages contain the same jobs.
    loader = Mock(
        side_effect=[
            first,
            second,
            third,
        ]
    )

    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
    )

    jobs = scraper.process_graphql_search(
        scraper_input,
        loader,
        page_size=2,
    )

    assert len(jobs) == 3

    assert [job.id for job in jobs] == [
        "xing-156968451",
        "xing-154535463",
        "xing-159116405",
    ]

    assert loader.call_count == 3


def test_workflow_recovers_partial_results() -> None:
    payload = load_fixture()

    loader = Mock(
        side_effect=[
            make_page(payload, 0, 2),
            ConnectionError("Connection lost"),
        ]
    )

    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=5,
    )

    jobs = scraper.process_graphql_search(
        scraper_input,
        loader,
        page_size=2,
        allow_partial=True,
    )

    assert len(jobs) == 2
    assert scraper.warnings
    assert "Connection lost" in scraper.warnings[0]
