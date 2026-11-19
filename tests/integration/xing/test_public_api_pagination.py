from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pandas as pd

from jobspy import scrape_jobs
from jobspy.model import JobPost
from jobspy.xing import Xing


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


def run_search(
    loader: Mock,
    *,
    offset: int = 0,
    results_wanted: int = 5,
) -> pd.DataFrame:
    with patch.object(
        Xing,
        "page_loader_factory",
        return_value=loader,
    ):
        return scrape_jobs(
            site_name=["xing"],
            search_term="Python Developer",
            location="Berlin",
            offset=offset,
            results_wanted=results_wanted,
            verbose=0,
        )


def test_multiple_pages_are_combined() -> None:
    loader = Mock(
        side_effect=[
            make_page(list(range(1, 21))),
            make_page(list(range(21, 41))),
        ]
    )

    result = run_search(
        loader,
        results_wanted=25,
    )

    assert len(result) == 25

    assert set(result["id"]) == {f"xing-{identifier}" for identifier in range(1, 26)}

    assert loader.call_count == 2


def test_duplicates_are_removed_across_pages() -> None:
    loader = Mock(
        side_effect=[
            make_page(list(range(1, 21))),
            make_page([20, *range(21, 40)]),
        ]
    )

    result = run_search(
        loader,
        results_wanted=25,
    )

    assert len(result) == 25
    assert result["id"].is_unique

    assert set(result["id"]) == {f"xing-{identifier}" for identifier in range(1, 26)}

    assert loader.call_count == 2


def test_offset_and_results_limit() -> None:
    loader = Mock(
        side_effect=[
            make_page(list(range(1, 21))),
            make_page(list(range(21, 41))),
        ]
    )

    result = run_search(
        loader,
        offset=18,
        results_wanted=5,
    )

    assert len(result) == 5

    assert set(result["id"]) == {
        "xing-19",
        "xing-20",
        "xing-21",
        "xing-22",
        "xing-23",
    }

    assert loader.call_count == 2


def test_empty_search_results() -> None:
    loader = Mock(return_value=make_page([], total=0))

    result = run_search(loader)

    assert result.empty
    assert list(result.columns) == list(JobPost.model_fields)


def test_page_loader_failure_reports_error() -> None:
    loader = Mock(side_effect=RuntimeError("Simulated XING page failure"))

    result = run_search(loader)

    assert result.empty
    assert "xing" in result.attrs["errors"]

    error = result.attrs["errors"]["xing"]

    assert "Simulated XING page failure" in error


def test_dataframe_contains_expected_columns() -> None:
    loader = Mock(return_value=make_page([1], total=1))

    result = run_search(
        loader,
        results_wanted=1,
    )

    assert len(result) == 1

    expected_columns = {
        "id",
        "site",
        "job_url",
        "title",
        "company",
        "location",
        "description",
        "date_posted",
    }

    assert expected_columns.issubset(result.columns)

    row = result.iloc[0]

    assert row["site"] == "xing"
    assert row["title"] == "Python Developer 1"
    assert row["company"] == "Example Company"
