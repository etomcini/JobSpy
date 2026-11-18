from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from jobspy.model import JobPost, JobType, Location

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
    """Convert one GraphQL result item to JobPost."""

    detail = item.get("jobDetail")

    if not isinstance(detail, dict):
        raise ValueError("Missing job detail")

    url = detail.get("url")
    title = detail.get("title")

    if not isinstance(url, str) or not _valid_job_url(url):
        raise ValueError("Invalid job URL")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Missing job title")

    raw_id = detail.get("id")

    if not isinstance(raw_id, str) or not raw_id:
        raise ValueError("Missing job ID")

    company_info = detail.get("companyInfo") or {}
    company = company_info.get("companyNameOverride")

    location_data = detail.get("location") or {}
    city = location_data.get("city")

    employment = detail.get("employmentType") or {}
    employment_type = employment.get("localizationValue")

    salary = detail.get("salary") or {}
    salary_type = salary.get("__typename")

    salary_source = None
    min_amount = None
    max_amount = None
    currency = None

    if salary_type in {"SalaryRange", "SalaryEstimate"}:
        min_amount = salary.get("minimum")
        max_amount = salary.get("maximum")
        currency = salary.get("currency")

        salary_source = (
            "estimated" if salary_type == "SalaryEstimate" else "direct_data"
        )

    elif salary_type == "Salary":
        amount = salary.get("amount")
        min_amount = amount
        max_amount = amount
        currency = salary.get("currency")
        salary_source = "direct_data"

    application = detail.get("application") or {}
    direct_url = (
        application.get("applyUrl")
        if application.get("__typename") == "UrlApplication"
        else None
    )

    return JobPost(
        id=f"xing-{raw_id.split('.')[0]}",
        site="xing",
        job_url=url,
        job_url_direct=direct_url,
        title=title.strip(),
        company=company,
        location=Location(city=city) if city else None,
        job_type=_job_type(employment_type),
        min_amount=min_amount,
        max_amount=max_amount,
        currency=currency,
        salary_source=salary_source,
    )


def parse_graphql_results(
    payload: dict[str, Any],
) -> list[JobPost]:
    """Parse XING GraphQL job-search results."""

    data = payload.get("data") or {}
    search = data.get("jobSearchByQuery") or {}
    collection = search.get("collection") or []

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
