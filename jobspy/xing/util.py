from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from jobspy.model import (
    Compensation,
    JobPost,
    JobType,
    Location,
)

BASE_URL = "https://www.xing.com"


SALARY_PATTERN = re.compile(
    r"(?P<currency>€|\$|£|EUR|USD|GBP|CHF)\s*"
    r"(?P<minimum>[\d,.]+)\s*[–-]\s*"
    r"(?:(?:€|\$|£|EUR|USD|GBP|CHF)\s*)?"
    r"(?P<maximum>[\d,.]+)",
    re.IGNORECASE,
)

CURRENCIES = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "EUR": "EUR",
    "USD": "USD",
    "GBP": "GBP",
    "CHF": "CHF",
}


JOB_TYPES: dict[str, JobType] = {
    "full-time": JobType.FULL_TIME,
    "full time": JobType.FULL_TIME,
    "fulltime": JobType.FULL_TIME,
    "part-time": JobType.PART_TIME,
    "part time": JobType.PART_TIME,
    "parttime": JobType.PART_TIME,
    "contract": JobType.CONTRACT,
    "temporary": JobType.TEMPORARY,
    "internship": JobType.INTERNSHIP,
    "freelance/temp": JobType.OTHER,
    "self-employed": JobType.OTHER,
}

REMOTE_LOCATIONS = {
    "homeoffice",
    "home office",
    "remote",
    "fully remote",
    "100% remote",
    "work from home",
}


def parse_remote_location(location_name: str | None) -> bool | None:
    if location_name is None:
        return None

    normalized = " ".join(location_name.lower().split())

    if normalized in REMOTE_LOCATIONS:
        return True

    return None


def parse_job_types(markers: list[str]) -> list[JobType] | None:
    job_types: list[JobType] = []

    for marker in markers:
        normalized = " ".join(marker.lower().split())
        job_type = JOB_TYPES.get(normalized)

        if job_type is not None and job_type not in job_types:
            job_types.append(job_type)

    return job_types or None


def parse_salary(text: str) -> Compensation:
    match = SALARY_PATTERN.search(text)

    if not match:
        return Compensation()

    minimum = float(match.group("minimum").replace(",", ""))
    maximum = float(match.group("maximum").replace(",", ""))

    return Compensation(
        min_amount=minimum,
        max_amount=maximum,
        currency=CURRENCIES[match.group("currency").upper()],
        interval=None,
    )


def parse_job_card(card: Tag) -> JobPost:
    title_tag = card.select_one('[data-testid="job-teaser-list-title"]')

    link_tag = card.select_one('a[href^="/jobs/"]')

    if title_tag is None or link_tag is None:
        raise ValueError("Missing job title or URL")

    href = link_tag.get("href")

    if not isinstance(href, str):
        raise ValueError("Invalid job URL")

    absolute_url = urljoin(BASE_URL, href)
    parsed_url = urlsplit(absolute_url)

    if parsed_url.hostname != "www.xing.com" or not parsed_url.path.startswith(
        "/jobs/"
    ):
        raise ValueError("Unexpected job URL")

    job_url = urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            "",
            "",
        )
    )

    company_tag = card.select_one('p[class*="__Company-"]')

    location_tag = card.select_one(
        'div[class*="multi-location-display-styles__Container"] p'
    )

    markers = [
        marker.get_text(" ", strip=True)
        for marker in card.select('[data-xds="Marker"]')
    ]

    job_types = parse_job_types(markers)

    salary = Compensation()

    for marker in markers:
        parsed_salary = parse_salary(marker)

        if parsed_salary.min_amount is not None:
            salary = parsed_salary
            break

    location_name = location_tag.get_text(" ", strip=True) if location_tag else None

    if location_name:
        location_name = re.sub(
            r"\+\s*\d+\s+more$",
            "",
            location_name,
        ).strip()

    job_id_match = re.search(
        r"-(\d+)$",
        parsed_url.path,
    )

    job_id = f"xing-{job_id_match.group(1)}" if job_id_match else None

    return JobPost(
        id=job_id,
        site="xing",
        job_url=job_url,
        title=title_tag.get_text(" ", strip=True),
        company=(company_tag.get_text(" ", strip=True) if company_tag else None),
        location=(Location(city=location_name) if location_name else None),
        job_type=job_types,
        is_remote=parse_remote_location(location_name),
        min_amount=salary.min_amount,
        max_amount=salary.max_amount,
        currency=salary.currency,
        interval=salary.interval,
        salary_source=None,
    )


def parse_search_results(html: str) -> list[JobPost]:
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select('article[data-testid="job-search-result"]')

    jobs: list[JobPost] = []
    seen: set[str] = set()

    for card in cards:
        try:
            job = parse_job_card(card)
        except ValueError:
            continue

        key = job.id or job.job_url

        if key in seen:
            continue

        seen.add(key)
        jobs.append(job)

    return jobs
