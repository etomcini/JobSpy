from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from jobspy.model import JobPost, JobType, Location
from jobspy.xing.normalization import (
    normalize_job_id,
    normalize_text,
    normalize_xing_job_url,
    safe_dict,
)
from jobspy.xing.salary import parse_graphql_salary
from jobspy.xing.util import parse_job_types

JOB_TYPES: dict[str, JobType] = {
    "full-time": JobType.FULL_TIME,
    "part-time": JobType.PART_TIME,
    "contract": JobType.CONTRACT,
    "temporary": JobType.TEMPORARY,
    "internship": JobType.INTERNSHIP,
}


def _job_type(value: str | None) -> list[JobType] | None:
    if not value:
        return None

    result = JOB_TYPES.get(value.strip().lower())
    return [result] if result is not None else None


def _valid_job_url(url: str) -> bool:
    parsed = urlsplit(url)

    return (
        parsed.scheme == "https"
        and parsed.netloc == "www.xing.com"
        and parsed.path.startswith("/jobs/")
        and parsed.path != "/jobs/search/ki"
    )


def parse_graphql_job(item: dict[str, Any]) -> JobPost:
    """Convert one XING GraphQL result into a normalized JobPost."""

    detail = safe_dict(item.get("jobDetail"))

    if not detail:
        raise ValueError("Missing job detail")

    job_url = normalize_xing_job_url(detail.get("url"))
    title = normalize_text(detail.get("title"))
    job_id = normalize_job_id(detail.get("id"))

    if job_url is None:
        raise ValueError("Invalid job URL")

    if title is None:
        raise ValueError("Missing job title")

    if job_id is None:
        raise ValueError("Missing job ID")

    company_info = safe_dict(detail.get("companyInfo"))
    company = normalize_text(company_info.get("companyNameOverride"))

    location_data = safe_dict(detail.get("location"))
    city = normalize_text(location_data.get("city"))

    employment = safe_dict(detail.get("employmentType"))
    employment_type = normalize_text(employment.get("localizationValue"))

    job_types = (
        parse_job_types([employment_type]) if employment_type is not None else None
    )

    salary = parse_graphql_salary(detail.get("salary"))

    application = safe_dict(detail.get("application"))

    direct_url = None

    if application.get("__typename") == "UrlApplication":
        direct_url = normalize_text(application.get("applyUrl"))

    return JobPost(
        id=job_id,
        site="xing",
        job_url=job_url,
        job_url_direct=direct_url,
        title=title,
        company=company,
        location=Location(city=city) if city else None,
        job_type=job_types,
        min_amount=salary.min_amount,
        max_amount=salary.max_amount,
        currency=salary.currency,
        salary_source=salary.salary_source,
    )


def parse_graphql_results(
    payload: dict[str, Any],
) -> list[JobPost]:
    """Parse valid, unique jobs from a XING GraphQL response."""

    data = safe_dict(payload.get("data"))
    search = safe_dict(data.get("jobSearchByQuery"))
    collection = search.get("collection")

    if not isinstance(collection, list):
        return []

    jobs: list[JobPost] = []
    seen: set[str] = set()

    for item in collection:
        if not isinstance(item, dict):
            continue

        try:
            job = parse_graphql_job(item)
        except (ValueError, TypeError):
            continue

        key = job.id or job.job_url

        if key in seen:
            continue

        seen.add(key)
        jobs.append(job)

    return jobs
