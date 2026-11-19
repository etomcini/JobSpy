from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from jobspy.model import ScraperInput
from jobspy.xing.pagination import iter_graphql_pages
from jobspy.xing.search_result import SearchStatus
from jobspy.xing.search_workflow import run_graphql_search


def make_job(identifier: int) -> dict[str, object]:
    return {
        "jobDetail": {
            "id": f"{identifier}.abc",
            "url": (f"https://www.xing.com/jobs/python-developer-{identifier}"),
            "title": f"Python Developer {identifier}",
            "companyInfo": {
                "companyNameOverride": "Example Company",
            },
            "location": {
                "city": "Berlin",
            },
        }
    }


def make_page(
    identifiers: list[int],
    *,
    total: int = 100,
) -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": total,
                "collection": [make_job(identifier) for identifier in identifiers],
            }
        }
    }


def make_loader(
    pages: list[dict[str, Any]],
) -> Mock:
    return Mock(side_effect=pages)


def make_input(
    *,
    offset: int = 0,
    results_wanted: int = 5,
    fetch_description: bool = False,
) -> ScraperInput:
    return ScraperInput(
        site_name=["xing"],
        search_term="Python Developer",
        location="Berlin",
        offset=offset,
        results_wanted=results_wanted,
        fetch_description=fetch_description,
    )


def test_multi_page_search_with_duplicates() -> None:
    loader = make_loader(
        [
            make_page([1, 2, 3]),
            make_page([3, 4, 5]),
            make_page([5, 6, 7]),
        ]
    )

    result = run_graphql_search(
        make_input(results_wanted=5),
        loader,
        page_size=3,
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.count == 5

    assert [job.id for job in result.jobs] == [
        "xing-1",
        "xing-2",
        "xing-3",
        "xing-4",
        "xing-5",
    ]

    assert result.metrics.pages_fetched == 2
    assert result.metrics.raw_jobs_seen == 6
    assert result.metrics.unique_jobs_seen == 5


def test_offset_and_result_limit() -> None:
    loader = make_loader(
        [
            make_page([1, 2, 3]),
            make_page([4, 5, 6]),
            make_page([7, 8, 9]),
        ]
    )

    result = run_graphql_search(
        make_input(
            offset=2,
            results_wanted=4,
        ),
        loader,
        page_size=3,
    )

    assert result.status == SearchStatus.COMPLETED

    assert [job.id for job in result.jobs] == [
        "xing-3",
        "xing-4",
        "xing-5",
        "xing-6",
    ]

    assert result.metrics.unique_jobs_seen == 6


def test_partial_recovery_after_loader_failure() -> None:
    loader = Mock(
        side_effect=[
            make_page([1, 2, 3]),
            RuntimeError("Connection interrupted"),
        ]
    )

    result = run_graphql_search(
        make_input(results_wanted=6),
        loader,
        page_size=3,
        allow_partial=True,
    )

    assert result.status == SearchStatus.PARTIAL
    assert result.count == 3
    assert result.metrics.pages_fetched == 1
    assert result.warnings


def test_loader_failure_without_partial_recovery() -> None:
    from jobspy.xing.exceptions import XingPageLoadError

    loader = Mock(
        side_effect=[
            make_page([1, 2, 3]),
            RuntimeError("Connection interrupted"),
        ]
    )

    with pytest.raises(XingPageLoadError):
        run_graphql_search(
            make_input(results_wanted=6),
            loader,
            page_size=3,
            allow_partial=False,
        )


def test_max_pages_limit() -> None:
    loader = make_loader(
        [
            make_page([1, 2, 3]),
            make_page([4, 5, 6]),
        ]
    )

    result = run_graphql_search(
        make_input(results_wanted=20),
        loader,
        page_size=3,
        max_pages=2,
    )

    assert result.status == SearchStatus.LIMIT_REACHED
    assert result.metrics.pages_fetched == 2
    assert result.count == 6
    assert result.warnings


def test_raw_iterator_and_search_have_same_jobs() -> None:
    pages = [
        make_page([1, 2, 3]),
        make_page([3, 4, 5]),
    ]

    raw_pages = list(
        iter_graphql_pages(
            make_loader(pages),
            required_results=5,
            page_size=3,
        )
    )

    result = run_graphql_search(
        make_input(results_wanted=5),
        make_loader(pages),
        page_size=3,
    )

    assert len(raw_pages) == 2
    assert result.count == 5

    raw_ids = {
        item["jobDetail"]["id"].split(".")[0]
        for page in raw_pages
        for item in page["data"]["jobSearchByQuery"]["collection"]
    }

    result_ids = {
        job.id.removeprefix("xing-") for job in result.jobs if job.id is not None
    }

    assert raw_ids == result_ids
