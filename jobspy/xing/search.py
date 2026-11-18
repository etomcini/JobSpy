from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True)
class XingSearch:
    keywords: str
    location: str | None
    city_id: str | None
    search_id: str | None


def parse_search_url(url: str) -> XingSearch:
    """Parse an observed XING search URL."""

    parsed = urlsplit(url)

    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.xing.com"
        or parsed.path != "/jobs/search/ki"
    ):
        raise ValueError("Invalid XING search URL")

    params = parse_qs(parsed.query)

    keywords = params.get("keywords", [""])[0].strip()

    if not keywords:
        raise ValueError("XING search keywords are required")

    return XingSearch(
        keywords=keywords,
        location=params.get("location", [None])[0],
        city_id=params.get("cityId", [None])[0],
        search_id=params.get("id", [None])[0],
    )
