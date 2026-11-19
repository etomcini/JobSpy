import json
from pathlib import Path
from typing import Any

import pytest

from jobspy.model import JobType
from jobspy.xing.graphql_parser import (
    parse_graphql_job,
    parse_graphql_results,
)


@pytest.fixture
def graphql_payload() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "xing"
        / "graphql_page_last.json"
    )

    return json.loads(path.read_text(encoding="utf-8"))


def test_parse_three_jobs(
    graphql_payload: dict[str, Any],
) -> None:
    jobs = parse_graphql_results(graphql_payload)

    assert len(jobs) == 3


def test_first_job(
    graphql_payload: dict[str, Any],
) -> None:
    jobs = parse_graphql_results(graphql_payload)
    job = jobs[0]

    assert job.id == "xing-156968451"
    assert job.title == "FULL STACK ENGINEER (f/m/d)"
    assert job.company == "Omnisent"
    assert job.location is not None
    assert job.location.city == "München"
    assert job.job_type == [JobType.FULL_TIME]


def test_salary_estimate(
    graphql_payload: dict[str, Any],
) -> None:
    jobs = parse_graphql_results(graphql_payload)
    job = jobs[0]

    assert job.min_amount == 55000
    assert job.max_amount == 71500
    assert job.currency == "EUR"
    assert job.salary_source == "estimated"


def test_external_application_url(
    graphql_payload: dict[str, Any],
) -> None:
    jobs = parse_graphql_results(graphql_payload)
    job = jobs[1]

    assert job.job_url_direct == (
        "https://helsing.ai/de/jobs/4871604101?utm_source=xing.com"
    )


def test_unique_job_ids(
    graphql_payload: dict[str, Any],
) -> None:
    jobs = parse_graphql_results(graphql_payload)

    assert len({job.id for job in jobs}) == len(jobs)


def test_empty_collection() -> None:
    payload = {
        "data": {
            "jobSearchByQuery": {
                "collection": [],
            }
        }
    }

    assert parse_graphql_results(payload) == []


def test_missing_job_detail() -> None:
    with pytest.raises(ValueError, match="Missing job detail"):
        parse_graphql_job({})


def test_duplicate_jobs(
    graphql_payload: dict[str, Any],
) -> None:
    collection = graphql_payload["data"]["jobSearchByQuery"]["collection"]

    payload = {
        "data": {
            "jobSearchByQuery": {
                "collection": [
                    collection[0],
                    collection[0],
                ],
            }
        }
    }

    jobs = parse_graphql_results(payload)

    assert len(jobs) == 1
