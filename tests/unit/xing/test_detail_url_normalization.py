from __future__ import annotations

import json

import pytest

from jobspy.model import JobPost
from jobspy.xing.detail import enrich_job_post

BASE_URL = "https://www.xing.com/jobs/python-developer-1001"


def make_job() -> JobPost:
    return JobPost(
        id="xing-1001",
        site="xing",
        job_url=BASE_URL,
        title="Python Developer",
    )


def make_html(url: str) -> str:
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "url": url,
        "description": "<p>Build reliable Python APIs.</p>",
    }

    return (
        "<html><head>"
        '<script type="application/ld+json">'
        f"{json.dumps(posting)}"
        "</script></head></html>"
    )


@pytest.mark.parametrize(
    "detail_url",
    [
        BASE_URL,
        BASE_URL + "/",
        BASE_URL + "?tracking=123",
        BASE_URL + "#description",
    ],
)
def test_equivalent_urls_allow_enrichment(detail_url: str) -> None:
    job = make_job()

    enriched = enrich_job_post(job, make_html(detail_url))

    assert enriched.description is not None
    assert "Build reliable Python APIs." in enriched.description


@pytest.mark.parametrize(
    "detail_url",
    [
        "https://www.xing.com/jobs/another-job-9999",
        "https://evil.example/jobs/python-developer-1001",
        "http://www.xing.com/jobs/python-developer-1001",
        "https://www.xing.com/jobs/search/?keywords=python",
        "https://www.xing.com.evil.example/jobs/python-developer-1001",
    ],
)
def test_invalid_or_mismatched_urls_reject_enrichment(
    detail_url: str,
) -> None:
    job = make_job()

    enriched = enrich_job_post(job, make_html(detail_url))

    assert enriched.description is None
    assert enriched is job


def test_missing_posting_url_preserves_original_job() -> None:
    job = make_job()

    html = (
        '<script type="application/ld+json">'
        '{"@type": "JobPosting", "description": "Example"}'
        "</script>"
    )

    enriched = enrich_job_post(job, html)

    assert enriched is job
