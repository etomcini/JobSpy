from typing import Any
from unittest.mock import Mock

import pytest

from jobspy.model import ScraperInput
from jobspy.xing import Xing
from jobspy.xing.exceptions import XingPageLoadError
from jobspy.xing.search_result import SearchStatus


def make_payload(numbers: list[int]) -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": -1,
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


def test_both_methods_return_same_jobs() -> None:
    pages = [
        make_payload([1, 2]),
        make_payload([3, 4]),
    ]

    scraper = Xing()
    scraper_input = make_input(wanted=4)

    jobs = scraper.process_graphql_search(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    result = scraper.search_with_metadata(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    assert [job.id for job in jobs] == [job.id for job in result.jobs]
    assert result.status == SearchStatus.COMPLETED


def test_both_methods_apply_same_offset() -> None:
    pages = [
        make_payload([1, 2]),
        make_payload([3, 4]),
    ]

    scraper = Xing()
    scraper_input = make_input(
        wanted=2,
        offset=1,
    )

    jobs = scraper.process_graphql_search(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    result = scraper.search_with_metadata(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    assert [job.id for job in jobs] == [
        "xing-2",
        "xing-3",
    ]

    assert [job.id for job in result.jobs] == [
        "xing-2",
        "xing-3",
    ]


def test_both_methods_deduplicate() -> None:
    pages = [
        make_payload([1, 2]),
        make_payload([2, 3]),
    ]

    scraper = Xing()
    scraper_input = make_input(wanted=3)

    jobs = scraper.process_graphql_search(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    result = scraper.search_with_metadata(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    assert [job.id for job in jobs] == [
        "xing-1",
        "xing-2",
        "xing-3",
    ]

    assert result.metrics.unique_jobs_seen == 3


def test_partial_recovery_returns_same_jobs() -> None:
    scraper_input = make_input(wanted=5)

    def make_loader() -> Mock:
        return Mock(
            side_effect=[
                make_payload([1, 2]),
                ConnectionError("Connection lost"),
            ]
        )

    jobs = Xing().process_graphql_search(
        scraper_input,
        make_loader(),
        page_size=2,
        allow_partial=True,
    )

    result = Xing().search_with_metadata(
        scraper_input,
        make_loader(),
        page_size=2,
        allow_partial=True,
    )

    assert [job.id for job in jobs] == [job.id for job in result.jobs]
    assert result.status == SearchStatus.PARTIAL
    assert result.count == 2


def test_failure_raises_by_default() -> None:
    scraper_input = make_input(wanted=5)

    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            ConnectionError("Connection lost"),
        ]
    )

    with pytest.raises(XingPageLoadError):
        Xing().process_graphql_search(
            scraper_input,
            loader,
            page_size=2,
        )


def test_legacy_method_delegates_to_metadata_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraper = Xing()
    scraper_input = make_input(wanted=2)

    expected_jobs = scraper.search_with_metadata(
        scraper_input,
        Mock(return_value=make_payload([1, 2])),
        page_size=2,
    ).jobs

    mocked = Mock()
    mocked.return_value.jobs = expected_jobs

    monkeypatch.setattr(
        scraper,
        "search_with_metadata",
        mocked,
    )

    jobs = scraper.process_graphql_search(
        scraper_input,
        Mock(),
        page_size=2,
    )

    assert jobs == expected_jobs
    mocked.assert_called_once()
