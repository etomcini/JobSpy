from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from urllib.parse import urlencode

import requests

from jobspy.model import DescriptionFormat, JobPost
from jobspy.xing.detail import enrich_job_post
from jobspy.xing.util import parse_search_results

BASE_URL = "https://www.xing.com/jobs/search/ki"
TIMEOUT = 20
REQUEST_DELAY_SECONDS = 2.0

HEADERS = {
    "User-Agent": "JobSpy-XING-Integration-Test/0.1",
    "Accept": "text/html",
}


class Workplace(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SearchFilters:
    search_term: str = "Python Developer"
    location: str = "Munich"

    # Search only the initial HTML page for now.
    results_wanted: int = 20

    # Set None to disable title filtering.
    title_keywords: tuple[str, ...] = (
        "python",
        "backend",
        "software",
        "developer",
        "engineer",
    )

    # None disables the publication-date filter.
    hours_old: int | None = 168

    # Examples: ("full_time",), ("part_time",)
    # Empty tuple disables employment-type filtering.
    job_types: tuple[str, ...] = ()

    # Empty tuple allows every workplace type.
    workplaces: tuple[Workplace, ...] = (
        Workplace.REMOTE,
        Workplace.HYBRID,
        Workplace.ONSITE,
        Workplace.UNKNOWN,
    )

    # Every required skill must be found in the
    # description or title.
    required_skills: tuple[str, ...] = ("python",)

    # Optional skills contribute to ranking.
    preferred_skills: tuple[str, ...] = (
        "fastapi",
        "postgresql",
        "docker",
        "rabbitmq",
        "rest api",
        "pytest",
    )

    # None disables experience filtering.
    # This checks explicit year requirements only.
    max_experience_years: int | None = None

    # When True, jobs without publication dates
    # are excluded if hours_old is enabled.
    exclude_unknown_dates: bool = False

    # When True, unknown job types are excluded
    # if job_types is enabled.
    exclude_unknown_job_types: bool = False

    # When True, missing descriptions are excluded.
    require_description: bool = True


FILTERS = SearchFilters()


@dataclass
class MatchedJob:
    job: JobPost
    workplace: Workplace
    matched_required: list[str]
    matched_preferred: list[str]
    experience_years: int | None
    score: int


def fetch_html(
    session: requests.Session,
    url: str,
) -> str | None:
    """Retrieve a XING page without following redirects."""

    try:
        response = session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=False,
        )
        response.raise_for_status()

        if response.status_code != 200:
            print(f"Unexpected HTTP status: {response.status_code}")
            return None

        response.encoding = "utf-8"
        return response.text

    except requests.RequestException as exc:
        print(f"Request failed for {url}: {exc}")
        return None


def contains_keyword(text: str, keyword: str) -> bool:
    """Match complete skill terms without partial-word matches."""

    normalized = " ".join(keyword.casefold().split())

    if not normalized:
        return False

    pattern = r"(?<!\w)" + re.escape(normalized).replace(r"\ ", r"\s+") + r"(?!\w)"

    return re.search(pattern, text.casefold()) is not None


def matching_keywords(
    text: str,
    keywords: tuple[str, ...],
) -> list[str]:
    return [keyword for keyword in keywords if contains_keyword(text, keyword)]


def classify_workplace(job: JobPost) -> Workplace:
    """Classify workplace using explicit textual evidence."""

    text = (f"{job.title}\n{job.location}\n{job.description or ''}").casefold()

    hybrid_patterns = (
        r"\bhybrid\b",
        r"\bhybrides?\b",
        r"\bhybridarbeit\b",
        r"\bteilweise\s+remote\b",
        r"\bpartially\s+remote\b",
        r"\bpartly\s+remote\b",
        r"\bremote\s+or\s+on[- ]site\b",
        r"\bhomeoffice.{0,50}\bbüro\b",
    )

    remote_patterns = (
        r"\bfully\s+remote\b",
        r"\b100\s*%\s*remote\b",
        r"\bremote[- ]only\b",
        r"\bwork\s+from\s+anywhere\b",
        r"\bvollständig\s+remote\b",
    )

    onsite_patterns = (
        r"\bon[- ]site\s+only\b",
        r"\bfully\s+on[- ]site\b",
        r"\b100\s*%\s*(?:on[- ]site|vor\s+ort)\b",
        r"\bno\s+remote\b",
        r"\bkein\s+homeoffice\b",
    )

    # Hybrid takes priority because it combines
    # remote and office-based work.
    if any(re.search(pattern, text) for pattern in hybrid_patterns):
        return Workplace.HYBRID

    if any(re.search(pattern, text) for pattern in remote_patterns):
        return Workplace.REMOTE

    if any(re.search(pattern, text) for pattern in onsite_patterns):
        return Workplace.ONSITE

    if job.is_remote is True:
        return Workplace.REMOTE

    # False does not prove an on-site requirement.
    return Workplace.UNKNOWN


def extract_experience_years(
    description: str,
) -> int | None:
    """Find explicit minimum years of experience."""

    patterns = (
        r"\b(?:at\s+least|minimum|min\.?)\s*"
        r"(\d{1,2})\+?\s*years?\b",
        r"\b(\d{1,2})\+?\s*years?\s+"
        r"(?:of\s+)?(?:professional\s+)?experience\b",
        r"\b(?:mindestens|min\.?)\s*"
        r"(\d{1,2})\+?\s*jahre?\b",
        r"\b(\d{1,2})\+?\s*jahre?\s+"
        r"(?:berufserfahrung|erfahrung)\b",
    )

    values: list[int] = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            description,
            flags=re.IGNORECASE,
        ):
            values.append(int(match.group(1)))

    # Conservative: return the largest explicit minimum.
    # This is a heuristic, not a complete requirement parser.
    return max(values) if values else None


