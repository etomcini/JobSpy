from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from jobspy.model import DescriptionFormat, ScraperInput
from jobspy.xing.detail import parse_job_posting
from jobspy.xing.search_result import SearchStatus
from jobspy.xing.search_workflow import run_graphql_search

JOB_URL = "https://www.xing.com/jobs/python-developer-1001"


def make_page() -> dict:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": 1,
                "collection": [
                    {
                        "jobDetail": {
                            "id": "1001.abc",
                            "url": JOB_URL,
                            "title": "Python Developer",
                            "companyInfo": {"companyNameOverride": "Example Company"},
                        }
                    }
                ],
            }
        }
    }


def make_detail_html(
    *,
    url: str = JOB_URL,
    description: str = "<h2>Responsibilities</h2><p>Build APIs.</p>",
) -> str:
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Python Developer",
        "url": url,
        "description": description,
        "datePosted": "2026-11-01",
        "jobLocationType": "TELECOMMUTE",
    }

    return (
        "<html><head>"
        '<script type="application/ld+json">'
        f"{json.dumps(posting)}"
        "</script></head><body></body></html>"
    )


def make_input(
    *,
    fetch_description: bool = True,
    description_format: DescriptionFormat = DescriptionFormat.MARKDOWN,
) -> ScraperInput:
    return ScraperInput(
        site_name=["xing"],
        search_term="Python Developer",
        results_wanted=1,
        fetch_description=fetch_description,
        description_format=description_format,
    )


def test_successful_description_enrichment() -> None:
    detail_loader = Mock(return_value=make_detail_html())

    result = run_graphql_search(
        make_input(),
        Mock(return_value=make_page()),
        detail_loader=detail_loader,
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.count == 1

    job = result.jobs[0]

    assert "Responsibilities" in (job.description or "")
    assert "Build APIs." in (job.description or "")
    assert job.date_posted == date(2026, 11, 1)
    assert job.is_remote is True

    detail_loader.assert_called_once_with(JOB_URL)


def test_plain_text_description() -> None:
    result = run_graphql_search(
        make_input(
            description_format=DescriptionFormat.PLAIN,
        ),
        Mock(return_value=make_page()),
        detail_loader=Mock(return_value=make_detail_html()),
    )

    description = result.jobs[0].description

    assert description is not None
    assert "Build APIs." in description
    assert "<h2>" not in description


def test_html_description() -> None:
    result = run_graphql_search(
        make_input(
            description_format=DescriptionFormat.HTML,
        ),
        Mock(return_value=make_page()),
        detail_loader=Mock(return_value=make_detail_html()),
    )

    assert result.jobs[0].description == ("<h2>Responsibilities</h2><p>Build APIs.</p>")


def test_mismatched_detail_url_preserves_job() -> None:
    result = run_graphql_search(
        make_input(),
        Mock(return_value=make_page()),
        detail_loader=Mock(
            return_value=make_detail_html(
                url="https://www.xing.com/jobs/another-job-9999"
            )
        ),
    )

    job = result.jobs[0]

    assert job.description is None
    assert job.date_posted is None
    assert job.is_remote is None


def test_detail_loader_failure_preserves_job() -> None:
    result = run_graphql_search(
        make_input(),
        Mock(return_value=make_page()),
        detail_loader=Mock(side_effect=RuntimeError("Connection interrupted")),
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.count == 1
    assert result.jobs[0].description is None
    assert any("Could not enrich job" in warning for warning in result.warnings)


def test_description_not_requested() -> None:
    detail_loader = Mock()

    result = run_graphql_search(
        make_input(fetch_description=False),
        Mock(return_value=make_page()),
        detail_loader=detail_loader,
    )

    assert result.count == 1
    assert result.jobs[0].description is None

    detail_loader.assert_not_called()


def test_missing_detail_loader_adds_warning() -> None:
    result = run_graphql_search(
        make_input(),
        Mock(return_value=make_page()),
        detail_loader=None,
    )

    assert result.count == 1
    assert result.jobs[0].description is None
    assert any("no detail loader" in warning.lower() for warning in result.warnings)


def test_enrichment_with_real_xing_fixture() -> None:
    """Verify enrichment using the captured XING detail page."""

    fixture_path = (
        Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "job_detail.html"
    )

    html = fixture_path.read_text(encoding="utf-8")

    posting = parse_job_posting(html)

    assert posting is not None

    job_url = posting.get("url")

    assert isinstance(job_url, str)

    # Use the real fixture URL to satisfy the URL match check.
    page = make_page()
    search = page["data"]["jobSearchByQuery"]
    job_detail = search["collection"][0]["jobDetail"]

    job_detail["id"] = "158839271.abc"
    job_detail["url"] = job_url

    detail_loader = Mock(return_value=html)

    result = run_graphql_search(
        make_input(),
        Mock(return_value=page),
        detail_loader=detail_loader,
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.count == 1

    job = result.jobs[0]

    assert job.id == "xing-158839271"
    assert job.job_url == job_url

    assert job.description is not None
    assert len(job.description) > 100

    assert job.date_posted == date(2026, 10, 28)
    assert job.is_remote is True

    detail_loader.assert_called_once_with(job_url)
