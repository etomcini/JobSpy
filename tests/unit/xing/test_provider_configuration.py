from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

from jobspy.model import ScraperInput
from jobspy.xing import Xing


def make_input() -> ScraperInput:
    return ScraperInput(
        site_name=["xing"],
        search_term="Python Developer",
        results_wanted=1,
    )


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
                        }
                    }
                ],
            }
        }
    }


def test_instance_loader_overrides_class_loader() -> None:
    instance_loader = Mock(return_value=make_page())
    instance_factory = Mock(return_value=instance_loader)

    class_factory = Mock()

    with patch.object(
        Xing,
        "page_loader_factory",
        class_factory,
    ):
        scraper = Xing(page_loader_factory=instance_factory)

        jobs = scraper.scrape(make_input())

    assert len(jobs) == 1
    assert jobs[0].id == "xing-1001"

    instance_factory.assert_called_once()
    class_factory.assert_not_called()


def test_two_instances_use_independent_loaders() -> None:
    first_loader = Mock(return_value=make_page())
    second_loader = Mock(
        return_value={
            "data": {
                "jobSearchByQuery": {
                    "total": 0,
                    "collection": [],
                }
            }
        }
    )

    first = Xing(page_loader_factory=lambda config: first_loader)
    second = Xing(page_loader_factory=lambda config: second_loader)

    first_jobs = first.scrape(make_input())
    second_jobs = second.scrape(make_input())

    assert len(first_jobs) == 1
    assert second_jobs == []

    first_loader.assert_called_once()
    second_loader.assert_called_once()


def test_factory_initialization_failure_is_reported() -> None:
    factory = Mock(side_effect=RuntimeError("Could not initialize page loader"))

    scraper = Xing(page_loader_factory=factory)

    jobs = scraper.scrape(make_input())

    assert jobs == []
    assert scraper.error is not None
    assert "Could not initialize page loader" in scraper.error


def test_loader_runtime_failure_is_reported() -> None:
    loader = Mock(side_effect=RuntimeError("Page retrieval failed"))

    scraper = Xing(page_loader_factory=lambda config: loader)

    jobs = scraper.scrape(make_input())

    assert jobs == []
    assert scraper.error is not None
    assert "Page retrieval failed" in scraper.error


def test_missing_loader_is_reported() -> None:
    with patch.object(
        Xing,
        "page_loader_factory",
        None,
    ):
        scraper = Xing()
        jobs = scraper.scrape(make_input())

    assert jobs == []
    assert scraper.error is not None
    assert "no permitted page loader" in scraper.error.lower()
