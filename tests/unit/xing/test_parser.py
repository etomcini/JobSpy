from pathlib import Path

import pytest

from jobspy.model import Compensation, JobType
from jobspy.xing.util import (
    parse_salary,
    parse_search_results,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "search_results.html"
)


@pytest.fixture
def xing_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_parse_search_results(xing_html: str) -> None:
    jobs = parse_search_results(xing_html)

    assert len(jobs) == 1


def test_parse_job_title(xing_html: str) -> None:
    job = parse_search_results(xing_html)[0]

    assert job.title == ("Full Stack Engineer (Python, FastAPI, Next.js) (m/f/x)")


def test_parse_company(xing_html: str) -> None:
    job = parse_search_results(xing_html)[0]

    assert job.company == "Innerspace GmbH"


def test_parse_location(xing_html: str) -> None:
    job = parse_search_results(xing_html)[0]

    assert job.location is not None
    assert job.location.city == "Innsbruck"


def test_parse_job_url(xing_html: str) -> None:
    job = parse_search_results(xing_html)[0]

    assert job.id == "xing-158702428"
    assert job.job_url == (
        "https://www.xing.com/jobs/"
        "innsbruck-full-stack-engineer-python-fastapi-js-158702428"
    )


def test_parse_job_type(xing_html: str) -> None:
    job = parse_search_results(xing_html)[0]

    assert job.job_type == [JobType.FULL_TIME]


def test_parse_salary_range(xing_html: str) -> None:
    job = parse_search_results(xing_html)[0]

    assert job.min_amount == 50000.0
    assert job.max_amount == 60000.0
    assert job.currency == "EUR"
    assert job.interval is None


def test_parse_salary_invalid() -> None:
    assert parse_salary("Competitive salary") == Compensation()


def test_parse_empty_html() -> None:
    assert parse_search_results("<html></html>") == []


def test_parse_duplicate_cards(xing_html: str) -> None:
    jobs = parse_search_results(f"<html><body>{xing_html}{xing_html}</body></html>")

    assert len(jobs) == 1
