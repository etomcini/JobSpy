from pathlib import Path
from unittest.mock import Mock

import pytest

from jobspy.model import ScraperInput
from jobspy.xing import Xing


@pytest.fixture
def search_html() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "xing"
        / "search_results_full.html"
    )
    return path.read_text(encoding="utf-8")


@pytest.fixture
def scraper() -> Xing:
    return Xing()


def test_process_all_jobs(
    scraper: Xing,
    search_html: str,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=20,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
    )

    assert len(jobs) == 20


def test_process_result_limit(
    scraper: Xing,
    search_html: str,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=5,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
    )

    assert len(jobs) == 5


def test_process_offset(
    scraper: Xing,
    search_html: str,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=5,
        results_wanted=5,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
    )

    assert len(jobs) == 5

    from jobspy.xing.util import parse_search_results

    expected = parse_search_results(search_html)[5:10]

    assert [job.id for job in jobs] == [job.id for job in expected]


def test_no_detail_loader_when_disabled(
    scraper: Xing,
    search_html: str,
) -> None:
    loader = Mock()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
        fetch_description=False,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
        detail_loader=loader,
    )

    assert len(jobs) == 3
    loader.assert_not_called()


def test_missing_detail_loader(
    scraper: Xing,
    search_html: str,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
        fetch_description=True,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
    )

    assert len(jobs) == 3
    assert scraper.warnings


def test_detail_loader_failure_preserves_job(
    scraper: Xing,
    search_html: str,
) -> None:
    loader = Mock(side_effect=RuntimeError("Detail unavailable"))

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=2,
        fetch_description=True,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
        detail_loader=loader,
    )

    assert len(jobs) == 2
    assert all(job.description is None for job in jobs)
    assert loader.call_count == 2
    assert scraper.warnings


def test_empty_search_results(
    scraper: Xing,
) -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=10,
    )

    jobs = scraper.process_results(
        scraper_input,
        "<html></html>",
    )

    assert jobs == []


def test_successful_detail_enrichment(
    scraper: Xing,
    search_html: str,
) -> None:
    detail_path = (
        Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "job_detail.html"
    )

    detail_html = detail_path.read_text(encoding="utf-8")

    from jobspy.xing.detail import parse_job_posting
    from jobspy.xing.util import parse_search_results

    posting = parse_job_posting(detail_html)
    assert posting is not None

    detail_url = posting["url"]

    matching_jobs = [
        job
        for job in parse_search_results(search_html)
        if job.job_url.split("?")[0] == detail_url.split("?")[0]
    ]

    assert matching_jobs, "Detail fixture must match a search-result job"

    loader = Mock(return_value=detail_html)

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=20,
        fetch_description=True,
    )

    jobs = scraper.process_results(
        scraper_input,
        search_html,
        detail_loader=loader,
    )

    matching_id = matching_jobs[0].id

    enriched = next(job for job in jobs if job.id == matching_id)

    assert enriched.description is not None
    assert enriched.date_posted is not None
