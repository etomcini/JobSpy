from collections.abc import Iterator
from unittest.mock import Mock

from jobspy.model import JobPost, ScraperInput
from jobspy.xing import Xing


def make_job(number: int) -> JobPost:
    return JobPost(
        id=f"xing-{number}",
        site="xing",
        job_url=f"https://www.xing.com/jobs/test-job-{number}",
        title=f"Job {number}",
        company="Test Company",
    )


def test_shared_deduplication() -> None:
    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=10,
    )

    pages = [
        [make_job(1), make_job(2)],
        [make_job(2), make_job(3)],
    ]

    jobs = scraper._process_job_pages(
        scraper_input,
        pages,
    )

    assert [job.id for job in jobs] == [
        "xing-1",
        "xing-2",
        "xing-3",
    ]


def test_shared_offset() -> None:
    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        offset=2,
        results_wanted=2,
    )

    pages = [
        [make_job(1), make_job(2)],
        [make_job(3), make_job(4)],
        [make_job(5)],
    ]

    jobs = scraper._process_job_pages(
        scraper_input,
        pages,
    )

    assert [job.id for job in jobs] == [
        "xing-3",
        "xing-4",
    ]


def test_shared_stops_early() -> None:
    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=2,
    )

    consumed = 0

    def pages() -> Iterator[list[JobPost]]:
        nonlocal consumed

        for number in range(10):
            consumed += 1
            yield [make_job(number)]

    jobs = scraper._process_job_pages(
        scraper_input,
        pages(),
    )

    assert len(jobs) == 2
    assert consumed == 2


def test_no_detail_loading_when_disabled() -> None:
    scraper = Xing()
    loader = Mock()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=1,
        fetch_description=False,
    )

    jobs = scraper._process_job_pages(
        scraper_input,
        [[make_job(1)]],
        detail_loader=loader,
    )

    assert len(jobs) == 1
    loader.assert_not_called()


def test_detail_failure_preserves_job() -> None:
    scraper = Xing()

    loader = Mock(side_effect=RuntimeError("Detail unavailable"))

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=1,
        fetch_description=True,
    )

    jobs = scraper._process_job_pages(
        scraper_input,
        [[make_job(1)]],
        detail_loader=loader,
    )

    assert len(jobs) == 1
    assert jobs[0].id == "xing-1"
    assert scraper.warnings


def test_empty_pages() -> None:
    scraper = Xing()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=5,
    )

    assert (
        scraper._process_job_pages(
            scraper_input,
            [],
        )
        == []
    )
