from datetime import date
from pathlib import Path

import pytest

from jobspy.model import DescriptionFormat
from jobspy.xing.detail import (
    parse_date_posted,
    parse_job_description,
    parse_job_posting,
    parse_job_remote,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "job_detail.html"
)


@pytest.fixture
def job_detail_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_parse_job_posting(
    job_detail_html: str,
) -> None:
    posting = parse_job_posting(job_detail_html)

    assert posting is not None
    assert posting["@type"] == "JobPosting"
    assert posting["title"] == ("Junior Engineer (m/w/d) Schwerpunkt Python")
    assert posting["hiringOrganization"]["name"] == ("BFI Informationssysteme GmbH")


def test_parse_markdown_description(
    job_detail_html: str,
) -> None:
    description = parse_job_description(job_detail_html)

    assert description is not None
    assert "Entwicklung und Wartung komplexer" in description
    assert "### Beschreibung:" in description
    assert "### Anforderungen:" in description


def test_parse_html_description(
    job_detail_html: str,
) -> None:
    description = parse_job_description(
        job_detail_html,
        DescriptionFormat.HTML,
    )

    assert description is not None
    assert "<H3>Beschreibung:</H3>" in description
    assert "<LI>" in description


def test_parse_plain_description(
    job_detail_html: str,
) -> None:
    description = parse_job_description(
        job_detail_html,
        DescriptionFormat.PLAIN,
    )

    assert description is not None
    assert "Beschreibung:" in description
    assert "Anforderungen:" in description
    assert "<H3>" not in description


def test_parse_publication_date(
    job_detail_html: str,
) -> None:
    assert parse_date_posted(job_detail_html) == date(2026, 10, 28)


def test_parse_remote_job(
    job_detail_html: str,
) -> None:
    assert parse_job_remote(job_detail_html) is True


def test_missing_structured_data() -> None:
    html = "<html><body>No job data</body></html>"

    assert parse_job_posting(html) is None
    assert parse_job_description(html) is None
    assert parse_date_posted(html) is None
    assert parse_job_remote(html) is None


def test_invalid_json_ld() -> None:
    html = """
    <script type="application/ld+json">
        {invalid json}
    </script>
    """

    assert parse_job_posting(html) is None


def test_empty_description() -> None:
    html = """
    <script type="application/ld+json">
    {
        "@type": "JobPosting",
        "description": ""
    }
    </script>
    """

    assert parse_job_description(html) is None


def test_json_ld_graph() -> None:
    html = """
    <script type="application/ld+json">
    {
        "@graph": [
            {"@type": "Organization", "name": "Example"},
            {
                "@type": "JobPosting",
                "description": "<p>Python developer</p>"
            }
        ]
    }
    </script>
    """

    assert (
        parse_job_description(
            html,
            DescriptionFormat.PLAIN,
        )
        == "Python developer"
    )


def test_raw_html_document() -> None:
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "description": "<p>FastAPI backend role</p>",
            "datePosted": "2026-11-17T10:00:00Z",
            "jobLocationType": "TELECOMMUTE"
        }
        </script>
    </head>
    </html>
    """

    assert (
        parse_job_description(
            html,
            DescriptionFormat.PLAIN,
        )
        == "FastAPI backend role"
    )
    assert parse_date_posted(html) == date(2026, 11, 17)
    assert parse_job_remote(html) is True
