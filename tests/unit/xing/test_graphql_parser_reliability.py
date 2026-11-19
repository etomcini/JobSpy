from __future__ import annotations

from copy import deepcopy

import pytest

from jobspy.xing.graphql_parser import (
    parse_graphql_job,
    parse_graphql_results,
)


def make_job(
    identifier: str,
    *,
    title: str = "Python Developer",
) -> dict[str, object]:
    return {
        "jobDetail": {
            "id": f"{identifier}.abc",
            "url": (f"https://www.xing.com/jobs/python-developer-{identifier}"),
            "title": title,
            "companyInfo": {
                "companyNameOverride": "Example Company",
            },
        }
    }


def make_payload(collection: list[object]) -> dict[str, object]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": len(collection),
                "collection": collection,
            }
        }
    }


def test_valid_jobs_are_preserved() -> None:
    payload = make_payload(
        [
            make_job("1001"),
            make_job("1002"),
            make_job("1003"),
        ]
    )

    jobs = parse_graphql_results(payload)

    assert len(jobs) == 3
    assert [job.id for job in jobs] == [
        "xing-1001",
        "xing-1002",
        "xing-1003",
    ]


def test_invalid_jobs_do_not_remove_valid_jobs() -> None:
    payload = make_payload(
        [
            make_job("1001"),
            None,
            "invalid",
            {"jobDetail": None},
            make_job("1002"),
            {"jobDetail": {"title": "Missing URL"}},
            make_job("1003"),
        ]
    )

    jobs = parse_graphql_results(payload)

    assert len(jobs) == 3
    assert [job.id for job in jobs] == [
        "xing-1001",
        "xing-1002",
        "xing-1003",
    ]


def test_duplicate_jobs_are_removed() -> None:
    first = make_job("1001")

    payload = make_payload(
        [
            first,
            deepcopy(first),
            make_job("1002"),
        ]
    )

    jobs = parse_graphql_results(payload)

    assert len(jobs) == 2
    assert [job.id for job in jobs] == [
        "xing-1001",
        "xing-1002",
    ]


@pytest.mark.parametrize(
    "invalid_detail",
    [
        None,
        "invalid",
        [],
        123,
        {},
    ],
)
def test_invalid_job_detail_is_skipped(
    invalid_detail: object,
) -> None:
    payload = make_payload(
        [
            {"jobDetail": invalid_detail},
            make_job("1001"),
        ]
    )

    jobs = parse_graphql_results(payload)

    assert len(jobs) == 1
    assert jobs[0].id == "xing-1001"


@pytest.mark.parametrize(
    "invalid_title",
    [
        None,
        "",
        "   ",
        123,
        [],
    ],
)
def test_invalid_titles_are_rejected(
    invalid_title: object,
) -> None:
    item = make_job("1001")
    detail = item["jobDetail"]

    assert isinstance(detail, dict)
    detail["title"] = invalid_title

    with pytest.raises(ValueError, match="Missing job title"):
        parse_graphql_job(item)


@pytest.mark.parametrize(
    "invalid_url",
    [
        None,
        "",
        "http://www.xing.com/jobs/python-1001",
        "https://example.com/jobs/python-1001",
        "https://www.xing.com/profile/example",
        "https://www.xing.com/jobs/search/ki",
    ],
)
def test_invalid_urls_are_rejected(
    invalid_url: object,
) -> None:
    item = make_job("1001")
    detail = item["jobDetail"]

    assert isinstance(detail, dict)
    detail["url"] = invalid_url

    with pytest.raises(ValueError, match="Invalid job URL"):
        parse_graphql_job(item)


@pytest.mark.parametrize(
    "collection",
    [
        None,
        {},
        "invalid",
        123,
    ],
)
def test_invalid_collections_return_empty(
    collection: object,
) -> None:
    payload = {
        "data": {
            "jobSearchByQuery": {
                "collection": collection,
            }
        }
    }

    assert parse_graphql_results(payload) == []


def test_malformed_optional_fields_are_ignored() -> None:
    item = make_job("1001")
    detail = item["jobDetail"]

    assert isinstance(detail, dict)

    detail.update(
        {
            "companyInfo": "invalid",
            "location": 123,
            "employmentType": [],
            "salary": "invalid",
            "application": None,
        }
    )

    job = parse_graphql_job(item)

    assert job.id == "xing-1001"
    assert job.company is None
    assert job.location is None
    assert job.job_type is None
    assert job.min_amount is None
    assert job.max_amount is None
