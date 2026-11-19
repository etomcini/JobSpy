from typing import Any
from unittest.mock import Mock

from jobspy.xing.page_loader import iter_graphql_pages


def make_job(number: int) -> dict[str, Any]:
    return {
        "jobDetail": {
            "id": f"{number}.abc",
            "url": f"https://www.xing.com/jobs/test-job-{number}",
            "title": f"Job {number}",
            "companyInfo": {
                "companyNameOverride": "Test Company",
            },
        }
    }


def make_payload(
    job_numbers: list[int],
    *,
    total: int = -1,
) -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": total,
                "collection": [make_job(number) for number in job_numbers],
            }
        }
    }


def test_duplicates_do_not_count_toward_limit() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([2, 3]),
            make_payload([4, 5]),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=5,
            page_size=2,
        )
    )

    assert len(pages) == 3
    assert loader.call_args_list == [
        ((0, 2),),
        ((2, 2),),
        ((4, 2),),
    ]


def test_all_duplicate_page_continues() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([1, 2]),
            make_payload([3, 4]),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=4,
            page_size=2,
        )
    )

    assert len(pages) == 3


def test_exact_total_stops_despite_duplicates() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2], total=4),
            make_payload([1, 2], total=4),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=4,
            page_size=2,
        )
    )

    assert len(pages) == 2


def test_max_pages_stops_repeated_results() -> None:
    loader = Mock(return_value=make_payload([1, 2]))

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=10,
            page_size=2,
            max_pages=3,
        )
    )

    assert len(pages) == 3
    assert loader.call_count == 3


def test_empty_page_stops() -> None:
    loader = Mock(
        side_effect=[
            make_payload([1, 2]),
            make_payload([]),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=5,
            page_size=2,
        )
    )

    assert len(pages) == 2