def normalize_job_types(job: JobPost) -> set[str]:
    """Convert JobSpy job-type values to comparable strings."""

    raw_types = job.job_type

    if raw_types is None:
        return set()

    values = raw_types if isinstance(raw_types, (list, tuple, set)) else [raw_types]

    normalized: set[str] = set()

    for value in values:
        raw = value.value if hasattr(value, "value") else str(value)
        normalized.add(str(raw).lower().replace("-", "_").replace(" ", "_"))

    return normalized


def passes_date_filter(
    job: JobPost,
    filters: SearchFilters,
) -> bool:
    if filters.hours_old is None:
        return True

    if job.date_posted is None:
        return not filters.exclude_unknown_dates

    posted = job.date_posted

    if isinstance(posted, date):
        cutoff = date.today() - timedelta(hours=filters.hours_old)
        return posted >= cutoff

    return not filters.exclude_unknown_dates


def passes_job_type_filter(
    job: JobPost,
    filters: SearchFilters,
) -> bool:
    if not filters.job_types:
        return True

    actual_types = normalize_job_types(job)

    if not actual_types:
        return not filters.exclude_unknown_job_types

    return bool(actual_types.intersection(filters.job_types))


def evaluate_job(
    job: JobPost,
    filters: SearchFilters,
) -> MatchedJob | None:
    """Filter and score one enriched job."""

    title = job.title or ""
    description = job.description or ""

    if filters.require_description and not description.strip():
        return None

    if filters.title_keywords:
        if not matching_keywords(title, filters.title_keywords):
            return None

    if not passes_date_filter(job, filters):
        return None

    if not passes_job_type_filter(job, filters):
        return None

    workplace = classify_workplace(job)

    if filters.workplaces and workplace not in filters.workplaces:
        return None

    searchable_text = f"{title}\n{description}"

    required = matching_keywords(
        searchable_text,
        filters.required_skills,
    )

    if len(required) != len(filters.required_skills):
        return None

    preferred = matching_keywords(
        searchable_text,
        filters.preferred_skills,
    )

    experience = extract_experience_years(description)

    if filters.max_experience_years is not None:
        if experience is not None and experience > filters.max_experience_years:
            return None

    score = len(required) * 10 + len(preferred) * 3

    return MatchedJob(
        job=job,
        workplace=workplace,
        matched_required=required,
        matched_preferred=preferred,
        experience_years=experience,
        score=score,
    )


def display_results(results: list[MatchedJob]) -> None:
    print(f"\n{'=' * 80}")
    print(f"MATCHED JOBS: {len(results)}")
    print(f"{'=' * 80}")

    for index, result in enumerate(results, start=1):
        job = result.job

        print(f"\n{'-' * 80}")
        print(f"{index}. {job.title}")
        print(f"{'-' * 80}")

        print("Company:", job.company)
        print("Location:", job.location)
        print("Published:", job.date_posted or "Unknown")
        print("Employment type:", normalize_job_types(job) or "Unknown")
        print("Workplace:", result.workplace.value)
        print("Experience years:", result.experience_years)
        print("Required skills:", ", ".join(result.matched_required))
        print("Preferred skills:", ", ".join(result.matched_preferred))
        print("Score:", result.score)
        print("URL:", job.job_url)

        print("\nFull description:")
        print(job.description or "Not available")


def main() -> None:
    filters = FILTERS

    if filters.results_wanted <= 0:
        raise ValueError("results_wanted must be positive")

    if filters.hours_old is not None and filters.hours_old < 0:
        raise ValueError("hours_old must be nonnegative")

    params = {
        "keywords": filters.search_term,
        "location": filters.location,
    }

    search_url = f"{BASE_URL}?{urlencode(params)}"

    print("XING ADVANCED JOB SEARCH")
    print("Search:", filters.search_term)
    print("Location:", filters.location)
    print("URL:", search_url)

    results: list[MatchedJob] = []

    with requests.Session() as session:
        session.headers.update(HEADERS)

        search_html = fetch_html(session, search_url)

        if search_html is None:
            return

        jobs = parse_search_results(search_html)

        print("\nJobs found:", len(jobs))

        # The current script processes only jobs from
        # the initial HTML search page.
        for index, job in enumerate(
            jobs[: filters.results_wanted],
            start=1,
        ):
            print(f"\n[{index}/{min(len(jobs), filters.results_wanted)}] {job.title}")

            # Avoid unnecessary detail requests when
            # the title cannot match.
            if filters.title_keywords:
                if not matching_keywords(
                    job.title or "",
                    filters.title_keywords,
                ):
                    print("Skipped: title filter")
                    continue

            time.sleep(REQUEST_DELAY_SECONDS)

            detail_html = fetch_html(session, job.job_url)

            if detail_html is None:
                print("Skipped: detail unavailable")
                continue

            enriched_job = enrich_job_post(
                job,
                detail_html,
                DescriptionFormat.MARKDOWN,
            )

            result = evaluate_job(enriched_job, filters)

            if result is None:
                print("Filtered out")
                continue

            results.append(result)
            print("Matched! Score:", result.score)

    results.sort(
        key=lambda result: result.score,
        reverse=True,
    )

    display_results(results)


if __name__ == "__main__":
    main()
