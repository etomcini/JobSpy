from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock, patch

import pytest

from jobspy import scrape_jobs
from jobspy.xing import Xing
from jobspy.xing.config import XingSearchConfig


def make_page() -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": 1,
                "collection": [
                    {
                        "jobDetail": {
                            "id": "1001.abc",
                            "url": ("https://www.xing.com/jobs/python-developer-1001"),
                            "title": "Python Developer",
                            "companyInfo": {"companyNameOverride": "Example Company"},
                            "location": {"city": "Berlin"},
                        }
                    }
                ],
            }
        }
    }


@pytest.fixture
def configured_xing_loader() -> Iterator[None]:
    def loader(
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        if offset == 0:
            return make_page()

        return {
            "data": {
                "jobSearchByQuery": {
                    "total": 1,
                    "collection": [],
                }
            }
        }

    with patch.object(
        Xing,
        "page_loader_factory",
        return_value=loader,
    ):
        yield


def test_scrape_jobs_with_injected_xing_loader(
    configured_xing_loader: None,
) -> None:
    result = scrape_jobs(
        site_name=["xing"],
        search_term="Python Developer",
        location="Berlin",
        results_wanted=1,
        verbose=0,
    )

    assert len(result) == 1

    job = result.iloc[0]

    assert job["site"] == "xing"
    assert job["id"] == "xing-1001"
    assert job["title"] == "Python Developer"
    assert job["company"] == "Example Company"


def test_scrape_jobs_without_loader_returns_error() -> None:
    with patch.object(
        Xing,
        "page_loader_factory",
        None,
    ):
        result = scrape_jobs(
            site_name=["xing"],
            search_term="Python Developer",
            verbose=0,
        )

    assert result.empty
    assert "xing" in result.attrs["errors"]


def test_scrape_jobs_handles_loader_failure() -> None:
    def failing_loader(
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        raise RuntimeError("Simulated loader failure")

    with patch.object(
        Xing,
        "page_loader_factory",
        return_value=failing_loader,
    ):
        result = scrape_jobs(
            site_name=["xing"],
            search_term="Python Developer",
            verbose=0,
        )

    assert result.empty
    assert "xing" in result.attrs["errors"]


def test_search_configuration_reaches_loader_factory() -> None:
    page_loader = Mock(return_value=make_page())
    factory = Mock(return_value=page_loader)

    with patch.object(
        Xing,
        "page_loader_factory",
        factory,
    ):
        result = scrape_jobs(
            site_name=["xing"],
            search_term="  Python Developer  ",
            location="  Berlin  ",
            results_wanted=1,
            verbose=0,
        )

    assert len(result) == 1

    factory.assert_called_once_with(
        XingSearchConfig(
            keywords="Python Developer",
            location="Berlin",
            is_remote=False,
            job_type=None,
        )
    )
