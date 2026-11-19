from typing import Any
from unittest.mock import Mock

import pytest

from jobspy.xing.exceptions import (
    XingGraphQLError,
    XingPageLoadError,
)
from jobspy.xing.page_loader import iter_graphql_pages


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


def test_first_page_failure_raises() -> None:
    loader = Mock(side_effect=ConnectionError("Connection failed"))

    with pytest.raises(XingPageLoadError):
        list(
            iter_graphql_pages(
                loader,
                required_results=10,
            )
        )


def test_later_failure_raises_by_default() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            ConnectionError("Connection lost"),
        ]
    )

    with pytest.raises(XingPageLoadError):
        list(
            iter_graphql_pages(
                loader,
                required_results=10,
                page_size=2,
            )
        )


def test_partial_recovery_after_loader_failure() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            ConnectionError("Connection lost"),
        ]
    )

    warnings: list[str] = []

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=10,
            page_size=2,
            allow_partial=True,
            on_warning=warnings.append,
        )
    )

    assert len(pages) == 1
    assert len(warnings) == 1
    assert "offset 2" in warnings[0]


def test_partial_not_allowed_without_valid_jobs() -> None:
    loader = Mock(
        side_effect=[
            make_payload([]),
            ConnectionError("Connection lost"),
        ]
    )

    # Empty pages terminate normally, so test an invalid-job
    # full page instead.
    invalid_page = {
        "data": {
            "jobSearchByQuery": {
                "total": -1,
                "collection": [{}, {}],
            }
        }
    }

    loader = Mock(
        side_effect=[
            invalid_page,
            ConnectionError("Connection lost"),
        ]
    )

    with pytest.raises(XingPageLoadError):
        list(
            iter_graphql_pages(
                loader,
                required_results=10,
                page_size=2,
                allow_partial=True,
            )
        )


def test_graphql_error_raises() -> None:
    loader = Mock(
        return_value={
            "errors": [{"message": "Invalid query"}],
            "data": None,
        }
    )

    with pytest.raises(XingGraphQLError):
        list(
            iter_graphql_pages(
                loader,
                required_results=10,
            )
        )


def test_malformed_response_raises() -> None:
    loader = Mock(return_value={"data": {}})

    with pytest.raises(XingGraphQLError):
        list(
            iter_graphql_pages(
                loader,
                required_results=10,
            )
        )


def test_no_progress_stops_after_three_pages() -> None:
    loader = Mock(return_value=make_payload([1, 2]))

    warnings: list[str] = []

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=10,
            page_size=2,
            max_no_progress_pages=3,
            on_warning=warnings.append,
        )
    )

    # First page has progress, next three do not.
    assert len(pages) == 4
    assert loader.call_count == 4
    assert any("without new valid jobs" in w for w in warnings)


def test_max_pages_warning() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([3, 4]),
        ]
    )

    warnings: list[str] = []

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=10,
            page_size=2,
            max_pages=2,
            on_warning=warnings.append,
        )
    )

    assert len(pages) == 2
    assert any("max_pages=2" in w for w in warnings)


@pytest.mark.parametrize(
    "max_no_progress_pages",
    [0, -1],
)
def test_invalid_no_progress_limit(
    max_no_progress_pages: int,
) -> None:
    with pytest.raises(ValueError):
        list(
            iter_graphql_pages(
                Mock(),
                required_results=10,
                max_no_progress_pages=max_no_progress_pages,
            )
        )
