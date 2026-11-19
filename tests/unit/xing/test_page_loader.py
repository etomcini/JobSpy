from typing import Any
from unittest.mock import Mock

import pytest

from jobspy.xing.page_loader import iter_graphql_pages


def make_payload(
    count: int,
    *,
    total: int = -1,
) -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": total,
                "collection": [{} for _ in range(count)],
            }
        }
    }


def test_loads_multiple_pages() -> None:
    loader = Mock(
        side_effect=[
            make_payload(20),
            make_payload(20),
            make_payload(5),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=50,
            page_size=20,
        )
    )

    assert len(pages) == 3
    assert loader.call_args_list == [
        ((0, 20),),
        ((20, 20),),
        ((40, 20),),
    ]


def test_stops_at_requested_count() -> None:
    payload = {
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
                    for number in range(20)
                ],
            }
        }
    }

    loader = Mock(return_value=payload)

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=20,
        )
    )

    assert len(pages) == 1
    loader.assert_called_once_with(0, 20)


def test_stops_on_empty_page() -> None:
    loader = Mock(
        side_effect=[
            make_payload(20),
            make_payload(0),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=100,
        )
    )

    assert len(pages) == 2


def test_stops_on_exact_total() -> None:
    loader = Mock(
        side_effect=[
            make_payload(20, total=25),
            make_payload(5, total=25),
        ]
    )

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=100,
        )
    )

    assert len(pages) == 2


def test_max_pages_safeguard() -> None:
    loader = Mock(return_value=make_payload(20))

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=1000,
            max_pages=3,
        )
    )

    assert len(pages) == 3
    assert loader.call_count == 3


def test_zero_results_makes_no_requests() -> None:
    loader = Mock()

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=0,
        )
    )

    assert pages == []
    loader.assert_not_called()


@pytest.mark.parametrize(
    "required,page_size,max_pages",
    [
        (-1, 20, 50),
        (10, 0, 50),
        (10, 20, 0),
    ],
)
def test_invalid_configuration(
    required: int,
    page_size: int,
    max_pages: int,
) -> None:
    with pytest.raises(ValueError):
        list(
            iter_graphql_pages(
                Mock(),
                required_results=required,
                page_size=page_size,
                max_pages=max_pages,
            )
        )


def test_invalid_jobs_do_not_count_toward_limit() -> None:
    loader = Mock(return_value=make_payload(20))

    pages = list(
        iter_graphql_pages(
            loader,
            required_results=20,
            page_size=20,
            max_pages=3,
        )
    )

    assert len(pages) == 3
    assert loader.call_count == 3
