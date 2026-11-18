import json
from datetime import date
from pathlib import Path

import pytest

import jobspy.xing.detail as detail
from jobspy.model import DescriptionFormat, JobPost, Location
from jobspy.xing.detail import enrich_job_post


@pytest.fixture
def job_detail_html() -> str:
    fixture = (
        Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "job_detail.html"
    )
    return fixture.read_text(encoding="utf-8")


@pytest.fixture
def job() -> JobPost:
    return JobPost(
        id="xing-158839271",
        site="xing",
        job_url=(
            "https://www.xing.com/jobs/"
            "ilmenau-junior-engineer-schwerpunkt-python-158839271"
        ),
        title="Junior Engineer (m/w/d) Schwerpunkt Python",
        company="BFI Informationssysteme GmbH",
        location=Location(city="Ilmenau"),
        is_remote=None,
    )


def test_enrich_job_description(
    job: JobPost,
    job_detail_html: str,
) -> None:
    enriched = enrich_job_post(job, job_detail_html)

    assert enriched.description is not None
    assert "Entwicklung und Wartung" in enriched.description


def test_enrich_job_date(
    job: JobPost,
    job_detail_html: str,
) -> None:
    enriched = enrich_job_post(job, job_detail_html)

    assert enriched.date_posted == date(2026, 10, 28)


def test_enrich_job_remote(
    job: JobPost,
    job_detail_html: str,
) -> None:
    enriched = enrich_job_post(job, job_detail_html)

    assert enriched.is_remote is True


def test_preserves_existing_fields(
    job: JobPost,
    job_detail_html: str,
) -> None:
    enriched = enrich_job_post(job, job_detail_html)

    assert enriched.id == job.id
    assert enriched.title == job.title
    assert enriched.company == job.company
    assert enriched.location == job.location
    assert enriched.job_url == job.job_url


def test_original_job_not_modified(
    job: JobPost,
    job_detail_html: str,
) -> None:
    enrich_job_post(job, job_detail_html)

    assert job.description is None
    assert job.date_posted is None
    assert job.is_remote is None


def test_missing_detail_data(
    job: JobPost,
) -> None:
    enriched = enrich_job_post(
        job,
        "<html><body>No structured data</body></html>",
    )

    assert enriched == job


def test_enrichment_html_format(
    job: JobPost,
    job_detail_html: str,
) -> None:
    enriched = enrich_job_post(
        job,
        job_detail_html,
        DescriptionFormat.HTML,
    )

    assert enriched.description is not None
    assert "<H3>Beschreibung:</H3>" in enriched.description


def make_detail_html(
    url: str | None,
    description: str = "<p>Python backend developer</p>",
) -> str:
    posting: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "description": description,
        "datePosted": "2026-11-18T10:00:00Z",
        "jobLocationType": "TELECOMMUTE",
    }

    if url is not None:
        posting["url"] = url

    return '<script type="application/ld+json">' + json.dumps(posting) + "</script>"


def test_enrichment_rejects_wrong_job(
    job: JobPost,
) -> None:
    html = make_detail_html("https://www.xing.com/jobs/berlin-other-job-999999")

    enriched = enrich_job_post(job, html)

    assert enriched is job
    assert enriched.description is None
    assert enriched.date_posted is None


def test_enrichment_rejects_missing_url(
    job: JobPost,
) -> None:
    html = make_detail_html(None)

    enriched = enrich_job_post(job, html)

    assert enriched is job


def test_enrichment_accepts_tracking_parameters(
    job: JobPost,
) -> None:
    job_with_tracking = job.model_copy(
        update={
            "job_url": job.job_url + "?ijt=jb_55",
        }
    )

    html = make_detail_html(job.job_url)

    enriched = enrich_job_post(
        job_with_tracking,
        html,
    )

    assert enriched.description is not None
    assert enriched.date_posted == date(2026, 11, 18)


def test_enrichment_rejects_external_url(
    job: JobPost,
) -> None:
    html = make_detail_html("https://example.com/jobs/other-job")

    enriched = enrich_job_post(job, html)

    assert enriched is job


def test_enrichment_preserves_existing_values(
    job: JobPost,
) -> None:
    existing = job.model_copy(
        update={
            "date_posted": date(2026, 11, 1),
            "is_remote": True,
        }
    )

    html = make_detail_html(
        existing.job_url,
        description="",
    )

    enriched = enrich_job_post(existing, html)

    assert enriched.date_posted == date(2026, 11, 18)
    assert enriched.is_remote is True


def test_enrichment_parses_posting_once(
    job: JobPost,
    job_detail_html: str,
    mocker,
) -> None:
    spy = mocker.spy(detail, "parse_job_posting")

    enrich_job_post(job, job_detail_html)

    assert spy.call_count == 1
