from __future__ import annotations

from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from jobspy.xing.util import parse_search_results

BASE_URL = "https://www.xing.com/jobs/search/ki"


def main() -> None:
    params = {
        "keywords": "python developer",
        "location": "Munich",
    }

    url = f"{BASE_URL}?{urlencode(params)}"

    response = requests.get(
        url,
        timeout=20,
        allow_redirects=False,
        headers={
            "User-Agent": "JobSpy-XING-Integration-Test/0.1",
            "Accept": "text/html",
        },
    )

    print("HTTP status:", response.status_code)
    response.encoding = "utf-8"
    print("HTML size:", len(response.content))

    if response.status_code != 200:
        print("Unable to retrieve search page.")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    print("\nHTML inspection:")
    print("Title:", soup.title.get_text(strip=True) if soup.title else None)

    job_links = [
        link
        for link in soup.select('a[href^="/jobs/"]')
        if not link.get("href", "").startswith("/jobs/search")
    ]

    print("Job links:", len(job_links))

    print("\nExisting JobSpy parser:")

    try:
        jobs = parse_search_results(response.text)

        print("Parsed jobs:", len(jobs))

        for job in jobs[:5]:
            print(
                f"ID: {job.id}\n"
                f"Title: {job.title}\n"
                f"Company: {job.company}\n"
                f"Location: {job.location}\n"
                f"URL: {job.job_url}\n"
            )

    except Exception as exc:
        print(
            "Parser error:",
            type(exc).__name__,
            str(exc),
        )


if __name__ == "__main__":
    main()
