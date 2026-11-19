from __future__ import annotations

from dataclasses import dataclass

from jobspy.model import JobType, ScraperInput


@dataclass(frozen=True, slots=True)
class XingSearchConfig:
    """Normalized search settings for a XING page loader."""

    keywords: str
    location: str | None
    is_remote: bool
    job_type: JobType | None

    @classmethod
    def from_scraper_input(
        cls,
        scraper_input: ScraperInput,
    ) -> XingSearchConfig:
        keywords = (scraper_input.search_term or "").strip()

        if not keywords:
            raise ValueError("XING search keywords are required")

        location = scraper_input.location.strip() if scraper_input.location else None

        return cls(
            keywords=keywords,
            location=location or None,
            is_remote=scraper_input.is_remote,
            job_type=scraper_input.job_type,
        )
