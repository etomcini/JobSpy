from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from jobspy.model import DescriptionFormat, JobPost
from jobspy.xing.detail import (
    enrich_job_post,
    extract_xing_html_description,
)
from jobspy.xing.util import parse_search_results

BASE_URL = "https://www.xing.com/jobs/search/ki"

HEADERS = {
    "User-Agent": "JobSpy-XING-Integration-Test/0.1",
    "Accept": "text/html",
}

TIMEOUT = 20
PREVIEW_LENGTH = 1500


def fetch_html(url: str) -> str | None:
    """Fetch a public XING HTML page."""

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=False,
            headers=HEADERS,
        )
    except requests.RequestException as exc:
        print(f"HTTP request failed: {exc}")
        return None

    print("HTTP status:", response.status_code)

    if response.status_code != 200:
        print("Unable to retrieve page.")
        return None

    response.encoding = "utf-8"

    print("HTML size:", len(response.content))

    return response.text


def inspect_search_html(html: str) -> None:
    """Inspect the XING search page."""

    soup = BeautifulSoup(html, "html.parser")

    print("\nSearch HTML inspection:")

    print(
        "Title:",
        soup.title.get_text(" ", strip=True) if soup.title else None,
    )

    job_links = [
        link
        for link in soup.select('a[href^="/jobs/"]')
        if not link.get("href", "").startswith("/jobs/search")
    ]

    print("Job links:", len(job_links))


def display_search_results(jobs: list[JobPost]) -> None:
    """Display parsed XING search results."""

    print("\nExisting JobSpy parser:")
    print("Parsed jobs:", len(jobs))

    for job in jobs[:5]:
        print(f"\n{'=' * 80}")
        print("ID:", job.id)
        print("Title:", job.title)
        print("Company:", job.company)
        print("Location:", job.location)
        print("URL:", job.job_url)

        print(
            "Description:",
            (job.description or "Not available")[:PREVIEW_LENGTH],
        )


def inspect_json_ld(soup: BeautifulSoup) -> None:
    """Inspect structured JSON-LD data in a job detail page."""

    print("\nJSON-LD inspection:")

    scripts = soup.select('script[type="application/ld+json"]')

    print("JSON-LD scripts:", len(scripts))

    for index, script in enumerate(scripts, start=1):
        raw_json = script.string or script.get_text()

        try:
            data: Any = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            print(f"Script {index}: Invalid JSON ({exc})")
            continue

        entries = data if isinstance(data, list) else [data]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            print("\nScript:", index)
            print("Type:", entry.get("@type"))
            print("Available fields:", list(entry.keys()))

            description = entry.get("description")

            print(
                "Description type:",
                type(description).__name__,
            )

            print(
                "Description length:",
                len(description) if isinstance(description, str) else 0,
            )

            if isinstance(description, str):
                print(
                    "Description preview:",
                    description[:PREVIEW_LENGTH],
                )


def inspect_detail_html(html: str) -> None:
    """Inspect available description structures."""

    soup = BeautifulSoup(html, "html.parser")

    print("\nDetail page diagnostics:")

    print("HTML size:", len(html))

    print(
        "Page title:",
        soup.title.get_text(" ", strip=True) if soup.title else None,
    )

    print(
        "Expandable content:",
        len(soup.select('[data-testid="expandable-content"]')),
    )

    print(
        "Description wrappers:",
        len(soup.select('[class*="DescriptionWrapper"]')),
    )

    print(
        "Styled content sections:",
        len(soup.select('[class*="StyledContent"]')),
    )

    print(
        "Contains JobPosting:",
        "JobPosting" in html,
    )

    print(
        "Contains expandable-content marker:",
        "expandable-content" in html,
    )

    print(
        "Contains jobDescription marker:",
        "jobDescription" in html,
    )

    inspect_json_ld(soup)


def inspect_description_extraction(
    job: JobPost,
    html: str,
) -> None:
    """Compare HTML extraction with existing JobSpy enrichment."""

    print(f"\n{'=' * 80}")
    print("DESCRIPTION EXTRACTION TEST")
    print(f"{'=' * 80}")

    # Method 1: HTML description extraction
    html_description = extract_xing_html_description(html)

    print("\nMethod 1: HTML extractor")
    print(
        "Description length:",
        len(html_description or ""),
    )
    print(
        "Description preview:",
        (html_description or "Not available")[:PREVIEW_LENGTH],
    )

    # Method 2: Existing JSON-LD enrichment
    print("\nMethod 2: Existing JobSpy enrichment")

    try:
        enriched_job = enrich_job_post(
            job,
            html,
            DescriptionFormat.MARKDOWN,
        )
    except Exception as exc:
        print(
            "Enrichment failed:",
            type(exc).__name__,
            str(exc),
        )
        return

    print("Job ID:", enriched_job.id)
    print("Title:", enriched_job.title)
    print("URL:", enriched_job.job_url)

    print(
        "Description length:",
        len(enriched_job.description or ""),
    )

    print("\nFull job description:")
    print(enriched_job.description or "Not available")


def main() -> None:
    params = {
        "keywords": "python developer",
        "location": "Munich",
    }

    search_url = f"{BASE_URL}?{urlencode(params)}"

    print(f"\n{'=' * 80}")
    print("XING LIVE SEARCH TEST")
    print(f"{'=' * 80}")

    print("Search URL:", search_url)

    search_html = fetch_html(search_url)

    if search_html is None:
        return

    inspect_search_html(search_html)

    try:
        jobs = parse_search_results(search_html)
    except Exception as exc:
        print(
            "Search parser failed:",
            type(exc).__name__,
            str(exc),
        )
        return

    display_search_results(jobs)

    if not jobs:
        print("\nNo jobs available for detail testing.")
        return

    # Test the first real job.
    job = jobs[0]

    print(f"\n{'=' * 80}")
    print("XING LIVE JOB DETAIL TEST")
    print(f"{'=' * 80}")

    print("Job:", job.title)
    print("URL:", job.job_url)

    detail_html = fetch_html(job.job_url)

    if detail_html is None:
        return

    inspect_detail_html(detail_html)

    inspect_description_extraction(job, detail_html)


if __name__ == "__main__":
    main()
