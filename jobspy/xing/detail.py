from __future__ import annotations

import json
from datetime import date
from typing import Any

from bs4 import BeautifulSoup
from markdownify import markdownify

from jobspy.model import DescriptionFormat, JobPost
from jobspy.xing.normalization import normalize_xing_job_url


def _get_document(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")

    source_lines = soup.select(".source-container td.line-content")

    if source_lines:
        source_html = "".join(line.get_text() for line in source_lines)
        return BeautifulSoup(source_html, "html.parser")

    return soup


def parse_job_posting(html: str) -> dict[str, Any] | None:
    soup = _get_document(html)

    for script in soup.select('script[type="application/ld+json"]'):
        if not script.string:
            continue

        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]

        while candidates:
            candidate = candidates.pop(0)

            if not isinstance(candidate, dict):
                continue

            job_type = candidate.get("@type")

            if job_type == "JobPosting" or (
                isinstance(job_type, list) and "JobPosting" in job_type
            ):
                return candidate

            graph = candidate.get("@graph")
            if isinstance(graph, list):
                candidates.extend(graph)

    return None


def _description_from_posting(
    posting: dict[str, Any],
    description_format: DescriptionFormat,
) -> str | None:
    description = posting.get("description")

    if not isinstance(description, str):
        return None

    description = description.strip()

    if not description:
        return None

    if description_format == DescriptionFormat.HTML:
        return description

    if description_format == DescriptionFormat.PLAIN:
        soup = BeautifulSoup(description, "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        return soup.get_text(separator="\n", strip=True) or None

    return (
        markdownify(
            description,
            heading_style="ATX",
        ).strip()
        or None
    )


def _date_from_posting(
    posting: dict[str, Any],
) -> date | None:
    value = posting.get("datePosted")

    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _remote_from_posting(
    posting: dict[str, Any],
) -> bool | None:
    location_type = posting.get("jobLocationType")

    if isinstance(location_type, str):
        if location_type.upper() == "TELECOMMUTE":
            return True

    return None


def parse_job_description(
    html: str,
    description_format: DescriptionFormat = (DescriptionFormat.MARKDOWN),
) -> str | None:
    posting = parse_job_posting(html)

    if posting is None:
        return None

    return _description_from_posting(
        posting,
        description_format,
    )


def parse_date_posted(html: str) -> date | None:
    posting = parse_job_posting(html)

    if posting is None:
        return None

    return _date_from_posting(posting)


def parse_job_remote(html: str) -> bool | None:
    posting = parse_job_posting(html)

    if posting is None:
        return None

    return _remote_from_posting(posting)


def enrich_job_post(
    job: JobPost,
    html: str,
    description_format: DescriptionFormat = (DescriptionFormat.MARKDOWN),
) -> JobPost:
    posting = parse_job_posting(html)

    if posting is None:
        return job

    detail_url = posting.get("url")

    if not isinstance(detail_url, str):
        return job

    expected_url = normalize_xing_job_url(job.job_url)
    actual_url = normalize_xing_job_url(detail_url)

    if expected_url is None or actual_url is None or expected_url != actual_url:
        return job

    description = _description_from_posting(
        posting,
        description_format,
    )
    date_posted = _date_from_posting(posting)
    is_remote = _remote_from_posting(posting)

    updates: dict[str, object] = {}

    if description is not None:
        updates["description"] = description

    if date_posted is not None:
        updates["date_posted"] = date_posted

    if is_remote is not None:
        updates["is_remote"] = is_remote

    if not updates:
        return job

    return job.model_copy(update=updates)
