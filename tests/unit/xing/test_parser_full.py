from pathlib import Path

import pytest

from jobspy.xing.util import parse_salary, parse_search_results

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "xing"
    / "search_results_full.html"
)


@pytest.fixture
def full_xing_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_parse_all_20_jobs(full_xing_html: str) -> None:
    jobs = parse_search_results(full_xing_html)

    assert len(jobs) == 20


def test_all_jobs_have_required_fields(
    full_xing_html: str,
) -> None:
    jobs = parse_search_results(full_xing_html)

    for job in jobs:
        assert job.title
        assert job.job_url.startswith("https://www.xing.com/jobs/")
        assert job.company


def test_all_jobs_have_unique_urls(
    full_xing_html: str,
) -> None:
    jobs = parse_search_results(full_xing_html)

    urls = [job.job_url for job in jobs]

    assert len(urls) == len(set(urls))


def test_first_job_matches_source(
    full_xing_html: str,
) -> None:
    job = parse_search_results(full_xing_html)[0]

    assert job.title == ("Junior Engineer (m/w/d) Schwerpunkt Python")
    assert job.company == "BFI Informationssysteme GmbH"
    assert job.location is not None
    assert job.location.city == "Ilmenau"
    assert job.min_amount == 38500
    assert job.max_amount == 54000
    assert job.currency == "EUR"


def test_parse_chf_salary() -> None:
    salary = parse_salary("CHF 92,000 – CHF 115,500")

    assert salary.currency == "CHF"
    assert salary.min_amount == 92000
    assert salary.max_amount == 115500


def test_parse_eur_salary_code() -> None:
    salary = parse_salary("EUR 38500 - EUR 54000")

    assert salary.currency == "EUR"
    assert salary.min_amount == 38500
    assert salary.max_amount == 54000


def test_missing_salary_is_allowed(
    full_xing_html: str,
) -> None:
    jobs = parse_search_results(full_xing_html)

    job = next(job for job in jobs if job.id == "xing-159220632")

    assert job.min_amount is None
    assert job.max_amount is None


def test_salary_interval_not_assumed(
    full_xing_html: str,
) -> None:
    jobs = parse_search_results(full_xing_html)

    for job in jobs:
        assert job.interval is None
