from typing import Any
from unittest.mock import Mock

import pytest

from jobspy.model import ScraperInput
from jobspy.xing import Xing
from jobspy.xing.exceptions import XingPageLoadError
from jobspy.xing.search_result import SearchStatus


def make_payload(
    numbers: list[int],
    total: int = -1,
) -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": total,
                "collection": [
                    {
                        "jobDetail": {
                            "id": f"{number}.abc",
                            "url": (f"https://www.xing.com/jobs/test-job-{number}"),
                            "title": f"Job {number}",
                            "companyInfo": {
                                "companyNameOverride": "Test Company",
                            },
                        }
                    }
                    for number in numbers
                ],
            }
        }
    }


def make_input(
    *,
    wanted: int,
    offset: int = 0,
) -> ScraperInput:
    return ScraperInput(
        site_name=["xing"],
        results_wanted=wanted,
        offset=offset,
    )


def test_completed_search() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([3, 4]),
        ]
    )

    result = Xing().search_with_metadata(
        make_input(wanted=4),
        loader,
        page_size=2,
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.count == 4
    assert result.metrics.pages_fetched == 2
    assert result.metrics.raw_jobs_seen == 4
    assert result.metrics.unique_jobs_seen == 4
    assert result.warnings == []


def test_exhausted_search() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([3]),
        ]
    )

    result = Xing().search_with_metadata(
        make_input(wanted=10),
        loader,
        page_size=2,
    )

    assert result.status == SearchStatus.EXHAUSTED
    assert result.count == 3
    assert result.metrics.pages_fetched == 2


def test_offset_applied() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([3, 4]),
        ]
    )

    result = Xing().search_with_metadata(
        make_input(wanted=2, offset=1),
        loader,
        page_size=2,
    )

    assert [job.id for job in result.jobs] == [
        "xing-2",
        "xing-3",
    ]


def test_duplicate_metrics() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([2, 3]),
        ]
    )

    result = Xing().search_with_metadata(
        make_input(wanted=3),
        loader,
        page_size=2,
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.metrics.raw_jobs_seen == 4
    assert result.metrics.unique_jobs_seen == 3


def test_partial_recovery() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            ConnectionError("Connection lost"),
        ]
    )

    scraper = Xing()

    result = scraper.search_with_metadata(
        make_input(wanted=5),
        loader,
        page_size=2,
        allow_partial=True,
    )

    assert result.status == SearchStatus.PARTIAL
    assert result.count == 2
    assert result.warnings
    assert scraper.warnings


def test_failure_raises_by_default() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            ConnectionError("Connection lost"),
        ]
    )

    with pytest.raises(XingPageLoadError):
        Xing().search_with_metadata(
            make_input(wanted=5),
            loader,
            page_size=2,
        )


def test_max_pages_status() -> None:
    loader = Mock(return_value=make_payload([1, 2]))

    result = Xing().search_with_metadata(
        make_input(wanted=10),
        loader,
        page_size=2,
        max_pages=2,
    )

    assert result.status == SearchStatus.LIMIT_REACHED
    assert result.metrics.pages_fetched == 2
    assert result.warnings


def test_no_progress_status() -> None:
    loader = Mock(return_value=make_payload([1, 2]))

    result = Xing().search_with_metadata(
        make_input(wanted=10),
        loader,
        page_size=2,
        max_no_progress_pages=2,
    )

    assert result.status == SearchStatus.LIMIT_REACHED
    assert result.metrics.pages_fetched == 3


def test_zero_requested_results_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(
        ValidationError,
        match="results_wanted",
    ):
        make_input(wanted=0)
